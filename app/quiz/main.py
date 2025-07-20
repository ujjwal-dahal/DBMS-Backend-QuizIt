from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from .quiz_models.quiz_model import QuizSchema, QuizTag
from services.response_handler import verify_bearer_token
from database.connect_db import connect_database
from datetime import datetime, timezone
import json

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
