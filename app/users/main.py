from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form
from database.connect_db import connect_database
from services.response_handler import verify_bearer_token
import json
from cloudinary.uploader import upload as cloudinary_upload
from services.cloudinary_config import configure_cloudinary
from typing import Optional, Annotated
import uuid

# Project Imports
from app.users.models.quiz_model import QuestionUpdate, QuizUpdateSchema

router = APIRouter()
configure_cloudinary()


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
            q.cover_photo,
            q.title,
            q.description,
            qq.id,
            qq.question,
            qq.question_index,
            qq.options,
            qq.correct_option,
            qq.points,
            qq.duration,
            q.id
        FROM quizzes AS q
        JOIN users AS u ON u.id = q.creator_id
        JOIN quiz_questions AS qq ON qq.quiz_id = q.id
        WHERE u.id = %s AND q.id = %s
        """
        cursor.execute(query, (user_id, quiz_id))
        fetched_data = cursor.fetchall()

        if not fetched_data:
            raise HTTPException(status_code=404, detail="Not Found")

        tags_query = """
        SELECT t.name
        FROM tags AS t
        JOIN quiz_tags AS qt ON qt.tag_id = t.id
        WHERE qt.quiz_id = %s
        """
        cursor.execute(tags_query, (quiz_id,))
        tags_data = cursor.fetchall()
        tags = [tag[0] for tag in tags_data]

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
                "tags": tags,
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
async def edit_user_quiz(
    quiz_id: int,
    title: str = Form(...),
    description: str = Form(None),
    cover_photo: UploadFile | None = File(None),
    questions: str = Form(...),
    tags: str = Form(...),
    user: dict = Depends(verify_bearer_token),
):
    user_id = user.get("id")
    connection = connect_database()
    cursor = connection.cursor()

    try:
        questions_data = json.loads(questions)
        tags_data = json.loads(tags)

        if cover_photo:
            file_bytes = await cover_photo.read()
            unique_public_id = f"quiz_cover_{user_id}_{uuid.uuid4().hex}"
            upload_result = cloudinary_upload(
                file_bytes,
                folder=f"QuizIt/Quiz_Cover_Photos/User_{user_id}_Quiz",
                public_id=unique_public_id,
                overwrite=False,
            )
            cover_photo_url = upload_result.get("secure_url")
        else:
            cursor.execute("SELECT cover_photo FROM quizzes WHERE id=%s", (quiz_id,))
            result = cursor.fetchone()
            cover_photo_url = result[0] if result else None

        update_query = """
            UPDATE quizzes
            SET cover_photo = %s,
                title = %s,
                description = %s
            WHERE id = %s AND creator_id = %s
        """
        cursor.execute(
            update_query, (cover_photo_url, title, description, quiz_id, user_id)
        )

        existing_question_ids = []
        for q in questions_data:
            if q.get("id"):
                cursor.execute(
                    """
                    UPDATE quiz_questions
                    SET question = %s,
                        question_index = %s,
                        options = %s,
                        correct_option = %s,
                        points = %s,
                        duration = %s
                    WHERE id = %s AND quiz_id = %s
                    """,
                    (
                        q["question"],
                        q["question_index"],
                        json.dumps(q["options"]),
                        q["correct_option"],
                        q.get("points", 1),
                        q.get("duration", 30),
                        q["id"],
                        quiz_id,
                    ),
                )
                existing_question_ids.append(q["id"])
            else:
                cursor.execute(
                    """
                    INSERT INTO quiz_questions
                    (question, question_index, options, correct_option, points, duration, quiz_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        q["question"],
                        q["question_index"],
                        json.dumps(q["options"]),
                        q["correct_option"],
                        q.get("points", 1),
                        q.get("duration", 30),
                        quiz_id,
                    ),
                )
                new_id = cursor.fetchone()[0]
                existing_question_ids.append(new_id)

        if existing_question_ids:
            cursor.execute(
                "DELETE FROM quiz_questions WHERE quiz_id = %s AND id NOT IN %s",
                (quiz_id, tuple(existing_question_ids)),
            )
        else:
            cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (quiz_id,))

        tag_ids = []
        for tag_name in tags_data:
            cursor.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
            tag_row = cursor.fetchone()
            if tag_row:
                tag_ids.append(tag_row[0])
            else:
                cursor.execute(
                    "INSERT INTO tags (name) VALUES (%s) RETURNING id", (tag_name,)
                )
                new_tag_id = cursor.fetchone()[0]
                tag_ids.append(new_tag_id)

        cursor.execute("DELETE FROM quiz_tags WHERE quiz_id = %s", (quiz_id,))

        for tid in tag_ids:
            cursor.execute(
                "INSERT INTO quiz_tags (quiz_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (quiz_id, tid),
            )

        connection.commit()

        return {"message": "Quiz, questions and tags updated successfully"}

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
        cursor.execute("SELECT id, creator_id FROM quizzes WHERE id = %s", (quiz_id,))
        quiz = cursor.fetchone()

        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        quiz_id_db, creator_id = quiz

        if creator_id != auth.get("id"):
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this quiz"
            )

        cursor.execute(
            """
            DELETE FROM room_answers 
            WHERE question_id IN (SELECT id FROM quiz_questions WHERE quiz_id = %s)
            """,
            (quiz_id,),
        )

        cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (quiz_id,))

        cursor.execute("DELETE FROM quiz_tags WHERE quiz_id = %s", (quiz_id,))

        cursor.execute("DELETE FROM quizzes WHERE id = %s", (quiz_id,))

        connection.commit()

        return {"message": "Quiz and related data deleted successfully"}

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
async def edit_profile_page(
    full_name: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    auth: dict = Depends(verify_bearer_token),
):
    connection = connect_database()
    cursor = connection.cursor()
    creator_id = auth.get("id")

    photo_url = None

    try:
        if username:
            cursor.execute(
                "SELECT * FROM users WHERE username=%s AND id != %s",
                (username, creator_id),
            )
            existing_username = cursor.fetchone()
            if existing_username:
                raise HTTPException(status_code=400, detail="Username already exists")

        fields = []
        values = []

        if full_name is not None:
            fields.append("full_name = %s")
            values.append(full_name)

        if username is not None:
            fields.append("username = %s")
            values.append(username)

        if photo is not None:
            file_bytes = await photo.read()

            unique_public_id = f"user_{creator_id}_{uuid.uuid4().hex}"

            upload_result = cloudinary_upload(
                file_bytes,
                folder=f"QuizIt/Profile_Pictures/User_ID_{creator_id}_Profile",
                public_id=unique_public_id,
                overwrite=False,
            )

            photo_url = upload_result.get("secure_url")

            if not photo_url:
                raise HTTPException(status_code=500, detail="Failed to upload photo")

            fields.append("photo = %s")
            values.append(photo_url)

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

        return {
            "message": "Updated User Data Successfully",
            "photo_url": photo_url,
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
