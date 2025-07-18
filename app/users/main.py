from fastapi import APIRouter, HTTPException, Query, Depends
from database.connect_db import connect_database
from services.response_handler import verify_bearer_token
from typing import Annotated

router = APIRouter()


@router.get("/")
def get_user(
    user_id: int = Query(None, description="Enter User ID"),
    username: str = Query(None, description="Enter Username"),
    auth: bool = Depends(verify_bearer_token),
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
