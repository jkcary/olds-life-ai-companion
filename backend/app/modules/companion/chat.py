"""
情感陪伴核心模块
AI 原生设计：
  - 支持多供应商（Anthropic/OpenAI/Kimi/DeepSeek/Grok/MiniMax）
  - Anthropic 模式：Claude 主动调用记忆工具、检测情绪
  - 其他供应商：纯对话模式（无工具调用），同样流式输出
  - 所有回复通过 SSE 流式输出，让老人感受实时陪伴
"""
import json
from datetime import datetime
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

import anthropic

from app.core.claude_client import get_client, MODEL_PRIMARY, MAX_TOKENS_CHAT
from app.core.ai_provider import get_active_provider, chat_stream as provider_chat_stream
from app.core.system_prompts import COMPANION_SYSTEM
from app.core.tool_registry import COMPANION_TOOLS
from app.modules.companion.memory import (
    save_memory,
    get_memory,
    log_mood,
    get_user_profile_summary,
)


async def _execute_tool(
    tool_name: str,
    tool_input: dict,
    user_id: str,
    db: AsyncSession,
) -> str:
    """分发并执行 Claude 选择的工具，返回结果字符串"""
    if tool_name == "save_user_memory":
        result = await save_memory(
            db, user_id,
            tool_input["category"],
            tool_input["key"],
            tool_input["value"],
            tool_input.get("note"),
        )
    elif tool_name == "get_user_memory":
        result = await get_memory(db, user_id, tool_input["category"])
    elif tool_name == "log_mood":
        result = await log_mood(db, user_id, tool_input["mood"], tool_input.get("trigger"))
    else:
        result = {"error": f"未知工具: {tool_name}"}
    return json.dumps(result, ensure_ascii=False)


async def chat_stream(
    user_id: str,
    message: str,
    history: list[dict],  # [{"role": "user"/"assistant", "content": "..."}]
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    情感陪伴流式对话
    - Anthropic 模式：Claude 调用记忆/情绪工具，支持工具循环
    - 其他供应商：纯对话流式输出，无工具调用
    """
    today = datetime.now().strftime("%Y年%m月%d日")
    profile = await get_user_profile_summary(db, user_id)
    system_prompt = COMPANION_SYSTEM.format(date=today, user_profile=profile)
    messages: list[dict] = [*history, {"role": "user", "content": message}]

    active = get_active_provider()

    if active != "anthropic":
        # ── 非 Anthropic 供应商：直接流式输出，无工具 ──────────────────────
        async for chunk in provider_chat_stream(
            messages=messages,
            system=system_prompt,
            max_tokens=MAX_TOKENS_CHAT,
        ):
            if chunk.startswith("data: "):
                try:
                    payload = json.loads(chunk[6:])
                    t = payload.get("type")
                    if t == "delta":
                        # 统一为 text_delta 格式
                        yield f"data: {json.dumps({'type': 'text_delta', 'text': payload['text']})}\n\n"
                    elif t in ("done", "error"):
                        yield chunk  # 直接透传 done 和 error
                except Exception:
                    yield chunk
        return

    # ── Anthropic 模式：工具调用循环 + 流式输出 ────────────────────────────
    client = get_client()
    max_tool_iterations = 3
    for _ in range(max_tool_iterations):
        with client.messages.stream(
            model=MODEL_PRIMARY,
            max_tokens=MAX_TOKENS_CHAT,
            system=system_prompt,
            tools=COMPANION_TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            for event in stream:
                if (
                    event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    yield f"data: {json.dumps({'type': 'text_delta', 'text': event.delta.text})}\n\n"

            final_msg = stream.get_final_message()
            collected_content = final_msg.content

        tool_use_blocks = [b for b in collected_content if b.type == "tool_use"]
        if not tool_use_blocks:
            break

        tool_results = []
        for tu in tool_use_blocks:
            result_str = await _execute_tool(tu.name, tu.input, user_id, db)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result_str,
            })

        messages.append({"role": "assistant", "content": collected_content})  # type: ignore[arg-type]
        messages.append({"role": "user", "content": tool_results})

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def chat_non_stream(
    user_id: str,
    message: str,
    history: list[dict],
    db: AsyncSession,
) -> str:
    """非流式对话（用于后台任务，如生成每日问候语）"""
    client = get_client()
    today = datetime.now().strftime("%Y年%m月%d日")
    profile = await get_user_profile_summary(db, user_id)
    system_prompt = COMPANION_SYSTEM.format(date=today, user_profile=profile)

    messages: list[dict] = [*history, {"role": "user", "content": message}]
    response = client.messages.create(
        model=MODEL_PRIMARY,
        max_tokens=MAX_TOKENS_CHAT,
        system=system_prompt,
        messages=messages,  # type: ignore[arg-type]
    )
    return next((b.text for b in response.content if b.type == "text"), "")
