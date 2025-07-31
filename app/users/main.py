from fastapi import APIRouter, HTTPException, Query, Depends, Body
from fastapi.responses import JSONResponse
from database.connect_db import connect_database
from services.response_handler import verify_bearer_token
from typing import Annotated, List, Dict
import json
from app.users.models.quiz_model import QuizSchema

router = APIRouter()


@router.get("/")
def get_all_users(auth: dict = Depends(verify_bearer_token)):
    user_id = auth.get("id")
    connection = connect_database()
    cursor = connection.cursor()
    try:
        get_all_users_query = """
        SELECT id , full_name , username,photo FROM users
        """
        cursor.execute(get_all_users_query)

        all_fetched_data = cursor.fetchall()

        if not all_fetched_data:
            raise HTTPException(status_code=400, detail="Something went wrong")

        all_fetched_data = list(all_fetched_data)
        result = []
        for data in all_fetched_data:
            id, name, username, image = data
            if user_id != id:
                is_this_me = False
            if user_id == id:
                is_this_me = True
            result.append(
                {
                    "id": id,
                    "name": name,
                    "username": username,
                    "image": image,
                    "is_this_me": is_this_me,
                    "is_followed": False,
                }
            )

        return JSONResponse(content={"message": "Successful Response", "data": result})

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@router.get("/")
def get_user(
    user_id: int = Query(None, description="Enter User ID"),
    username: str = Query(None, description="Enter Username"),
    auth: dict = Depends(verify_bearer_token),
):
    if user_id is None and username is None:
        raise HTTPException(status_code=400, detail="Provide user_id or username")

    connection = connect_database()
    cursor = connection.cursor()

    try:
        if user_id:
            query = (
                "SELECT id, full_name, email, username, photo FROM Users WHERE id = %s"
            )
            cursor.execute(query, (user_id,))
        if username:
            query = "SELECT id, full_name, email, username, photo FROM Users WHERE username = %s"
            cursor.execute(query, (username,))

        user = cursor.fetchone()

        if user is None:
            raise HTTPException(status_code=404, detail="User not Found")

        (id, full_name, email, username, photo) = user

        return {
            "user": {
                "id": id,
                "full_name": full_name,
                "username": username,
                "email": email,
                "photo": photo,
            }
        }

    finally:
        cursor.close()
        connection.close()


@router.get("/check-username")
def check_username_uniqueness(
    username: Annotated[
        str, Query(..., description="Enter Username to Check Uniqueness")
    ],
):
    connection = connect_database()
    cursor = connection.cursor()

    if username is None:
        raise HTTPException(status_code=400, detail="Enter Username")

    try:
        cursor.execute("SELECT * FROM Users WHERE username=%s", (username,))
        existing_data = cursor.fetchone()

        if existing_data:
            return {"is_unique": False}

        elif not existing_data:
            return {"is_unique": True}

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@router.get("/me/{quiz_id}/edit")
def user_page(quiz_id: str, user: dict = Depends(verify_bearer_token)):
    user_id = user.get("id")

    connection = connect_database()
    cursor = connection.cursor()

    try:
        query = """
        SELECT q.cover_photo , q.title, q.description,
        qq.id, qq.question, qq.question_index, qq.options, qq.correct_option, qq.points, qq.duration , q.id
        FROM quizzes as q
        JOIN users as u ON u.id = q.creator_id
        JOIN quiz_questions as qq ON qq.quiz_id = q.id
        WHERE u.id = %s AND q.id = %s
        """

        cursor.execute(query, (user_id, quiz_id))
        fetched_data = cursor.fetchall()

        if not fetched_data:
            raise HTTPException(status_code=404, detail="Not Found")

        quiz_id = fetched_data[0][10]
        cover_photo = fetched_data[0][0]
        title = fetched_data[0][1]
        description = fetched_data[0][2]

        questions = []
        for row in fetched_data:
            questions.append(
                {
                    "id": row[3],
                    "question": row[4],
                    "question_index": row[5],
                    "options": row[6],
                    "correct_option": row[7],
                    "points": row[8],
                    "duration": row[9],
                }
            )
        return {
            "user_id": user_id,
            "edit_data": {
                "quiz_id": quiz_id,
                "cover_photo": cover_photo,
                "title": title,
                "description": description,
                "questions": questions,
            },
        }

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@router.put("/me/{quiz_id}/edit")
def edit_user_quiz(
    quiz_id: str, update_data: QuizSchema, user: dict = Depends(verify_bearer_token)
):
    user_id = user.get("id")
    connection = connect_database()
    cursor = connection.cursor()

    try:

        if not update_data:
            raise HTTPException(status_code=404, detail="No any Update Data")

        cover_photo = update_data.cover_photo
        title = update_data.title
        description = update_data.description
        creator_id = user_id

        query = """
            UPDATE quizzes
            SET cover_photo = %s,
            title = %s,
            description = %s
            WHERE id = %s AND creator_id = %s
        """

        cursor.execute(query, (cover_photo, title, description, quiz_id, creator_id))

        for q in update_data.questions:
            question_query = """
                    UPDATE quiz_questions
                    SET question = %s,
                    question_index = %s,
                    options = %s,
                    correct_option = %s,
                    points = %s,
                    duration = %s
                    WHERE quiz_id = %s AND question_index = %s
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
                    quiz_id,
                    q.question_index,
                ),
            )

        connection.commit()
        return {
            "message": "Updated Successfully",
            "quiz_id": quiz_id,
            "updated_questions": len(update_data.questions),
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


@router.delete("/me/{quiz_id}/delete")
def delete_quiz(quiz_id: str, auth: dict = Depends(verify_bearer_token)):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id FROM quizzes WHERE id = %s", (quiz_id,))
        quiz = cursor.fetchone()

        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        cursor.execute("SELECT created_by FROM quizzes WHERE id = %s", (quiz_id,))
        created_id = cursor.fetchone()[0]

        if not created_id:
            raise HTTPException(status_code=404, detail="Quiz not found")

        if created_id != auth.get("id"):
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this quiz"
            )

        query = """
        DELETE FROM quizzes WHERE id=%s
        """
        cursor.execute(query, (quiz_id,))

        connection.commit()

        return {"message": "Quiz Deleted Successfully"}

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(status_code=400, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
