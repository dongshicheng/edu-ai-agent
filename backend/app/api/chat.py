from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.engine import get_session, async_session
from app.models.db_models import Session, Message
from app.services.chat_service import stream_chat, extract_intent
import json
import uuid
from sqlalchemy import select

router = APIRouter()


# 定义一个FastAPI接口，用来查询所有的会话列表，通常是前端聊天页/历史记录页的后端接口
# 把数据库中的所有会话按照时间倒序查询出来，并按照前端需要的字符串格式返回
@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Session).order_by(Session.updated_at.desc())
    )
    sessions = result.scalars().all()
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "createdAt": s.created_at.isoformat() if s.created_at else "",
                "updatedAt": s.updated_at.isoformat() if s.updated_at else "",
            }
            for s in sessions
        ]
    }


# 定义一个FastAPI接口，用来创建一个新的聊天会话，插入数据库，然后把新会话的ID返回给前端，前端之后就可以用这个ID继续聊天
@router.post("/sessions")
async def create_session(db: AsyncSession = Depends(get_session)):
    session = Session(id=str(uuid.uuid4()), title="新对话")
    db.add(session)
    await db.commit()
    return {"session_id": session.id}


# 定义一个FastAPI接口，用来查询指定会话的所有消息，按照时间顺序返回，用于聊天记录展示
@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else "",
            }
            for m in messages
        ]
    }


# 定义一个FastAPI接口，当用户在某个会话里继续聊天时，后端可以先判断当前会话的意图，再决定接下来该走哪条业务逻辑
@router.post("/sessions/{session_id}/intent")
async def get_intent(session_id: str, db: AsyncSession = Depends(get_session)):
    intent = await extract_intent(db, session_id)
    return {"intent": intent}


# 定义一个FastAPI接口，用来处理WebSocket连接，前端可以通过WebSocket实时发送消息给后端，后端会调用stream_chat函数生成回复，并通过WebSocket实时返回给前端
@router.websocket("/stream/{session_id}")
async def chat_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            text = raw.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": '请发送单行 JSON，例如 {"content": "你好"}',
                })
                continue
            content = data.get("content", "") if isinstance(data, dict) else ""

            async with async_session() as db:
                try:
                    async for chunk in stream_chat(db, session_id, content):
                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk,
                        })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"生成回复时出错: {str(e)}",
                    })

            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass
