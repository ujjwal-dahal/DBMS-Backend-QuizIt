from datetime import datetime, timezone
from app.websocket.websocket_manager.ws_manager import ConnectionManager
from database.connect_db import connect_database

manager = ConnectionManager()


async def process_answer_and_update_leaderboard(
    user_id: int, room_code: str, answer_data: dict
):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id, quiz_id FROM rooms WHERE room_code = %s", (room_code,)
        )
        room = cursor.fetchone()
        if not room:
            return {"error": "Invalid room code"}
        room_id, quiz_id = room

        cursor.execute(
            "SELECT id FROM room_participants WHERE user_id = %s AND room_id = %s",
            (user_id, room_id),
        )
        participant = cursor.fetchone()
        if not participant:
            return {"error": "User not participant in room"}
        participant_id = participant[0]

        question_id = answer_data.get("question_id")
        selected_option = answer_data.get("selected_option")
        point = answer_data.get("point", 0)
        answered_at_str = answer_data.get("answered_at")

        if not (question_id and selected_option is not None and answered_at_str):
            return {"error": "Incomplete answer data"}

        answered_at = datetime.fromisoformat(answered_at_str.replace("Z", "+00:00"))

        cursor.execute(
            "SELECT correct_option FROM quiz_questions WHERE question_index = %s AND quiz_id = %s",
            (question_id, quiz_id),
        )
        result = cursor.fetchone()
        if not result:
            return {"error": "Question not found"}
        correct_option = result[0]

        is_correct = str(correct_option) == str(selected_option)

        if is_correct:
            cursor.execute(
                "UPDATE room_participants SET score = score + %s WHERE id = %s",
                (point, participant_id),
            )

        cursor.execute(
            "INSERT INTO room_questions (room_id, question_id, shown_at) VALUES (%s, %s, %s) RETURNING id",
            (room_id, question_id, datetime.now(timezone.utc)),
        )
        question_show_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO room_answers (room_id, participant_id, question_id, selected_option, is_correct, answered_at)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
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
        return {"error": str(e)}

    finally:
        cursor.close()
        connection.close()
