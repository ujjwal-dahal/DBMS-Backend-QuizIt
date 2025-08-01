from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AnswerSchema(BaseModel):
    question_id: int
    selected_option: str
    point: int
    answered_at: Optional[datetime] = None
