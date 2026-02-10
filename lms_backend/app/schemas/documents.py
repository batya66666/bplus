from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    title: str
    file_url: str
    category: str
    access_level: str

    class Config:
        from_attributes = True
