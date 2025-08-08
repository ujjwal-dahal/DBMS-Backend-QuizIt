from fastapi import APIRouter, HTTPException, Query, Depends, Body
from fastapi.responses import JSONResponse
from database.connect_db import connect_database
from services.response_handler import verify_bearer_token
from typing import Annotated, List, Dict
import json
from app.users.models.quiz_model import QuizSchema, UpdateProfileSchema

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
        SELECT 
        q.cover_photo , q.title, q.description,
        qq.id, qq.question, qq.question_index, qq.options, qq.correct_option, 
        qq.points, qq.duration , q.id
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


@router.get("/profile")
def profile_of_user(
    auth: dict = Depends(verify_bearer_token),
    filter: str = Query(None),
    order: str = Query(None),
):
    connection = connect_database()
    cursor = connection.cursor()
    creator_id = auth.get("id")

    try:
        get_user_detail_query = """
        SELECT u.full_name, u.username, u.photo, COUNT(q.id)
        FROM users AS u
        LEFT JOIN quizzes AS q ON q.creator_id = u.id
        WHERE u.id = %s
        GROUP BY u.id, u.full_name, u.username, u.photo
        """

        cursor.execute(get_user_detail_query, (creator_id,))
        fetched_user_data = cursor.fetchone()

        if not fetched_user_data:
            raise HTTPException(status_code=404, detail="User not found")

        (full_name, username, photo, quizzes_created) = fetched_user_data

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

        follower_count_query = """
                SELECT COUNT(*) AS follower_count
                FROM follows
                WHERE following_id = %s
                """
        cursor.execute(follower_count_query, (creator_id,))
        follower_count = cursor.fetchone()[0]

        following_count_query = """
        SELECT COUNT(*) AS following_count
        FROM follows
        WHERE follower_id =%s
        """

        cursor.execute(following_count_query, (creator_id,))

        following_count = cursor.fetchone()[0]

        return {
            "message": "Successful Response",
            "data": {
                "user_data": {
                    "username": username,
                    "full_name": full_name,
                    "photo": photo,
                    "quizzes": quizzes_created,
                    "follower": follower_count,
                    "following": following_count,
                },
                "quiz_data": result,
            },
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


@router.get("/profile/{user_id}")
def other_user_profile(
    user_id: str,
    auth: dict = Depends(verify_bearer_token),
):
    connection = connect_database()
    cursor = connection.cursor()
    logged_in_user_id = auth.get("id")

    try:
        get_user_detail_query = """
        SELECT u.full_name, u.username, u.photo, COUNT(q.id)
        FROM users AS u
        LEFT JOIN quizzes AS q ON q.creator_id = u.id
        WHERE u.id = %s
        GROUP BY u.id, u.full_name, u.username, u.photo
        """
        cursor.execute(get_user_detail_query, (user_id,))
        fetched_user_data = cursor.fetchone()

        if not fetched_user_data:
            raise HTTPException(status_code=404, detail="User not found")

        (full_name, username, photo, quizzes_created) = fetched_user_data

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
        cursor.execute(is_followed_query, (logged_in_user_id, user_id))
        is_followed = cursor.fetchone() is not None

        return {
            "message": "Successful Response",
            "data": {
                "user_data": {
                    "id": user_id,
                    "username": username,
                    "full_name": full_name,
                    "photo": photo,
                    "quizzes": quizzes_created,
                    "follower": follower_count,
                    "following": following_count,
                    "is_followed": is_followed,
                }
            },
        }

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@router.get("/profile/edit")
def get_profile_data_for_edit(auth: dict = Depends(verify_bearer_token)):
    connection = connect_database()
    cursor = connection.cursor()
    creator_id = auth.get("id")

    try:
        get_profile_data_query = """
        SELECT full_name , username , photo 
        FROM users 
        WHERE id=%s
        """

        cursor.execute(get_profile_data_query, (creator_id,))

        fetched_user_data = cursor.fetchone()

        if not fetched_user_data:
            raise HTTPException(status_code=400, detail="Not Found")

        (full_name, username, photo) = fetched_user_data

        return {
            "message": "Successfull Response",
            "data": {"full_name": full_name, "username": username, "photo": photo},
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


@router.put("/profile/edit")
def edit_profile_page(
    update_data: UpdateProfileSchema, auth: dict = Depends(verify_bearer_token)
):
    connection = connect_database()
    cursor = connection.cursor()
    creator_id = auth.get("id")

    try:
        if update_data.username:
            cursor.execute(
                "SELECT * FROM users WHERE username=%s", (update_data.username,)
            )
            existing_username = cursor.fetchone()
            if existing_username:
                raise HTTPException(status_code=400, detail="Username already exists")

        fields = []
        values = []

        if update_data.full_name is not None:
            fields.append("full_name = %s")
            values.append(update_data.full_name)

        if update_data.username is not None:
            fields.append("username = %s")
            values.append(update_data.username)

        if update_data.photo is not None:
            fields.append("photo = %s")
            values.append(update_data.photo)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        values.append(creator_id)

        update_query = f"""
        UPDATE users
        SET {', '.join(fields)}
        WHERE id = %s
        """

        cursor.execute(update_query, tuple(values))
        connection.commit()

        return {"message": "Updated User Data Successfully"}

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@router.get("/{user_id}/quizzes")
def my_quizzes(
    user_id: str,
    auth: dict = Depends(verify_bearer_token),
    filter: str = Query(None),
    order: str = Query(None),
):
    connection = connect_database()
    cursor = connection.cursor()

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

        filtering_criteria = "q.created_at" if filter == "newest" else "q.created_at"

        get_quiz_description_query = f"""
        SELECT 
            q.id,
            q.cover_photo,
            q.title,
            q.description,
            q.created_at,
            u.photo AS author_photo,
            u.full_name AS author_name,
            COUNT(DISTINCT rp.id) AS total_plays,
            COUNT(DISTINCT qq.id) AS question_count
        FROM quizzes AS q
        JOIN users AS u ON u.id = q.creator_id
        LEFT JOIN rooms r ON r.quiz_id = q.id
        LEFT JOIN room_participants rp ON rp.room_id = r.id
        LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id
        WHERE q.creator_id = %s
        GROUP BY q.id, q.cover_photo, q.title, q.description, q.created_at, u.photo, u.full_name
        ORDER BY {filtering_criteria} {order.upper()}
        """

        cursor.execute(get_quiz_description_query, (user_id,))
        fetch_all_data = cursor.fetchall()

        if not fetch_all_data:
            return {"data": []}

        result = []

        for data in fetch_all_data:
            (
                quiz_id,
                cover_photo,
                title,
                description,
                created_at,
                author_photo,
                author_name,
                total_plays,
                question_count,
            ) = data

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
                    "id": quiz_id,
                    "title": title,
                    "cover_photo": cover_photo,
                    "description": description,
                    "image": author_photo,
                    "author": author_name,
                    "plays": total_plays,
                    "date": created_at,
                    "count": question_count,
                    "questions": question_result,
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
