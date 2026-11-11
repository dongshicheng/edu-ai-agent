import asyncio
import json
import os
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import TeachingIntent, SlideSpec, DocSpec
from app.models.db_models import GenerationTask
from app.services.llm_gateway import chat_completion_json
from app.services.intent_service import extract_teaching_intent
from app.services import rag_service
from app.prompts.courseware_prompts import SLIDE_GENERATION_PROMPT, DOC_GENERATION_PROMPT
from app.config import settings


def _strip_markdown_json_fence(text: str) -> str:
    """去掉 ```json ... ``` 包裹，便于 json.loads。"""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _loads_json_lenient(raw: str) -> Any:
    """解析 LLM 输出的 JSON；失败时尝试截取第一个完整 {…} 或 […]。"""
    raw = _strip_markdown_json_fence(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = raw.find(open_ch)
        end = raw.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("无法解析 LLM 返回的 JSON")


def _normalize_slides_payload(data: Any) -> list[dict]:
    """
    只接受 list[dict] 或 {\"slides\": [...]}。
    禁止对「无 slides 键的 dict」做迭代（否则会遍历到 \"subject\" 等键名，触发怪异错误）。
    """
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        slides = data.get("slides")
        if isinstance(slides, list):
            return [x for x in slides if isinstance(x, dict)]
    return []


def _dict_to_slide_spec(d: dict) -> SlideSpec:
    bullets = d.get("bullets") or []
    if not isinstance(bullets, list):
        bullets = [str(bullets)]
    bullets = [str(b) for b in bullets if b is not None]
    sn = d.get("slide_number", 1)
    try:
        sn = int(sn)
    except (TypeError, ValueError):
        sn = 1
    return SlideSpec(
        slide_number=sn,
        layout=str(d.get("layout") or "content"),
        title=str(d.get("title") or "未命名"),
        bullets=bullets,
        notes=str(d.get("notes") or ""),
        image_prompt=str(d.get("image_prompt") or ""),
    )


def _safe_filename(name: str, default: str = "courseware") -> str:
    bad = '\\/:*?"<>|\n\r\t'
    s = "".join(c for c in (name or default) if c not in bad).strip() or default
    return s[:180]


def _as_str_list(value: Any, fallback: list[str]) -> list[str]:
    if value is None:
        return list(fallback)
    if isinstance(value, list):
        return [str(x) for x in value if x is not None]
    if isinstance(value, str) and value.strip():
        return [value]
    return list(fallback)


def _as_stage_list(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, dict)]


async def _get_rag_context(intent: TeachingIntent) -> str:
    query = f"{intent.subject} {intent.topic} {' '.join(intent.key_points)}"
    try:
        results = await asyncio.to_thread(rag_service.search, query, top_k=5)
        return "\n\n".join(r["content"] for r in results if r["score"] > 0.3)
    except Exception:
        return ""


async def generate_slides(intent: TeachingIntent, context: str) -> list[SlideSpec]:
    """Generate slide specifications using LLM."""
    prompt = SLIDE_GENERATION_PROMPT.format(
        intent=intent.model_dump_json(indent=2),
        context=context or "无额外参考资料",
    )
    messages = [
        {"role": "system", "content": "你是一位专业的教学课件设计师。请严格按照JSON格式输出。"},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion_json(messages, max_tokens=8000)

    try:
        data = _loads_json_lenient(result)
        slides_list = _normalize_slides_payload(data)
        if not slides_list:
            raise ValueError("slides 为空或格式非 slides 数组")
        return [_dict_to_slide_spec(s) for s in slides_list]
    except (json.JSONDecodeError, ValueError, TypeError, Exception):
        # Return a minimal set of slides on error
        return [
            SlideSpec(slide_number=1, layout="cover", title=intent.topic,
                      bullets=[f"{intent.subject} - {intent.grade_level}"]),
            SlideSpec(slide_number=2, layout="content", title="教学目标",
                      bullets=intent.objectives or ["待补充"]),
            SlideSpec(slide_number=3, layout="summary", title="课堂总结",
                      bullets=["本节课学习了...", "重点掌握..."]),
        ]


async def generate_doc_spec(intent: TeachingIntent, context: str) -> DocSpec:
    """Generate document specification using LLM."""
    prompt = DOC_GENERATION_PROMPT.format(
        intent=intent.model_dump_json(indent=2),
        context=context or "无额外参考资料",
    )
    messages = [
        {"role": "system", "content": "你是一位专业的教学设计师。请严格按照JSON格式输出。"},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion_json(messages, max_tokens=8000)

    try:
        data = _loads_json_lenient(result)
        if not isinstance(data, dict):
            raise ValueError("教案 JSON 应为对象")
        return DocSpec(
            title=str(data.get("title") or intent.topic),
            subject=str(data.get("subject") or intent.subject),
            grade_level=str(data.get("grade_level") or intent.grade_level),
            duration=str(data.get("duration") or f"{intent.duration_minutes}分钟"),
            objectives=_as_str_list(data.get("objectives"), intent.objectives),
            key_points=_as_str_list(data.get("key_points"), intent.key_points),
            difficulty_points=_as_str_list(
                data.get("difficulty_points"), intent.difficulty_points
            ),
            teaching_process=_as_stage_list(data.get("teaching_process")),
            homework=_as_str_list(data.get("homework"), []),
            reflection=str(data.get("reflection") or ""),
        )
    except (json.JSONDecodeError, ValueError, TypeError, Exception):
        return DocSpec(
            title=intent.topic,
            subject=intent.subject,
            grade_level=intent.grade_level,
            duration=f"{intent.duration_minutes}分钟",
            objectives=intent.objectives,
            key_points=intent.key_points,
            difficulty_points=intent.difficulty_points,
        )


async def generate_courseware(
    db: AsyncSession,
    task_id: str,
    session_id: str,
    output_types: list[str],
):
    """Main courseware generation pipeline."""
    # Update task status
    result = await db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one()
    task.status = "processing"
    task.progress = 10
    await db.commit()

    try:
        # Step 1: Extract teaching intent
        intent = await extract_teaching_intent(db, session_id)
        task.progress = 25
        await db.commit()

        # Step 2: Get RAG context
        context = await _get_rag_context(intent)
        task.progress = 35
        await db.commit()

        output_dir = os.path.join(settings.upload_dir, "..", "generated", task_id)
        os.makedirs(output_dir, exist_ok=True)
        result_paths = {}

        # Step 3: Generate PPTX
        if "pptx" in output_types:
            slides = await generate_slides(intent, context)
            task.progress = 60
            await db.commit()

            from app.services.ppt_generator import generate_pptx
            pptx_path = os.path.join(
                output_dir, f"{_safe_filename(intent.topic)}.pptx"
            )
            await asyncio.to_thread(generate_pptx, slides, pptx_path)
            result_paths["pptx"] = pptx_path
            task.progress = 75
            await db.commit()

        # Step 4: Generate DOCX
        if "docx" in output_types:
            doc_spec = await generate_doc_spec(intent, context)
            task.progress = 85
            await db.commit()

            from app.services.doc_generator import generate_docx
            docx_path = os.path.join(
                output_dir, f"{_safe_filename(intent.topic, 'lesson_plan')}_教案.docx"
            )
            await asyncio.to_thread(generate_docx, doc_spec, docx_path)
            result_paths["docx"] = docx_path
            task.progress = 95
            await db.commit()

        # Done
        task.status = "completed"
        task.progress = 100
        task.result_paths = result_paths
        await db.commit()

    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        await db.commit()
