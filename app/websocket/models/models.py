from pydantic import BaseModel


class AnswerData(BaseModel):
    question_id: int
    selected_option: str
    point: int
    answered_at: str
