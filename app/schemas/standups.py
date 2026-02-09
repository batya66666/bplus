from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    day_number: int = Field(ge=1)
    text_done: str
    text_plan: str
    text_blockers: str


class ReportUpdate(BaseModel):
    text_done: str
    text_plan: str
    text_blockers: str


class MentorDecisionIn(BaseModel):
    action: str  # "ACCEPTED" | "REVISION"
    mentor_comment: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    user_id: int
    day_number: int
    text_done: str
    text_plan: str
    text_blockers: str
    status: str
    mentor_comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
