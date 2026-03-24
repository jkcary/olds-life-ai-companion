"""
情感陪伴 API 路由
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.schema import get_db
from app.modules.companion.chat import chat_stream, chat_non_stream

router = APIRouter(prefix="/chat", tags=["情感陪伴"])


class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: list[dict] = []


@router.post("/stream")
async def stream_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    流式情感陪伴对话
    返回 SSE 事件流：delta(文本片段) | tool_call | done | error
    """
    return StreamingResponse(
        chat_stream(req.user_id, req.message, req.history, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/message")
async def send_message(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """非流式对话（适用于后台任务）"""
    reply = await chat_non_stream(req.user_id, req.message, req.history, db)
    return {"reply": reply, "user_id": req.user_id}
