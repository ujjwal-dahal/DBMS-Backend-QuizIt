from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class QuizQuestionSchema(BaseModel):
    question: str = Field(..., example="What is 2 + 2?")
    question_index: int = Field(..., example=1)
    options: List[str] = Field(..., example=["2", "3", "4", "5"])
    correct_option: int = Field(..., example=2)
    points: int = Field(default=1)
    duration: int = Field(default=30)


class QuizSchema(BaseModel):
    title: str = Field(..., example="Math Quiz")
    description: Optional[str] = Field(None, example="A simple math quiz.")
    cover_photo: Optional[str] = Field(None, description="Enter Cover Pic")
    is_published: Optional[bool] = Field(default=False)

    questions: List[QuizQuestionSchema] = Field(..., example=[])
    tags: List[str] = Field(..., examples=["science", "math"])


class QuizTag(str, Enum):
    gk = "GK"
    science = "Science"
    math = "Math"
    history = "History"
    geography = "Geography"
    literature = "Literature"
    technology = "Technology"
    sports = "Sports"
    arts = "Arts"
