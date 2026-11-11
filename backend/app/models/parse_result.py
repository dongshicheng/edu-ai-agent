from pydantic import BaseModel, Field


class ParseResult(BaseModel):
    text: str = ""
    tables: list[str] = Field(default_factory=list)
    images: list[dict] = Field(default_factory=list)  # [{description, path}]
    metadata: dict = Field(default_factory=dict)
    source_type: str = ""  # pdf, docx, image, video
    page_count: int = 0
