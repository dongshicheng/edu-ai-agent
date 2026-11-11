from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class ChatMessage(BaseModel):
    content: str
    role: MessageRole = MessageRole.user
    files: list[str] = Field(default_factory=list)

class SessionCreate(BaseModel):
    title: str = "新对话"

class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

class MessageResponse(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str
    status: str = "uploaded"

class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    collection: str = "default"

class SearchResult(BaseModel):
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)

class TeachingIntent(BaseModel):
    subject: str = ""
    topic: str = ""
    grade_level: str = ""
    duration_minutes: int = 45
    objectives: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    difficulty_points: list[str] = Field(default_factory=list)
    teaching_style: str = "讲授式"
    interactive_elements: list[str] = Field(default_factory=list)

class SlideSpec(BaseModel):
    slide_number: int
    layout: str = "content"
    title: str
    bullets: list[str] = Field(default_factory=list)
    notes: str = ""
    image_prompt: str = ""

class DocSpec(BaseModel):
    title: str
    subject: str
    grade_level: str
    duration: str
    objectives: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    difficulty_points: list[str] = Field(default_factory=list)
    teaching_process: list[dict] = Field(default_factory=list)
    homework: list[str] = Field(default_factory=list)
    reflection: str = ""

class GenerateRequest(BaseModel):
    session_id: str
    output_types: list[str] = Field(default=["pptx", "docx"])

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    result_urls: dict = Field(default_factory=dict)
    error: str | None = None
