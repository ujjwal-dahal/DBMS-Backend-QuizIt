from fastapi import APIRouter, HTTPException, Depends
from .auth_models.auth_models import (
    SignUpSchema,
    ForgotPasswordSchema,
    ForgotPasswordCheckSchema,
    ResetPasswordSchema,
)
from services.jwt_handler import (
    get_access_token,
    get_refresh_token,
    renew_access_token,
)
from jose import jwt
from database.connect_db import connect_database
from services.password_hashing import hash_password, match_password
from services.response_handler import verify_bearer_token
from services.email_send import send_email
from dotenv import load_dotenv
import os
from services.generate_token import generate_token_jwt, generate_otp
from datetime import datetime, timezone, timedelta
from fastapi.security import OAuth2PasswordRequestForm

load_dotenv()

app = APIRouter()

ACCESS_TOKEN_EXPIRY = 15  # 15 Minutes
REFRESH_TOKEN_EXPIRY = 1  # 1 Days

VERIFY_MAIL_EXPIRY = 2

FORGOT_PASSWORD_EXPIRY = 5

TOKEN_SECRET = os.getenv("TOKEN_SECRET")
TOKEN_ALGO = os.getenv("TOKEN_ALGO")

PROTOCOL = os.getenv("PROTOCOL")
DOMAIN = os.getenv("DOMAIN")
PORT_NUMBER = int(os.getenv("PORT_NUMBER"))
PATH = os.getenv("VERIFY_EMAIL_PATH")


@app.get("/")
def auth_index_page():
    return {"message": "This is auth page"}


@app.get("/verify-email")
def verify_email(token: str):
    """This is Verify Email Page Where Verification of Email happen After Sinup"""
    token_data = jwt.decode(token, key=TOKEN_SECRET, algorithms=TOKEN_ALGO)

    user_id = token_data.get("payload")
    print(f"User ID {user_id}")
    if token_data is None:
        raise HTTPException(status_code=404, detail="Invalid Token")

    if datetime.now(timezone.utc).timestamp() > token_data.get("expiry"):
        raise HTTPException(status_code=404, detail="Token is Expire")

    connection = connect_database()
    cursor = connection.cursor()

    try:
        query = "UPDATE Users SET is_verified=%s WHERE id=%s"
        cursor.execute(query, (True, user_id))

        connection.commit()
        return {"message": "Email Verified"}

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/signup")
async def signup_user(user: SignUpSchema):
    """Signup API"""
    connection = connect_database()
    cursor = connection.cursor()

    try:
        full_name = user.full_name
        username = user.username
        email = user.email
        password = user.password
        hashed_password = hash_password(password)
        created_at = datetime.now(timezone.utc)

        cursor.execute("SELECT * from Users WHERE email=%s", (email,))
        email_exist = cursor.fetchone()

        cursor.execute("SELECT * FROM Users WHERE username=%s", (username,))
        username_exist = cursor.fetchone()

        if email_exist or username_exist:
            raise HTTPException(
                status_code=401, detail="Email or Username already exist"
            )

        query = "INSERT INTO Users (full_name,username, email, hashed_password,created_at) VALUES (%s, %s, %s,%s,%s) RETURNING id"
        cursor.execute(query, (full_name, username, email, hashed_password, created_at))
        user_id = cursor.fetchone()[0]

        connection.commit()

        generated_token = generate_token_jwt(user_id, VERIFY_MAIL_EXPIRY)
        URL = f"{PROTOCOL}://{DOMAIN}:{PORT_NUMBER}/{PATH}?token={generated_token}"

        email_body = f"To Verify Your Email Click Here : {URL}"
        await send_email(subject="Verify Email", to_whom=email, body=email_body)

        return {"message": "Signup Successful. Please verify your email."}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.post("/login")
def login_user(user: OAuth2PasswordRequestForm = Depends()):
    """Login API"""
    connection = connect_database()
    cursor = connection.cursor()

    try:
        email = user.username
        password = user.password

        cursor.execute(
            "SELECT id,hashed_password,is_verified from Users WHERE email=%s", (email,)
        )
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Email doesnot Exist")

        user_id, hashed_password, is_verified = result

        if not (match_password(password, hashed_password)):
            raise HTTPException(status_code=401, detail="Invalid Password")

        if not is_verified:
            raise HTTPException(status_code=401, detail="Please Verify Your Email")

        access_token = get_access_token({"id": user_id}, ACCESS_TOKEN_EXPIRY)
        refresh_token = get_refresh_token({"id": user_id}, REFRESH_TOKEN_EXPIRY)

        return {"token": {"access_token": access_token, "refresh_token": refresh_token}}

    except Exception as e:
        connection.rollback()

        raise HTTPException(status_code=404, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.post("/renew-access")
async def new_access_token(refresh_token: str):
    access_token = await renew_access_token(refresh_token)
    return {"access_token": access_token}


@app.get("/protected-route")
def protected_route(verified: bool = Depends(verify_bearer_token)):
    return {"message": "You are Authorized!"}


@app.post("/forgot-password")
async def forgot_password(data: ForgotPasswordSchema):
    try:
        connection = connect_database()
        cursor = connection.cursor()

        email = data.email
        query = "SELECT * FROM Users WHERE email=%s"
        cursor.execute(query, (email,))
        existing_email = cursor.fetchone()

        if not existing_email:
            raise HTTPException(status_code=404, detail="Invalid Email")

        otp = generate_otp()
        token_expiry = datetime.now(timezone.utc) + timedelta(
            minutes=FORGOT_PASSWORD_EXPIRY
        )

        cursor.execute("SELECT id FROM Users WHERE email=%s", (email,))
        user_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO forgot_password_token (users_id, token, expiry) VALUES (%s, %s, %s)",
            (user_id, otp, token_expiry),
        )

        connection.commit()

        email_body = f"To Reset Your Password Enter This Token : {otp}"
        await send_email(subject="Reset Password", to_whom=email, body=email_body)

        return {"message": "Token Has Sent to Your Email"}
    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.post("/forgot-password-token")
def forgot_password_token(data: ForgotPasswordCheckSchema):
    try:
        connection = connect_database()
        cursor = connection.cursor()

        token = data.token
        email = data.email

        query = "SELECT u.id, f.token, f.expiry, u.email FROM forgot_password_token AS f JOIN users AS u ON u.id = f.users_id WHERE u.email = %s ORDER BY f.id DESC LIMIT 1;"

        cursor.execute(query, (email,))

        existing_email = cursor.fetchone()

        if not existing_email:
            raise HTTPException(status_code=404, detail="Invalid Email")

        user_id, database_token, expiry_date, database_email = existing_email

        expiry_date = expiry_date.replace(tzinfo=timezone.utc)

        if token != database_token:
            raise HTTPException(status_code=404, detail="Invalid Token")

        if datetime.now(timezone.utc) > expiry_date:
            raise HTTPException(status_code=404, detail="Token Expired")

        if email != database_email:
            raise HTTPException(status_code=404, detail="Wrong Email")

        update_query = (
            "UPDATE forgot_password_token SET is_reset = %s WHERE  users_id=%s"
        )
        cursor.execute(update_query, (True, user_id))

        connection.commit()

        return {"message": "Valid Token Now You Can Reset Password"}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.post("/reset-password")
def reset_password(data: ResetPasswordSchema):
    try:
        print(f"Data : {data}")
        connection = connect_database()
        cursor = connection.cursor()

        password = data.password
        email = data.email
        print(f"Password : {password} Email : {email}")

        query = "SELECT f.is_reset ,u.id FROM forgot_password_token as f JOIN Users as u ON u.id = f.users_id WHERE u.email=%s"

        cursor.execute(query, (email,))

        existing_data = cursor.fetchone()

        if not existing_data:
            raise HTTPException(status_code=404, detail="Invalid Email")

        (is_reset, id) = existing_data

        if not is_reset:
            raise HTTPException(
                status_code=404, detail="You are not allowed to Reset Password"
            )

        hashed_password = hash_password(password)

        update_query = "UPDATE Users SET hashed_password=%s WHERE email=%s"
        cursor.execute(update_query, (hashed_password, email))
        connection.commit()

        delete_query = "DELETE FROM forgot_password_token WHERE users_id=%s"
        cursor.execute(delete_query, (id,))
        connection.commit()

        return {"message": "Password has been Reset"}

    except Exception as e:
        connection.rollback()

        raise HTTPException(status_code=404, detail=str(e))

    finally:
        connection.close()
        cursor.close()
