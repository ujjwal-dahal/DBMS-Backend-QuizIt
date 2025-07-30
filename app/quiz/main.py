from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from .quiz_models.quiz_model import QuizSchema, QuizTag
from services.response_handler import verify_bearer_token
from database.connect_db import connect_database
from datetime import datetime, timezone
import json
import random as rd

app = APIRouter()


@app.post("/upload-quiz")
def upload_quiz(quiz_data: QuizSchema, auth: dict = Depends(verify_bearer_token)):
    connection = connect_database()
    cursor = connection.cursor()
    user_id = auth.get("id")
    created_at = datetime.now(timezone.utc)
    try:
        query_into_quiz = """
            INSERT INTO quizzes ( cover_photo , title , description , is_published , created_at , creator_id )
            VALUES
            ( %s,%s,%s,%s,%s,%s )
            RETURNING id
        """

        cursor.execute(
            query_into_quiz,
            (
                quiz_data.cover_photo,
                quiz_data.title,
                quiz_data.description,
                quiz_data.is_published,
                created_at,
                user_id,
            ),
        )

        returned_quiz_id = cursor.fetchone()

        if not returned_quiz_id:
            raise HTTPException(
                status_code=500, detail="Unable to Insert into Database"
            )

        quiz_id = returned_quiz_id[0]

        for q in quiz_data.questions:

            question_query = """
            INSERT INTO quiz_questions ( question , question_index, options, correct_option , points , duration, quiz_id )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """

            cursor.execute(
                question_query,
                (
                    q.question,
                    q.question_index,
                    json.dumps(q.options),
                    q.correct_option,
                    q.points,
                    q.duration,
                    returned_quiz_id[0],
                ),
            )

        tag_query = """
        INSERT INTO tags (name)
        VALUES (%s) RETURNING id
        """
        for tag in quiz_data.tags:
            cursor.execute("SELECT id FROM tags WHERE name=%s", (tag,))
            existing_data = cursor.fetchone()

            if existing_data:
                tag_id = existing_data[0]
            else:
                cursor.execute(tag_query, (tag,))
                tag_id = cursor.fetchone()[0]

            quiz_tag_query = """
            INSERT INTO quiz_tags (quiz_id , tag_id)
            VALUES
            (%s,%s)
            """
            cursor.execute(quiz_tag_query, (quiz_id, tag_id))

        connection.commit()

        return {"message": "Quiz Uploaded Successfully", "quiz_id": quiz_id}

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
    return JSONResponse(content={"quiz_tags": quiz_tags_list})


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

        return JSONResponse(content={"message": "Response Successful", "data": result})

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

    try:
        query = """
        SELECT q.id, q.title, q.description, q.cover_photo,
               u.full_name, u.photo, q.created_at,
               COUNT(qq.id)
        FROM quizzes q
        JOIN users u ON u.id = q.creator_id
        LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id
        WHERE q.id = %s
        GROUP BY q.id, q.title, q.description, q.cover_photo,
                 u.full_name, u.photo, q.created_at
        """
        cursor.execute(query, (quiz_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Quiz not found.")

        id, title, description, cover_photo, name, image, date, count = row
        result = {
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

        return JSONResponse(content={"message": "Response Successful", "data": result})

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
