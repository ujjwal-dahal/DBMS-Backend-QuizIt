from pydantic import BaseModel
from typing import List


class AnswerResponseSchema(BaseModel):
    answer_id: int
    question_show_id: int
    is_correct: bool


class LeaderboardUser(BaseModel):
    id: int
    name: str
    image: str | None
    rank: int
    score: int


class LeaderboardResponse(BaseModel):
    message: str
    user_score: List[LeaderboardUser]
