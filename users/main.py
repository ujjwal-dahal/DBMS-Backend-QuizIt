from fastapi import APIRouter, HTTPException, Path, Depends
from database.connect_db import connect_database
from services.response_handler import verify_bearer_token

router = APIRouter()


@router.get("/{parms}")
def get_users(
    parms: str = Path(..., description="Enter ID of User Here"),
    auth: bool = Depends(verify_bearer_token),
):
    connection = connect_database()
    cursor = connection.cursor()
    try:

        if parms.isdigit():
            query = (
                "SELECT id ,full_name, email, username, photo FROM Users WHERE id=%s"
            )
            cursor.execute(query, (int(parms),))
        else:
            query = "SELECT id ,full_name, email, username, photo FROM Users WHERE username=%s"
            cursor.execute(query, (parms,))

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

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(status_code=400, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
