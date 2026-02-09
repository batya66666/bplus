from pydantic import BaseModel, Field
from app.models.enums import Role


class UserCreate(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: Role = Role.EMPLOYEE
    department_id: int | None = None
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department_id: int | None
    is_active: bool

    class Config:
        from_attributes = True
