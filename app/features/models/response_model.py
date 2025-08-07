from pydantic import BaseModel
from typing import List


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
    cover_photo: str
