from pydantic import BaseModel
from typing import List, Optional


class InviteUserSchema(BaseModel):
    user_id: int
    username: str
    image: str


class InviteOutputSchema(BaseModel):
    message: str
    data: List[InviteUserSchema]


class FavouriteQuizOutputSchema(BaseModel):
    id: str
    title: str
    description: str
    cover_photo: Optional[str] = None
    author: str
    image: Optional[str] = None
    plays: int
    question_count: int
    created_at: str
