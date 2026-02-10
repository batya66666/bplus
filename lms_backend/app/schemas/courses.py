from pydantic import BaseModel, Field
from datetime import datetime


class CourseOut(BaseModel):
    id: int
    title: str
    description: str | None
    is_mandatory: bool
    deadline_days: int

    class Config:
        from_attributes = True


class EnrollmentOut(BaseModel):
    course_id: int
    status: str
    progress_percent: int
    deadline_at: datetime | None

    class Config:
        from_attributes = True


class VideoProgressIn(BaseModel):
    position_sec: int = Field(ge=0)
    watched_percent: int = Field(ge=0, le=100)
