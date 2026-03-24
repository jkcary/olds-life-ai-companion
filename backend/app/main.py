"""
银龄AI伴伴 — FastAPI 主应用
AI 原生架构：每个请求都由 Claude 驱动决策，非规则引擎

启动：uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.schema import init_db
from app.api import chat, health, safety


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_db()
    print("✅ 银龄AI伴伴后端启动成功")
    print(f"📖 API 文档: http://localhost:8000/docs")
    yield
    print("👋 服务关闭")


app = FastAPI(
    title="银龄AI伴伴 API",
    description="""
## 夕阳伴侣·银龄AI伴伴后端服务

**AI 原生架构** — 由 Claude Opus 4.6 驱动的老年人 AI 生活管家

### 核心模块
- 🤝 **情感陪伴**：流式 AI 聊天，Claude 主动记忆用户信息，检测并响应情绪变化
- 🏥 **健康医疗**：adaptive thinking 深度推理症状，工具调用健康档案和药物数据库
- 🛡️ **安全防护**：两阶段 AI 防诈骗检测（Haiku 初筛 → Opus 深度分析）
- 🆘 **SOS 急救**：一键触发紧急求救，自动通知家人

### AI 特性
- Claude Opus 4.6 主力模型（自适应思考）
- Claude Haiku 4.5 快速模型（低延迟分类）
- SSE 流式输出（实时响应感）
- 结构化输出（保证 JSON 格式一致性）
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — 允许 Flutter Web / Mobile 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(safety.router, prefix="/api/v1")


@app.get("/", tags=["系统"])
async def root():
    return {
        "service": "银龄AI伴伴后端",
        "version": "1.0.0",
        "status": "running",
        "ai_model": "claude-opus-4-6",
        "docs": "/docs",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "healthy"}
