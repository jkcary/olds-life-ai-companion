"""
情感陪伴核心模块
AI 原生设计：
  - Claude 主动决定何时调用记忆工具（save/get）
  - Claude 检测用户情绪并调用 log_mood 工具
  - 所有回复通过 SSE 流式输出，让老人感受实时陪伴
  - 使用 compaction 支持超长对话（数月的陪伴记录）
"""
import json
from datetime import datetime
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

import anthropic

from app.core.claude_client import get_client, MODEL_PRIMARY, MAX_TOKENS_CHAT
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
    使用 tool_runner 思路：Claude 可以在回复中途调用工具，完成后继续流式输出
    """
    client = get_client()
    today = datetime.now().strftime("%Y年%m月%d日")
    profile = await get_user_profile_summary(db, user_id)
    system_prompt = COMPANION_SYSTEM.format(date=today, user_profile=profile)

    # 构建消息历史（支持 compaction 的格式）
    messages: list[dict] = [*history, {"role": "user", "content": message}]

    # 工具调用循环 + 流式输出
    # 当 Claude 需要调用工具时，暂停流式 → 执行工具 → 继续流式
    max_tool_iterations = 3
    for _ in range(max_tool_iterations):
        with client.messages.stream(
            model=MODEL_PRIMARY,
            max_tokens=MAX_TOKENS_CHAT,
            system=system_prompt,
            tools=COMPANION_TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            tool_use_blocks = []
            collected_content = []

            for event in stream:
                # 流式输出文本 delta
                if (
                    event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    chunk = event.delta.text
                    yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"

            final_msg = stream.get_final_message()
            collected_content = final_msg.content

            # 收集工具调用
            for block in collected_content:
                if block.type == "tool_use":
                    tool_use_blocks.append(block)

        if not tool_use_blocks:
            # 无工具调用，对话结束
            break

        # 执行工具并将结果反馈给 Claude
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
