from pydantic import BaseModel
from datetime import datetime
from config import (
    BASE_OFF_CAMPUS,
    OFF_TO_ON_RATE,
    MAX_EXCEED_DISCOUNT,
    ON_TO_OFF_RATE,
    BASE_ON_CAMPUS,
)
from typings.activity import ActivityMode


class UserActivityTime(BaseModel):
    _id: str
    user: str  # ObjectId
    on_campus_raw: float = 0.0
    off_campus_raw: float = 0.0
    social_practice: float = 0.0
    updated_at: datetime

    # Getter of `total` returns the sum of all time attributes
    @property
    def total(self) -> float:
        return self.on_campus_raw + self.off_campus_raw + self.social_practice

    @property
    def on_campus(self) -> float:
        return self.on_campus_raw + max(
            min((self.off_campus_raw - BASE_OFF_CAMPUS), 0) * OFF_TO_ON_RATE,
            MAX_EXCEED_DISCOUNT,
        )

    @property
    def off_campus(self) -> float:
        return self.off_campus_raw + max(
            min((self.on_campus_raw - BASE_ON_CAMPUS), 0) * ON_TO_OFF_RATE,
            MAX_EXCEED_DISCOUNT,
        )


class UserTimeStat(BaseModel):
    _id: str
    user: str  # ObjectId
    time: UserActivityTime
    origins: tuple[str, ActivityMode, float]
