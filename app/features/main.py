from fastapi import APIRouter, HTTPException, Depends

# FastAPI Projects Import
from services.response_handler import verify_bearer_token
from database.connect_db import connect_database
from services.email_send import send_email
from app.features.models.response_model import InviteOutputSchema
from app.features.models.input_schema import FollowSchema, InviteSchame
from messages.invited_user_email import invite_message

app = APIRouter()


@app.post("/follow-user")
def follow_user(data: FollowSchema, auth: dict = Depends(verify_bearer_token)):
    followed_by_user_id = auth.get("id")
    followed_to_id = data.followed_to_id
    connect = connect_database()
    cursor = connect.cursor()

    try:

        if int(followed_by_user_id) == int(followed_to_id):
            raise HTTPException(status_code=400, detail="Cannot Follow Yourself")

        cursor.execute(
            "SELECT id FROM follows WHERE follower_id = %s AND following_id = %s",
            (followed_by_user_id, followed_to_id),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Already following this user")

        insert_query = """
          INSERT INTO follows (follower_id , following_id)
          VALUES ( %s , %s) RETURNING id
          """

        cursor.execute(insert_query, (followed_by_user_id, followed_to_id))

        follow_id = cursor.fetchone()
        if not follow_id:
            raise HTTPException(status_code=400, detail="Something Went Wrong")

        follow_id = follow_id[0]

        connect.commit()

        return {"message": f"Followed to User ID : {followed_to_id}"}

    except Exception as e:
        connect.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connect.close()


@app.get("/invite-user-list", response_model=InviteOutputSchema)
def invite_user_list(auth: dict = Depends(verify_bearer_token)):
    connect = connect_database()
    cursor = connect.cursor()
    user_id = auth.get("id")

    try:
        get_all_user_query = """
            SELECT u.id, u.username, u.photo FROM users AS u
            JOIN follows AS f1 ON f1.follower_id = u.id
            JOIN follows AS f2 ON f2.following_id = u.id
            WHERE f1.following_id = %s AND f2.follower_id = %s
        """
        cursor.execute(get_all_user_query, (user_id, user_id))
        fetch_all_user = cursor.fetchall()

        if not fetch_all_user:
            return {"message": "Successful Response", "data": []}

        result = []
        for data in fetch_all_user:
            (user_id, username, photo) = data
            result.append({"user_id": user_id, "username": username, "image": photo})

        return {"message": "Successful Response", "data": result}

    except Exception as e:
        connect.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connect.close()


@app.post("/room/{room_code}/invite")
async def invite_friends(
    room_code: str, data: InviteSchame, auth: dict = Depends(verify_bearer_token)
):
    invitor_id = auth.get("id")
    invited_to_id = data.invited_to_id
    quiz_id = data.quiz_id

    connect = connect_database()
    cursor = connect.cursor()

    try:
        if str(invitor_id) == str(invited_to_id):
            raise HTTPException(status_code=400, detail="You cannot invite yourself")

        cursor.execute("SELECT id FROM rooms WHERE room_code=%s", (room_code,))

        fetch_room_id = cursor.fetchone()
        if not fetch_room_id:
            raise HTTPException(status_code=404, detail="Invalid Room Code")

        room_id = fetch_room_id[0]

        cursor.execute("SELECT full_name FROM users WHERE id=%s", (invitor_id,))

        invitor_name = cursor.fetchone()[0]

        cursor.execute("SELECT email FROM users WHERE id=%s", (invited_to_id))

        invited_to_email = cursor.fetchone()[0]

        email_body = invite_message(invitor_name, room_code, quiz_id)
        subject = """You’ve Been Invited to a Quiz Room!"""

        await send_email(
            subject=subject, to_whom=invited_to_email, body=email_body, is_html=True
        )

        cursor.execute(
            """INSERT INTO room_invites (room_id , invited_by , invited_user_id , email_sent)
            VALUES (%s,%s,%s,%s) RETURNING id
            """,
            (room_id, invitor_id, invited_to_id, True),
        )

        fetch_invite_id = cursor.fetchone()
        if not fetch_invite_id:
            raise HTTPException(status_code=400, detail="Something Went Wrong")

        connect.commit()
        return {"message": "Invite Sent"}

    except Exception as e:
        connect.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connect.close()
