import asyncio
import json
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import Session, Message
from app.services.llm_gateway import chat_completion_stream, chat_completion_json
from app.services import rag_service
from app.prompts.teaching_assistant import SYSTEM_PROMPT, INTENT_EXTRACTION_PROMPT


async def get_or_create_session(db: AsyncSession, session_id: str) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        session = Session(id=session_id, title="新对话")
        db.add(session)
        await db.commit()
    return session


async def get_message_history(db: AsyncSession, session_id: str) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]


async def save_message(db: AsyncSession, session_id: str, role: str, content: str) -> Message:
    msg = Message(session_id=session_id, role=role, content=content)
    db.add(msg)
    await db.commit()
    return msg


def build_context_messages(
    history: list[dict],
    user_content: str,
    rag_context: str = "",
) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if rag_context:
        messages.append({
            "role": "system",
            "content": f"以下是从知识库中检索到的相关参考资料：\n\n{rag_context}\n\n请在回答中适当引用这些内容。",
        })

    # Keep last 20 messages for context
    for msg in history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_content})
    return messages


async def get_rag_context(query: str) -> str:
    try:
        results = await asyncio.to_thread(rag_service.search, query, top_k=3)
        if not results:
            return ""
        context_parts = []
        for r in results:
            if r["score"] > 0.3:
                source = r["metadata"].get("source", "未知来源")
                context_parts.append(f"[来源: {source}]\n{r['content']}")
        return "\n\n---\n\n".join(context_parts)
    except Exception:
        return ""


async def stream_chat(
    db: AsyncSession,
    session_id: str,
    user_content: str,
) -> AsyncGenerator[str, None]:
    """Stream a chat response, saving messages to DB."""
    await save_message(db, session_id, "user", user_content)

    history = await get_message_history(db, session_id)

    # RAG context retrieval
    rag_context = await get_rag_context(user_content)

    messages = build_context_messages(history[:-1], user_content, rag_context)

    full_response = ""
    async for chunk in chat_completion_stream(messages):
        full_response += chunk
        yield chunk

    await save_message(db, session_id, "assistant", full_response)

    # Update session title from first message
    if len(history) <= 1:
        title = user_content[:30] + ("..." if len(user_content) > 30 else "")
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.title = title
            await db.commit()


async def extract_intent(db: AsyncSession, session_id: str) -> dict:
    """Extract structured teaching intent from conversation history."""
    history = await get_message_history(db, session_id)
    conversation = "\n".join(
        f"{'教师' if m['role'] == 'user' else 'AI助手'}: {m['content']}"
        for m in history
    )
    prompt = INTENT_EXTRACTION_PROMPT.format(conversation=conversation)
    messages = [
        {"role": "system", "content": "你是一个教学意图分析专家。请严格按照JSON格式输出。"},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion_json(messages)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"error": "Failed to parse intent", "raw": result}
