from pydantic import BaseModel, Field
from app.models.enums import Role


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: Role | None = None
    department_id: int | None = None
    is_active: bool | None = None


class ResetPasswordIn(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)
