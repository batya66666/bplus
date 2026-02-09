from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class DepartmentOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
