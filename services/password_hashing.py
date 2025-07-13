from passlib.context import CryptContext


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(user_password: str) -> str:
    hashed_password = password_context.hash(user_password)
    return hashed_password


def match_password(user_password: str, hashed_password: str) -> bool:
    is_match = password_context.verify(user_password, hashed_password)
    return is_match
