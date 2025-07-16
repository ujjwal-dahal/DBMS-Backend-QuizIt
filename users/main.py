from fastapi import APIRouter, HTTPException, Path, Depends
from database.connect_db import connect_database
from services.response_handler import verify_bearer_token

router = APIRouter()


@router.get("/{user_id}")
def get_users(
    user_id: str = Path(..., description="Enter ID of User Here"),
    auth: bool = Depends(verify_bearer_token),  # 🔒 Protected Route
):
    try:
        connection = connect_database()
        cursor = connection.cursor()

        query = "SELECT email, username, photo FROM Users WHERE id=%s"
        cursor.execute(query, (user_id,))

        user = cursor.fetchone()

        if user is None:
            raise HTTPException(status_code=404, detail="User not Found")

        (email, username, photo) = user

        return {"message": {"username": username, "email": email, "photo": photo}}

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(status_code=400, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
