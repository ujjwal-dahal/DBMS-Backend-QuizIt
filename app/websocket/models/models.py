from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AnswerSchema(BaseModel):
    question_index: int
    selected_option: int
    point: int
    answered_at: datetime
