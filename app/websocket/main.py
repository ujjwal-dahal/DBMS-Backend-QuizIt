from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from datetime import datetime, timezone
from starlette.websockets import WebSocketState
import json

# Project Imports
from services.response_handler import verify_bearer_token, verify_bearer_token_manual
from database.connect_db import connect_database
from services.room_code import room_code_generator
from app.websocket.websocket_manager.ws_manager import ConnectionManager
from app.websocket.models.models import AnswerSchema
from app.websocket.models.output_response import (
    AnswerResponseSchema,
    LeaderboardResponse,
)
from app.websocket.helper.helper_functions import process_answer_and_update_leaderboard

app = APIRouter()
manager = ConnectionManager()


@app.get("/room-code")
def room_code_transfer(
    quiz_id: str = Query(...), auth: dict = Depends(verify_bearer_token)
):

    connection = connect_database()
    cursor = connection.cursor()
    creator_id = auth.get("id")

    try:
        room_code = room_code_generator()
        query = """
            INSERT INTO rooms (room_code, quiz_id, created_by)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        cursor.execute(query, (room_code, quiz_id, creator_id))
        fetched_id = cursor.fetchone()[0]

        if not fetched_id:
            raise HTTPException(status_code=500, detail="Something went wrong")

        cursor.execute("SELECT username FROM users WHERE id=%s", (creator_id,))

        fetched_username = cursor.fetchone()

        if not fetched_username:
            raise HTTPException(status_code=500, detail="Something went wrong")

        (room_host_name,) = fetched_username

        connection.commit()
        return {
            "room_code": room_code,
            "room_host": room_host_name,
            "redirect": f"room/{room_code}/admin",
        }

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.post("/{room_code}/join")
def check_user(
    room_code: str,
    auth: dict = Depends(verify_bearer_token),
):
    connection = connect_database()
    cursor = connection.cursor()
    user_id = auth.get("id")

    try:
        cursor.execute(
            "SELECT id, quiz_id FROM rooms WHERE room_code = %s", (room_code,)
        )
        room = cursor.fetchone()

        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        room_id, quiz_id = room

        cursor.execute(
            "SELECT id FROM room_participants WHERE room_id = %s AND user_id = %s",
            (room_id, user_id),
        )
        existing = cursor.fetchone()

        if existing:
            return {
                "message": "Already Joined",
                "participant_id": existing[0],
                "is_joined": True,
                "quiz_id": quiz_id,
            }

        joined_at = datetime.now(timezone.utc)
        cursor.execute(
            "INSERT INTO room_participants (room_id, user_id, joined_at) VALUES (%s, %s, %s) RETURNING id",
            (room_id, user_id, joined_at),
        )
        participant_id = cursor.fetchone()[0]
        connection.commit()

        return {
            "message": "Joined",
            "participant_id": participant_id,
            "is_joined": True,
            "quiz_id": quiz_id,
        }

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.websocket("/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        auth = verify_bearer_token_manual(token)
        user_id = auth.get("id")

        if not user_id:
            await websocket.close(code=1008)
            return

        conn = connect_database()
        cursor = conn.cursor()
        cursor.execute("SELECT username, photo FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            await websocket.close(code=1008)
            return

        username, photo = result

        await manager.connect(websocket, room_code, username, user_id, photo)

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.broadcast("chat", room_code, f"{username}: {data}")
                continue

            msg_type = message.get("type")
            msg_data = message.get("data")

            if msg_type == "chat":
                await manager.broadcast("chat", room_code, f"{username}: {msg_data}")

            elif msg_type == "answer":
                result = await process_answer_and_update_leaderboard(
                    user_id, room_code, msg_data
                )
                await websocket.send_json({"type": "answer_ack", "data": result})

            else:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast_user_list(room_code)

    except Exception as e:
        print("WebSocket Error:", e)
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011)


@app.post("/start-quiz/{room_code}")
async def start_quiz(room_code: str, auth: dict = Depends(verify_bearer_token)):
    user_id = auth.get("id")

    connection = connect_database()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id, created_by FROM rooms WHERE room_code = %s",
            (room_code,),
        )
        room = cursor.fetchone()

        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        room_id, room_host_id = room

        if user_id != room_host_id:
            raise HTTPException(
                status_code=403, detail="Only room host can start the quiz"
            )

        await manager.broadcast("quiz_started", room_code)

        return {"message": "Quiz Started By Room Host"}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.post("/{room_code}/game")
async def submit_answer(
    room_code: str,
    answer_data: AnswerSchema,
    auth: dict = Depends(verify_bearer_token),
):
    connection = connect_database()
    cursor = connection.cursor()
    user_id = auth.get("id")

    try:
        cursor.execute(
            "SELECT id, quiz_id FROM rooms WHERE room_code = %s", (room_code,)
        )
        room = cursor.fetchone()
        if not room:
            raise HTTPException(status_code=400, detail="Invalid room code")
        room_id, quiz_id = room

        cursor.execute(
            "SELECT id FROM room_participants WHERE user_id = %s AND room_id = %s",
            (user_id, room_id),
        )
        participant = cursor.fetchone()
        if not participant:
            raise HTTPException(status_code=400, detail="User not in this room")
        participant_id = participant[0]

        cursor.execute(
            """
            SELECT id, correct_option 
            FROM quiz_questions 
            WHERE question_index = %s AND quiz_id = %s
            """,
            (answer_data.question_index, quiz_id),
        )
        question = cursor.fetchone()
        if not question:
            raise HTTPException(status_code=400, detail="Question not found")
        question_id, correct_option = question

        selected_option = answer_data.selected_option
        is_correct = str(correct_option) == str(selected_option)

        if is_correct:
            cursor.execute(
                "UPDATE room_participants SET score = score + %s WHERE id = %s",
                (answer_data.point, participant_id),
            )

        cursor.execute(
            "INSERT INTO room_questions (room_id, question_id, shown_at) VALUES (%s, %s, %s) RETURNING id",
            (room_id, question_id, datetime.now(timezone.utc)),
        )
        question_show_id = cursor.fetchone()[0]

        answered_at = answer_data.answered_at
        cursor.execute(
            """
            INSERT INTO room_answers (
                room_id, participant_id, question_id,
                selected_option, is_correct, answered_at
            ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                room_id,
                participant_id,
                question_id,
                selected_option,
                is_correct,
                answered_at,
            ),
        )
        answer_id = cursor.fetchone()[0]

        connection.commit()

        cursor.execute(
            """
            SELECT u.id, u.full_name, rp.score, u.photo
            FROM room_participants rp
            JOIN users u ON rp.user_id = u.id
            WHERE rp.room_id = %s
            ORDER BY rp.score DESC
            """,
            (room_id,),
        )
        leaderboard_raw = cursor.fetchall()

        leaderboard_data = [
            {
                "id": uid,
                "name": name,
                "image": photo,
                "rank": idx + 1,
                "totalPoints": score,
            }
            for idx, (uid, name, score, photo) in enumerate(leaderboard_raw)
        ]

        await manager.send_leaderboard(room_code, leaderboard_data)

        return {
            "answer_id": answer_id,
            "question_show_id": question_show_id,
            "is_correct": is_correct,
        }

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.get("/{room_code}/{quiz_id}/{user_id}/result", response_model=AnswerResponseSchema)
def each_user_result(
    room_code: str,
    quiz_id: str,
    user_id: str,
    auth: dict = Depends(verify_bearer_token),
):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id FROM rooms WHERE room_code = %s", (room_code,))
        room = cursor.fetchone()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        room_id = room[0]

        cursor.execute(
            """
            SELECT rp.id, u.full_name, rp.score, u.photo, u.id
            FROM room_participants AS rp
            JOIN users AS u ON rp.user_id = u.id
            WHERE rp.room_id = %s AND u.id = %s
        """,
            (room_id, user_id),
        )

        participant_data = cursor.fetchone()

        if not participant_data:
            raise HTTPException(status_code=404, detail="Participant not found")

        participant_id, name, score, image, uid = participant_data

        user_info = {"id": uid, "name": name, "image": image, "score": score}

        cursor.execute(
            """
            SELECT
                qq.question,
                qq.options,
                ra.selected_option,
                qq.correct_option,
                ra.is_correct
            FROM room_answers AS ra
            JOIN quiz_questions AS qq ON ra.question_id = qq.id
            WHERE ra.room_id = %s AND ra.participant_id = %s
            ORDER BY qq.question_index ASC
        """,
            (room_id, participant_id),
        )

        answer_rows = cursor.fetchall()

        answers = []
        for (
            question,
            options,
            selected_option,
            correct_option,
            is_correct,
        ) in answer_rows:
            answers.append(
                {
                    "question": question,
                    "options": options,
                    "selected_option": selected_option,
                    "correct_option": correct_option,
                    "is_correct": is_correct,
                }
            )

        return {
            "message": "User result with answers",
            "user_info": user_info,
            "answers": answers,
        }

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.get("/{room_code}/{quiz_id}/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    room_code: str, quiz_id: str, auth: dict = Depends(verify_bearer_token)
):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id FROM rooms WHERE room_code = %s", (room_code,))
        room = cursor.fetchone()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        room_id = room[0]

        cursor.execute(
            """
            SELECT u.full_name, rp.score, u.photo, u.id
            FROM room_participants AS rp
            JOIN users AS u ON rp.user_id = u.id
            WHERE rp.room_id = %s
            ORDER BY rp.score DESC
            """,
            (room_id,),
        )
        fetched_data = cursor.fetchall()

        if not fetched_data:
            raise HTTPException(status_code=404, detail="No participants found")

        user_scores = [
            {
                "id": id,
                "name": name,
                "image": image,
                "rank": idx + 1,
                "totalPoints": score,
                "score": score,
            }
            for idx, (name, score, image, id) in enumerate(fetched_data)
        ]

        return {"message": "LeaderBoard Score", "user_score": user_scores}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()
