from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class FollowSchema(BaseModel):
    followed_to_id: str


class InviteSchame(BaseModel):
    quiz_id: str
    invited_to_id: str


class FavouriteQuizSchema(BaseModel):
    quiz_id: str


class EncryptedDataSchema(BaseModel):
    encrypted_text: str


class ContactUsSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    question: str = Field(..., min_length=1)


class FeedbackSchema(BaseModel):
    reaction: str = Field(..., min_length=1, max_length=100)
    feedback_message: str = Field(..., min_length=1)
