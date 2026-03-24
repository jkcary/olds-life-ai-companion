"""
流式响应工具
所有面向用户的 AI 聊天均使用 SSE 流式输出，减少等待感
"""
import json
from typing import AsyncGenerator
from collections.abc import Iterator


def stream_to_sse(text_chunks: Iterator[str]) -> AsyncGenerator[str, None]:
    """将文本 chunk 转为 SSE 格式（同步迭代器包装）"""
    async def _gen():
        for chunk in text_chunks:
            yield f"data: {json.dumps({'text': chunk, 'type': 'delta'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    return _gen()


def format_sse_event(event_type: str, data: dict) -> str:
    """格式化单个 SSE 事件"""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


def format_sse_error(message: str) -> str:
    """格式化 SSE 错误事件"""
    return f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"
