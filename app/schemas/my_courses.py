from pydantic import BaseModel
from datetime import datetime

class LessonOut(BaseModel):
    id: int
    order: int
    title: str
    is_completed: bool

    class Config:
        from_attributes = True

class MyCourseOut(BaseModel):
    course_id: int
    title: str
    description: str | None = None
    is_mandatory: bool
    status: str
    progress_percent: int
    deadline_at: datetime | None = None
    lessons: list[LessonOut]

class CompleteLessonIn(BaseModel):
    lesson_id: int
    completed: bool = True
