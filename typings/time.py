from pydantic import BaseModel
from datetime import datetime
from config import (
    BASE_OFF_CAMPUS,
    OFF_TO_ON_RATE,
    MAX_EXCEED_DISCOUNT,
    ON_TO_OFF_RATE,
    BASE_ON_CAMPUS, BASE_SOCIAL_PRACTICE,
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
    def total_effective(self) -> float:
        return self.on_campus + self.off_campus + self.social_practice

    @property
    def diff(self) -> float:
        return max(BASE_ON_CAMPUS - self.on_campus, 0) + max(BASE_OFF_CAMPUS - self.off_campus, 0) + max(BASE_SOCIAL_PRACTICE - self.social_practice, 0)

    @property
    def percentage(self) -> float:
        total = BASE_ON_CAMPUS + BASE_OFF_CAMPUS + BASE_SOCIAL_PRACTICE
        return (total - self.diff) / total * 100

    @property
    def on_campus(self) -> float:
        return self.on_campus_raw + min(
            max((self.off_campus_raw - BASE_OFF_CAMPUS), 0) * OFF_TO_ON_RATE,
            MAX_EXCEED_DISCOUNT,
        )

    @property
    def off_campus(self) -> float:
        return self.off_campus_raw + min(
            max((self.on_campus_raw - BASE_ON_CAMPUS), 0) * ON_TO_OFF_RATE,
            MAX_EXCEED_DISCOUNT,
        )


class UserTimeStat(BaseModel):
    _id: str
    user: str  # ObjectId
    time: UserActivityTime
    origins: tuple[str, ActivityMode, float]
