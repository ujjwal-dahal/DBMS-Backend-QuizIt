from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from typing import Annotated


class SignUpSchema(BaseModel):
    # id: Annotated[str, Field(default=None, description="ID of User")]
    full_name: Annotated[str, Field(..., description="Full name of User")]
    username: Annotated[str, Field(...)]
    email: Annotated[str, EmailStr()]
    password: Annotated[str, Field(...)]
    re_password: Annotated[str, Field(...)]

    @model_validator(mode="after")
    def field_validator(cls, model):
        password = model.password
        re_password = model.re_password

        if password != re_password:
            raise ValueError("Password donot Match")

        return model

    class Config:
        json_schema_extra = {
            "signup_demo": {
                "full_name": "User Full Name",
                "username": "Unique Username",
                "email": "username@gmail.com",
                "password": "user_password",
                "re_password": "user_password",
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

    @model_validator(mode="after")
    def check_password(cls, model):
        password = model.password
        re_password = model.re_password

        if password != re_password:
            raise ValueError("Password Didnot Match")

        return model
