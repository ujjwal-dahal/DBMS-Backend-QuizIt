from pydantic import BaseModel


class FollowSchema(BaseModel):
    followed_to_id: str


class InviteSchame(BaseModel):
    quiz_id: str
    invited_to_id: str


class FavouriteQuizSchema(BaseModel):
    quiz_id: str


class EncryptedDataSchema(BaseModel):
    encrypted_text: str
