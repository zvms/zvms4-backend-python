from pydantic import BaseModel, Field


class ActivityRating(BaseModel):
    id: str = Field(..., alias="_id")
    activity_id: str
    user_id: str
    general: int
    self_behavior: int
    leader: int
    similar_interest: int
