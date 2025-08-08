from jose import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

# Project Imports
from helper.config import ALGORITHM, SECRET_KEY, ACCESS_TOKEN_EXPIRY


def get_access_token(user_info: dict, expiry_minutes: int):
    user_data = user_info.copy()

    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    user_data.update({"exp": expiry_time, "type": "access_token"})

    access_token = jwt.encode(claims=user_data, algorithm=ALGORITHM, key=SECRET_KEY)

    return access_token


def get_refresh_token(user_info: dict, expiry_time: int):
    user_data = user_info.copy()

    expiry_time = datetime.now(timezone.utc) + timedelta(days=expiry_time)
    user_data.update({"exp": expiry_time, "type": "refresh_token"})

    refresh_token = jwt.encode(claims=user_data, algorithm=ALGORITHM, key=SECRET_KEY)

    return refresh_token


def decode_jwt_token(token: str):
    decoded_token = jwt.decode(token=token, key=SECRET_KEY, algorithms=ALGORITHM)
    return decoded_token


def verify_token(token: str) -> dict | None:
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("id")

        if user_id is None:
            return None

        if datetime.now(timezone.utc).timestamp() > payload.get("exp"):
            return None

        return payload

    except Exception:
        return None


async def renew_access_token(refresh_token: str):
    try:
        user_data = decode_jwt_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Refresh Token")

    expiry_time = user_data.get("exp")

    if expiry_time is None or datetime.now(timezone.utc).timestamp() > expiry_time:
        raise HTTPException(
            status_code=401, detail="Refresh Token is Expired so Login Again"
        )

    payload = {"id": user_data.get("id")}

    new_access_token = get_access_token(payload, ACCESS_TOKEN_EXPIRY)
    return new_access_token
