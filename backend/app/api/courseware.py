import os
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.engine import get_session, async_session
from app.models.schemas import GenerateRequest, TaskStatus
from app.models.db_models import GenerationTask
from app.services.courseware_service import generate_courseware

router = APIRouter()


async def _run_generation(task_id: str, session_id: str, output_types: list[str]):
    async with async_session() as db:
        await generate_courseware(db, task_id, session_id, output_types)


@router.post("/generate")
async def create_generation_task(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    task_id = str(uuid.uuid4())
    task = GenerationTask(
        id=task_id,
        session_id=request.session_id,
        output_types=request.output_types,
    )
    db.add(task)
    await db.commit()

    background_tasks.add_task(
        _run_generation, task_id, request.session_id, request.output_types
    )

    return {"task_id": task_id, "status": "pending"}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "Task not found"}

    return TaskStatus(
        task_id=task.id,
        status=task.status,
        progress=task.progress / 100.0,
        result_urls={
            fmt: f"/api/v1/courseware/download/{task.id}?file_type={fmt}"
            for fmt in (task.result_paths or {})
        },
        error=task.error or None,
    )


@router.get("/download/{task_id}")
async def download_courseware(
    task_id: str,
    file_type: str = "pptx",
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task or task.status != "completed":
        return {"error": "File not ready"}

    paths = task.result_paths or {}
    file_path = paths.get(file_type)
    if not file_path or not os.path.exists(file_path):
        return {"error": "File not found"}

    media_types = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    return FileResponse(
        file_path,
        media_type=media_types.get(file_type, "application/octet-stream"),
        filename=os.path.basename(file_path),
    )


class InteractiveRequest(BaseModel):
    topic: str
    requirements: str = "创建一个与主题相关的互动小测验"


@router.post("/interactive")
async def generate_interactive(request: InteractiveRequest):
    from app.services.interactive_service import generate_interactive_html
    html = await generate_interactive_html(request.topic, request.requirements)
    return HTMLResponse(content=html)
