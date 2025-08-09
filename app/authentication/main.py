from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
import os

# Project Imports
from .auth_models.auth_models import (
    SignUpSchema,
    ForgotPasswordSchema,
    ForgotPasswordCheckSchema,
    ResetPasswordSchema,
    EmailTokenVerifySchema,
    RenewVerifyEmailToken,
    LoginSchema,
)
from services.jwt_handler import (
    get_access_token,
    get_refresh_token,
    renew_access_token,
)
from database.connect_db import connect_database
from services.password_hashing import hash_password, match_password
from services.response_handler import verify_bearer_token
from services.email_send import send_email
from services.generate_token import generate_otp
from datetime import datetime, timezone, timedelta
from messages.verify_email import otp_email_body
from messages.reset_password import reset_password_email_body
from helper.config import (
    ACCESS_TOKEN_EXPIRY,
    REFRESH_TOKEN_EXPIRY,
    VERIFY_MAIL_EXPIRY,
    FORGOT_PASSWORD_EXPIRY,
)
from helper.oauth_config import oauth
from authlib.integrations.starlette_client import OAuthError
from helper.config import QUIZIT_URL, GOOGLE_REVOKE_URL

app = APIRouter()


@app.get("/")
def auth_index_page():
    return {
        "message": "This is Authentication API for QuizIt",
        "Backend Developer": "Ujjwal Dahal",
        "Frontend Developer": "Dharmananda Joshi",
    }


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
                status_code=409, detail="Email or Username already exist"
            )

        query = "INSERT INTO Users (full_name,username, email, hashed_password,created_at) VALUES (%s, %s, %s,%s,%s) RETURNING id"
        cursor.execute(query, (full_name, username, email, hashed_password, created_at))
        user_id = cursor.fetchone()[0]

        connection.commit()

        otp = generate_otp()

        email_body = otp_email_body(otp=otp)
        subject = "Verify Your Email"
        await send_email(subject=subject, to_whom=email, body=email_body, is_html=True)

        verify_mail_expiry_time = datetime.now(timezone.utc) + timedelta(
            minutes=VERIFY_MAIL_EXPIRY
        )

        verify_mail_query = "INSERT INTO verify_email_token (user_id , token , expiry) VALUES (%s,%s,%s)"
        cursor.execute(verify_mail_query, (user_id, otp, verify_mail_expiry_time))
        connection.commit()

        return {"message": "Signup Successful. Please verify your email."}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.post("/email-token-verify")
def email_token_verify(data: EmailTokenVerifySchema):
    try:
        connection = connect_database()
        cursor = connection.cursor()

        email = data.email
        token = data.token

        extract_query = "SELECT u.id, v.token , u.is_verified,v.expiry FROM Users as u JOIN verify_email_token as v ON u.id = v.user_id WHERE u.email=%s ORDER BY v.id DESC LIMIT 1"

        cursor.execute(extract_query, (email,))
        extracted_data = cursor.fetchone()
        print(f"Email Token Verify Extracted Data : {extracted_data}")
        if not extracted_data:
            raise HTTPException(status_code=404, detail="Invalid Email Address")

        (id, db_token, is_verified, expiry) = extracted_data

        if token != db_token:
            raise HTTPException(status_code=401, detail="Invalid or Incorrect Token")

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(status_code=401, detail="Token Expired")

        if is_verified:
            raise HTTPException(status_code=409, detail="Email already Verified")

        update_users_table = "UPDATE Users SET is_verified=%s WHERE email=%s"
        delete_verify_email_token = (
            "DELETE FROM verify_email_token WHERE user_id = %s AND token=%s"
        )
        cursor.execute(update_users_table, (True, email))
        cursor.execute(delete_verify_email_token, (id, token))
        connection.commit()

        return {"message": "Email is Verified"}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.post("/renew-verify-email-token")
async def renew_verify_email_token(data: RenewVerifyEmailToken):
    try:
        connection = connect_database()
        cursor = connection.cursor()

        email = data.email

        otp = generate_otp()

        cursor.execute("SELECT id , is_verified FROM Users WHERE email=%s", (email,))
        result = cursor.fetchone()

        if result is None:
            raise HTTPException(
                status_code=400, detail="User not Found with that Email"
            )

        (user_id, is_verified) = result

        if is_verified:
            raise HTTPException(status_code=409, detail="Email already Verified")

        cursor.execute("DELETE FROM verify_email_token WHERE user_id=%s", (user_id,))
        connection.commit()

        email_body = otp_email_body(otp)
        subject = "Verify Your Email"
        await send_email(subject=subject, to_whom=email, body=email_body, is_html=True)

        verify_mail_expiry_time = datetime.now(timezone.utc) + timedelta(
            minutes=VERIFY_MAIL_EXPIRY
        )

        verify_mail_query = "INSERT INTO verify_email_token (user_id , token , expiry) VALUES (%s,%s,%s)"
        cursor.execute(verify_mail_query, (user_id, otp, verify_mail_expiry_time))
        connection.commit()

        return {"message": "Verify Mail Token has Resend"}

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(status_code=400, detail=str(e))

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.post("/login")
def login_user(user: LoginSchema):
    """Login API"""
    connection = connect_database()
    cursor = connection.cursor()

    try:
        email = user.email
        password = user.password

        cursor.execute(
            "SELECT id,hashed_password,is_verified,full_name,username from Users WHERE email=%s",
            (email,),
        )
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Email doesnot Exist")

        user_id, hashed_password, is_verified, full_name, username = result

        if not (match_password(password, hashed_password)):
            raise HTTPException(status_code=401, detail="Invalid Password")

        if not is_verified:
            raise HTTPException(status_code=401, detail="Please Verify Your Email")

        access_token = get_access_token({"id": user_id}, ACCESS_TOKEN_EXPIRY)
        refresh_token = get_refresh_token({"id": user_id}, REFRESH_TOKEN_EXPIRY)

        return JSONResponse(
            content={
                "message": "Login Successful",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                },
            }
        )

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
            "INSERT INTO forgot_password_token (user_id, token, expiry) VALUES (%s, %s, %s)",
            (user_id, otp, token_expiry),
        )

        connection.commit()

        email_body = reset_password_email_body(token=otp)
        subject = "Reset Your Password"
        await send_email(subject=subject, to_whom=email, body=email_body, is_html=True)

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

        query = "SELECT u.id, f.token, f.expiry, u.email FROM forgot_password_token AS f JOIN users AS u ON u.id = f.user_id WHERE u.email = %s ORDER BY f.id DESC LIMIT 1;"

        cursor.execute(query, (email,))

        existing_email = cursor.fetchone()

        if not existing_email:
            raise HTTPException(status_code=404, detail="Invalid Email or Token")

        user_id, database_token, expiry_date, database_email = existing_email

        if token != database_token:
            raise HTTPException(status_code=401, detail="Invalid Token")

        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expiry_date:
            raise HTTPException(status_code=401, detail="Token Expired")

        if email != database_email:
            raise HTTPException(status_code=400, detail="Wrong Email")

        update_query = (
            "UPDATE forgot_password_token SET is_reset = %s WHERE  user_id=%s"
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

        query = "SELECT f.is_reset ,u.id FROM forgot_password_token as f JOIN Users as u ON u.id = f.user_id WHERE u.email=%s ORDER BY f.id DESC LIMIT 1"

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

        delete_query = "DELETE FROM forgot_password_token WHERE user_id=%s"
        cursor.execute(delete_query, (id,))
        connection.commit()

        return {"message": "Password has been Reset"}

    except Exception as e:
        connection.rollback()

        raise HTTPException(status_code=404, detail=str(e))

    finally:
        connection.close()
        cursor.close()


@app.get("/me")
def get_authenticated_user(auth: dict = Depends(verify_bearer_token)):
    connection = connect_database()
    cursor = connection.cursor()

    try:
        user_id = auth.get("id")

        cursor.execute(
            "SELECT id, username, email, full_name, photo FROM Users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        access_token = get_access_token({"id": user_id}, ACCESS_TOKEN_EXPIRY)
        refresh_token = get_refresh_token({"id": user_id}, REFRESH_TOKEN_EXPIRY)

        user_id, username, email, full_name, photo = user

        return JSONResponse(
            content={
                "message": "Token is valid",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                    "image": photo,
                },
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connection.close()


@app.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("auth_google")
    print("Redirect URI:", redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/google")
async def auth_google(request: Request):
    """After User Select Google Account Redirect Here"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            raise HTTPException(
                status_code=400, detail="Failed to obtain user info from Google"
            )

    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    email = user_info.get("email")
    full_name = user_info.get("name")
    picture = user_info.get("picture")

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("SELECT id, username FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if not user:
        random_password = os.urandom(16).hex()
        hashed_password = hash_password(random_password)

        cursor.execute(
            """
            INSERT INTO users (email, full_name, username, photo, auth_provider, is_verified, hashed_password, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (
                email,
                full_name,
                email.split("@")[0],
                picture,
                "google",
                True,
                hashed_password,
            ),
        )
        user_id = cursor.fetchone()[0]
        connection.commit()
    else:
        user_id = user[0]

    cursor.close()
    connection.close()

    access_token = get_access_token({"id": user_id}, expiry_minutes=ACCESS_TOKEN_EXPIRY)
    refresh_token = get_refresh_token({"id": user_id}, expiry_time=REFRESH_TOKEN_EXPIRY)

    frontend_url = f"{QUIZIT_URL}/redirect" f"?refresh_token={refresh_token}"
    return RedirectResponse(url=frontend_url)


@app.get("/logout/google")
async def logout(request: Request):
    request.session.pop("user", None)
    response = RedirectResponse(url=f"{QUIZIT_URL}")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
