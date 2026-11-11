import asyncio
from fastapi import APIRouter, UploadFile, File, Depends, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.engine import get_session, async_session
from app.models.db_models import UploadedFile
from app.config import settings
import uuid
import os
import aiofiles
from sqlalchemy import select

router = APIRouter()

PARSEABLE_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".webp": "image",
    ".mp4": "video",
    ".avi": "video",
    ".mov": "video",
    ".mkv": "video",
    ".txt": "text",
    ".md": "text",
}


async def parse_file_background(file_id: str, stored_path: str, file_type: str):
    """Background task to parse uploaded file."""
    try:
        parsed_text = ""

        if file_type == "pdf":
            from app.parsers.pdf_parser import parse_pdf
            result = await asyncio.to_thread(parse_pdf, stored_path)
            parsed_text = result.text

        elif file_type == "docx":
            from app.parsers.docx_parser import parse_docx
            result = await asyncio.to_thread(parse_docx, stored_path)
            parsed_text = result.text
            if result.tables:
                parsed_text += "\n\n## 表格\n\n" + "\n\n".join(result.tables)

        elif file_type == "image":
            from app.parsers.image_parser import parse_image
            result = await parse_image(stored_path)
            parsed_text = result.text

        elif file_type == "video":
            from app.parsers.video_parser import parse_video
            result = await parse_video(stored_path)
            parsed_text = result.text

        elif file_type == "text":
            async with aiofiles.open(stored_path, "r", encoding="utf-8", errors="ignore") as f:
                parsed_text = await f.read()

        async with async_session() as db:
            stmt = select(UploadedFile).where(UploadedFile.id == file_id)
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                record.parsed_content = parsed_text
                record.parse_status = "completed"
                await db.commit()

    except Exception as e:
        async with async_session() as db:
            stmt = select(UploadedFile).where(UploadedFile.id == file_id)
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                record.parse_status = "failed"
                record.parsed_content = f"解析失败: {str(e)}"
                await db.commit()


@router.post("/file")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
    db: AsyncSession = Depends(get_session),
):
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "")[1].lower()
    stored_name = f"{file_id}{ext}"
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    stored_path = os.path.join(upload_dir, stored_name)

    async with aiofiles.open(stored_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    file_type = PARSEABLE_EXTENSIONS.get(ext, "unknown")

    record = UploadedFile(
        id=file_id,
        session_id=session_id or None,
        original_name=file.filename or "unknown",
        stored_path=stored_path,
        content_type=file.content_type or "",
        file_size=len(content),
        parse_status="processing" if file_type != "unknown" else "unsupported",
    )
    db.add(record)
    await db.commit()

    if file_type != "unknown":
        background_tasks.add_task(parse_file_background, file_id, stored_path, file_type)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "file_type": file_type,
        "status": "processing" if file_type != "unknown" else "unsupported",
    }


@router.get("/status/{file_id}")
async def get_file_status(file_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"error": "File not found"}

    return {
        "file_id": record.id,
        "filename": record.original_name,
        "status": record.parse_status,
        "has_content": bool(record.parsed_content),
    }


@router.get("/content/{file_id}")
async def get_file_content(file_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"error": "File not found"}

    return {
        "file_id": record.id,
        "filename": record.original_name,
        "status": record.parse_status,
        "content": record.parsed_content or "",
    }
