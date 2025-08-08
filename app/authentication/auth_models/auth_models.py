from pydantic import BaseModel, EmailStr, Field, root_validator
from typing import Annotated


class SignUpSchema(BaseModel):
    full_name: Annotated[str, Field(..., description="Full name of User")]
    username: Annotated[str, Field(...)]
    email: Annotated[str, EmailStr()]
    password: Annotated[str, Field(...)]
    re_password: Annotated[str, Field(...)]

    @root_validator
    def check_password_match(cls, values):
        password = values.get("password")
        re_password = values.get("re_password")

        if password != re_password:
            raise ValueError("Password do not match")

        return values

    class Config:
        schema_extra = {
            "example": {
                "full_name": "User Full Name",
                "username": "Unique Username",
                "email": "username@gmail.com",
                "password": "user_password",
                "re_password": "user_password",
            }
        }


class LoginSchema(BaseModel):
    email: Annotated[str, EmailStr()]
    password: Annotated[str, Field(...)]

    model_config = {
        "json_schema_extra": {
            "example": {"email": "ram@gmail.com", "password": "ram123"}
        }
    }


class EmailTokenVerifySchema(BaseModel):
    email: Annotated[str, EmailStr()]
    token: Annotated[str, Field(...)]


class RenewVerifyEmailToken(BaseModel):
    email: Annotated[str, EmailStr()]


class ForgotPasswordSchema(BaseModel):
    email: Annotated[str, EmailStr()]


class ForgotPasswordCheckSchema(BaseModel):
    email: Annotated[str, EmailStr()]
    token: Annotated[str, Field(...)]


class ResetPasswordSchema(BaseModel):
    email: Annotated[str, EmailStr()]
    password: Annotated[str, Field(...)]
    re_password: Annotated[str, Field(...)]

    @root_validator
    def check_password(cls, values):
        password = values.get("password")
        re_password = values.get("re_password")

        if password != re_password:
            raise ValueError("Password did not match")
        return values
