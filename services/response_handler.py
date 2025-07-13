from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, status
from fastapi import HTTPException
from dotenv import load_dotenv
import os
from .jwt_handler import verify_token

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_bearer_token(
    token: str = Depends(oauth2_scheme),
):
    is_valid = verify_token(token)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token"
        )

    return True
