from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.engine import init_db
from app.api import chat, upload, knowledge, courseware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown

# 初始化一个FastAPI应用实例，并设置应用的标题、版本和生命周期管理器
app = FastAPI(
    title="AI 互动式教学智能体",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置跨域资源共享（CORS）中间件，允许来自指定来源的请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 将不同的API路由器包含到FastAPI应用中，并为每个路由器设置前缀和标签
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(courseware.router, prefix="/api/v1/courseware", tags=["courseware"])

# 定义一个健康检查的路由，用于检查服务的状态
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "edu-ai-agent"}
