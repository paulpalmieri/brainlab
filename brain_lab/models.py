from pydantic import BaseModel, Field


class Note(BaseModel):
    id: str
    title: str
    body: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str

