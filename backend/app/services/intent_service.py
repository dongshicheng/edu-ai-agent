import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import Message, UploadedFile
from app.models.schemas import TeachingIntent
from app.services.llm_gateway import chat_completion_json
from app.prompts.teaching_assistant import INTENT_EXTRACTION_PROMPT


async def extract_teaching_intent(
    db: AsyncSession, session_id: str
) -> TeachingIntent:
    """Extract structured teaching intent from conversation history and uploaded files."""
    # Get conversation history
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    conversation = "\n".join(
        f"{'教师' if m.role == 'user' else 'AI助手'}: {m.content}"
        for m in messages
    )

    # Get uploaded file summaries
    file_result = await db.execute(
        select(UploadedFile)
        .where(UploadedFile.session_id == session_id)
        .where(UploadedFile.parse_status == "completed")
    )
    files = file_result.scalars().all()

    file_context = ""
    if files:
        file_summaries = []
        for f in files:
            summary = (f.parsed_content or "")[:500]
            file_summaries.append(f"[{f.original_name}]: {summary}")
        file_context = "\n\n上传的参考资料摘要：\n" + "\n".join(file_summaries)

    prompt = INTENT_EXTRACTION_PROMPT.format(
        conversation=conversation + file_context
    )

    llm_messages = [
        {"role": "system", "content": "你是一个教学意图分析专家。请严格按照JSON格式输出。"},
        {"role": "user", "content": prompt},
    ]

    result_str = await chat_completion_json(llm_messages)

    try:
        data = json.loads(result_str)
        return TeachingIntent(**data)
    except (json.JSONDecodeError, Exception):
        return TeachingIntent(
            subject="未知",
            topic="未知",
        )
