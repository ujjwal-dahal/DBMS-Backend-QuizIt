from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, status, HTTPException

# Project Imports
from .jwt_handler import verify_token
from jose import jwt
from helper.config import JWT_SECRET_KEY, JWT_ALGORITHM


security = HTTPBearer()


def verify_bearer_token(
    token: HTTPAuthorizationCredentials = Depends(security),
):
    actual_token = token.credentials

    payload = verify_token(actual_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token"
        )

    return payload


def verify_bearer_token_manual(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, JWT_ALGORITHM)
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
