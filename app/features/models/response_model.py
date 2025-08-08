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
    cover_photo: str
    author: str
    image: str
    plays: int
    count: int
    date: str


class FavouriteQuizResponseSchema(BaseModel):
    message: str
    data: List[FavouriteQuizOutputSchema]


class UserSearchOutput(BaseModel):
    id: str
    username: str
    full_name: str
    image: Optional[str]


class UserSearchResponse(BaseModel):
    message: str
    data: List[UserSearchOutput]
