from pydantic import BaseModel, Field
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




# Схема для получения полной информации об уроке
class LessonDetailOut(BaseModel):
    id: int
    title: str
    video_url: str | None
    content: str | None
    order: int
    # Текущий прогресс пользователя в этом уроке
    current_position_sec: int = 0
    is_completed: bool = False

    class Config:
        from_attributes = True

# Схема, которую присылает фронтенд при просмотре
class VideoProgressIn(BaseModel):
    position_sec: int = Field(ge=0)
    watched_percent: int = Field(ge=0, le=100)
