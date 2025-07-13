from jose import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import random

load_dotenv()


TOKEN_SECRET = os.getenv("TOKEN_SECRET")
TOKEN_ALGO = os.getenv("TOKEN_ALGO")


def generate_token_jwt(payload: str, expiry_minute):
    expiry_time = (
        datetime.now(timezone.utc) + timedelta(minutes=expiry_minute)
    ).timestamp()

    payload = {"payload": payload, "expiry": expiry_time}

    if not TOKEN_ALGO:
        raise ValueError("TOKEN_ALGO is not set in .env file.")

    token = jwt.encode(claims=payload, key=TOKEN_SECRET, algorithm=TOKEN_ALGO)

    return token


def generate_otp():
    otp = random.randint(100000, 999999)

    return otp
