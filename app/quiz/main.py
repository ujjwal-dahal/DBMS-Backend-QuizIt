from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from datetime import datetime, timezone
import json
import random as rd
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os
from cloudinary.uploader import upload as cloudinary_upload
import uuid


# Project Imports
from .quiz_models.quiz_model import QuizTag
from services.response_handler import verify_bearer_token
from database.connect_db import connect_database
from services.cloudinary_config import configure_cloudinary

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

app = APIRouter()
fernet = Fernet(ENCRYPTION_KEY)
configure_cloudinary()


@app.post("/upload-quiz")
async def upload_quiz(
    cover_photo: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
    is_published: bool = Form(...),
    questions: str = Form(...),
    tags: str = Form(...),
    auth: dict = Depends(verify_bearer_token),
):
    connection = connect_database()
    cursor = connection.cursor()
    user_id = auth.get("id")

    try:

        file_bytes = await cover_photo.read()

        unique_public_id = f"quiz_cover_{user_id}_{uuid.uuid4().hex}"

        upload_result = cloudinary_upload(
            file_bytes,
            folder=f"quiz_covers/user_{user_id}",
            public_id=unique_public_id,
            overwrite=False,
        )

        cover_photo_url = upload_result.get("secure_url")
        if not cover_photo_url:
            raise HTTPException(
                status_code=500, detail="Failed to upload quiz cover photo"
            )

        created_at = datetime.now(timezone.utc)

        insert_quiz_query = """
            INSERT INTO quizzes (cover_photo, title, description, is_published, created_at, creator_id)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """

        cursor.execute(
            insert_quiz_query,
            (
                cover_photo_url,
                title,
                description,
                is_published,
                created_at,
                user_id,
            ),
        )
        returned_quiz_id = cursor.fetchone()
        if not returned_quiz_id:
            raise HTTPException(status_code=500, detail="Unable to insert quiz")

        quiz_id = returned_quiz_id[0]

        questions_data = json.loads(questions)
        for q in questions_data:
            question_query = """
                INSERT INTO quiz_questions (question, question_index, options, correct_option, points, duration, quiz_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                question_query,
                (
                    q.get("question"),
                    q.get("question_index"),
                    json.dumps(q.get("options")),
                    q.get("correct_option"),
                    q.get("points"),
                    q.get("duration"),
                    quiz_id,
                ),
            )

        tags_data = json.loads(tags)
        for tag in tags_data:
            cursor.execute("SELECT id FROM tags WHERE name=%s", (tag,))
            existing_tag = cursor.fetchone()
            if existing_tag:
                tag_id = existing_tag[0]
            else:
                cursor.execute(
                    "INSERT INTO tags (name) VALUES (%s) RETURNING id", (tag,)
                )
                tag_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO quiz_tags (quiz_id, tag_id) VALUES (%s, %s)",
                (quiz_id, tag_id),
            )

        connection.commit()

        return {
            "message": "Quiz Uploaded Successfully",
            "quiz_id": quiz_id,
            "cover_photo_url": cover_photo_url,
        }

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.get("/tags-option")
def quiz_tags_option(auth: dict = Depends(verify_bearer_token)):
    quiz_tags_list = [tag.value for tag in QuizTag]
    return {"quiz_tags": quiz_tags_list}


@app.get("/")
def get_all_quizzes(auth: dict = Depends(verify_bearer_token)):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        query = """
        SELECT q.id, q.title, q.description, q.cover_photo,
               u.full_name, u.photo, q.created_at,
               COUNT(qq.id)
        FROM quizzes q
        JOIN users u ON u.id = q.creator_id
        LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id
        GROUP BY q.id, q.title, q.description, q.cover_photo,
                 u.full_name, u.photo, q.created_at
        """
        cursor.execute(query)
        all_fetched_data = cursor.fetchall()

        if not all_fetched_data:
            raise HTTPException(status_code=404, detail="No quizzes found.")

        result = []
        for data in all_fetched_data:
            id, title, description, cover_photo, name, image, date, count = data
            result.append(
                {
                    "id": id,
                    "title": title,
                    "description": description,
                    "cover_photo": cover_photo,
                    "author": name,
                    "image": image,
                    "plays": rd.randint(1, 100),
                    "date": date,
                    "count": count,
                }
            )

        return {"message": "Response Successful", "data": result}

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.get("/my-quizzes")
def my_quizzes(
    auth: dict = Depends(verify_bearer_token),
    filter: str = Query(None),
    order: str = Query(None),
):
    connection = connect_database()
    cursor = connection.cursor()
    creator_id = auth.get("id")

    try:
        filtering_list = ["newest"]
        ordering_list = ["asc", "desc"]

        if filter is None:
            filter = "newest"
        if order is None:
            order = "asc"

        if order.lower() not in ordering_list:
            raise HTTPException(status_code=400, detail="Invalid ordering value")
        if filter not in filtering_list:
            raise HTTPException(status_code=400, detail="Invalid filtering value")

        if filter == "newest":
            filtering_criteria = "created_at"

        get_quiz_description_query = f"""
        SELECT q.id , q.cover_photo, q.title , q.description, q.created_at
        FROM quizzes AS q
        WHERE q.creator_id = %s
        ORDER BY {filtering_criteria} {order.upper()}
        """

        cursor.execute(get_quiz_description_query, (creator_id,))
        fetch_all_data = cursor.fetchall()

        if not fetch_all_data:
            return {"data": []}

        result = []

        for data in fetch_all_data:
            (quiz_id, cover_photo, title, description, created_at) = data

            get_all_questions_query = """
            SELECT qq.id, qq.question, qq.question_index, qq.options,
                   qq.correct_option, qq.points, qq.duration
            FROM quiz_questions AS qq
            WHERE qq.quiz_id = %s
            """

            cursor.execute(get_all_questions_query, (quiz_id,))
            fetch_all_questions = cursor.fetchall()

            question_result = []
            for qq in fetch_all_questions:
                (
                    id,
                    question,
                    question_index,
                    options,
                    correct_option,
                    points,
                    duration,
                ) = qq
                question_result.append(
                    {
                        "question_id": id,
                        "question": question,
                        "question_index": question_index,
                        "options": options,
                        "correct_option": correct_option,
                        "points": points,
                        "duration": duration,
                    }
                )

            result.append(
                {
                    "quiz_id": quiz_id,
                    "cover_photo": cover_photo,
                    "title": title,
                    "description": description,
                    "questions": question_result,
                    "created_at": created_at,
                }
            )

        return {"message": "Successful Response", "data": result}

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.get("/{quiz_id}")
def get_quiz_by_id(quiz_id: str, auth: dict = Depends(verify_bearer_token)):
    connection = connect_database()
    cursor = connection.cursor()
    user_id = auth.get("id")

    try:
        query = """
                SELECT q.id, u.id, q.title, q.description, q.cover_photo,
                u.full_name, u.photo, q.created_at,
                COUNT(qq.id)
                FROM quizzes q
                JOIN users u ON u.id = q.creator_id
                LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id
                WHERE q.id = %s
                GROUP BY q.id, u.id, q.title, q.description, q.cover_photo,
                u.full_name, u.photo, q.created_at
        """
        cursor.execute(query, (quiz_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Quiz not found.")

        id, player_id, title, description, cover_photo, name, image, date, count = row

        if player_id == user_id:
            is_this_me = True
        if player_id != user_id:
            is_this_me = False

        follower_count_query = """
        SELECT COUNT(*) FROM follows WHERE following_id = %s
        """
        cursor.execute(follower_count_query, (user_id,))
        follower_count = cursor.fetchone()[0]

        following_count_query = """
        SELECT COUNT(*) FROM follows WHERE follower_id = %s
        """
        cursor.execute(following_count_query, (user_id,))
        following_count = cursor.fetchone()[0]

        is_followed_query = """
        SELECT 1 FROM follows WHERE follower_id = %s AND following_id = %s
        """
        cursor.execute(is_followed_query, (user_id, player_id))
        is_followed = cursor.fetchone() is not None

        result = {
            "id": id,
            "title": title,
            "description": description,
            "cover_photo": cover_photo,
            "author": name,
            "image": image,
            "plays": rd.randint(1, 100),
            "date": date,
            "is_this_me": is_this_me,
            "count": count,
            "follower": follower_count,
            "following": following_count,
            "is_followed": is_followed,
            "quiz_creator_id": player_id,
        }

        return {"message": "Response Successful", "data": result}

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.delete("/{quiz_id}/question/{question_id}")
def delete_question(
    quiz_id: str, question_id: str, auth: dict = Depends(verify_bearer_token)
):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        delete_question_query = """
        DELETE FROM quiz_questions 
        WHERE quiz_id=%s AND id=%s
        """

        cursor.execute(delete_question_query, (quiz_id, question_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found")

        connection.commit()

        return {"message": f"Question Id : {question_id} Deleted Successfully"}

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.get("/quiz-questions/{quiz_id}")
def get_quiz_questions(quiz_id: str, auth: dict = Depends(verify_bearer_token)):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        get_all_quiz_questions_query = """
            SELECT qq.id, qq.question, qq.question_index, qq.options,
                   qq.correct_option, qq.points, qq.duration
            FROM quiz_questions AS qq
            WHERE qq.quiz_id = %s
        """

        cursor.execute(get_all_quiz_questions_query, (quiz_id,))
        fetch_all_questions = cursor.fetchall()

        question_result = []
        for qq in fetch_all_questions:
            (
                id,
                question,
                question_index,
                options,
                correct_option,
                points,
                duration,
            ) = qq

            encrypted_correct_option = fernet.encrypt(
                str(correct_option).encode()
            ).decode()

            question_result.append(
                {
                    "question_id": id,
                    "question": question,
                    "question_index": question_index,
                    "options": options,
                    "correct_option": encrypted_correct_option,
                    "points": points,
                    "duration": duration,
                }
            )

        return {
            "message": "Successful Response",
            "data": question_result,
        }

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
