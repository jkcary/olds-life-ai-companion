"""
健康医疗 AI 顾问
AI 原生设计：
  - Claude 使用 adaptive thinking 对复杂症状进行深度推理
  - 通过工具调用健康档案、药物禁忌数据库
  - 自动识别急症信号，触发 SOS 工具
  - 食疗建议基于 24 节气和用户体质动态生成
"""
import json
from datetime import datetime
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

import anthropic

from app.core.claude_client import get_client, MODEL_PRIMARY, MAX_TOKENS_HEALTH
from app.core.ai_provider import get_active_provider, chat_stream as provider_chat_stream
from app.core.system_prompts import HEALTH_SYSTEM
from app.core.tool_registry import HEALTH_TOOLS
from app.modules.health.tools import (
    check_drug_interaction,
    trigger_sos,
    set_medication_reminder,
    get_health_records,
)


# 急症关键词（用于快速预检，真正的判断由 Claude 完成）
EMERGENCY_KEYWORDS = ["胸痛", "胸闷", "呼吸困难", "半身不遂", "口角歪斜", "昏迷", "大出血"]


async def _execute_health_tool(
    tool_name: str,
    tool_input: dict,
    user_id: str,
    db: AsyncSession,
) -> str:
    """执行健康模块工具"""
    if tool_name == "check_drug_interaction":
        result = await check_drug_interaction(tool_input["drugs"])
    elif tool_name == "trigger_sos":
        result = await trigger_sos(
            db,
            tool_input.get("user_id", user_id),
            tool_input["emergency_type"],
            tool_input.get("message", ""),
        )
    elif tool_name == "set_medication_reminder":
        result = await set_medication_reminder(
            db, user_id,
            tool_input["drug_name"],
            tool_input["times"],
            tool_input["dosage"],
            tool_input.get("notes"),
        )
    elif tool_name == "get_health_records":
        result = await get_health_records(db, user_id, tool_input["record_type"])
    else:
        result = {"error": f"未知工具: {tool_name}"}
    return json.dumps(result, ensure_ascii=False)


async def health_consult_stream(
    user_id: str,
    message: str,
    history: list[dict],
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    AI 健康问诊流式接口
    - Anthropic：adaptive thinking + 工具调用（药物查询、SOS）
    - 其他供应商：直接流式回答，无工具调用
    """
    today = datetime.now().strftime("%Y年%m月%d日")
    health_records = await get_health_records(db, user_id, "all")
    profile_text = json.dumps(health_records, ensure_ascii=False) if health_records else "无健康档案"
    system_prompt = HEALTH_SYSTEM.format(date=today, user_profile=profile_text)

    is_emergency_related = any(kw in message for kw in EMERGENCY_KEYWORDS)
    if is_emergency_related:
        yield f"data: {json.dumps({'type': 'urgent_flag', 'message': '检测到可能的急症描述，正在分析...'})}\n\n"

    messages: list[dict] = [*history, {"role": "user", "content": message}]
    active = get_active_provider()

    if active != "anthropic":
        # ── 非 Anthropic 供应商：纯流式对话 ──────────────────────────────
        async for chunk in provider_chat_stream(
            messages=messages,
            system=system_prompt,
            max_tokens=MAX_TOKENS_HEALTH,
        ):
            if chunk.startswith("data: "):
                try:
                    payload = json.loads(chunk[6:])
                    t = payload.get("type")
                    if t == "delta":
                        # 统一为 text_delta，与健康 Anthropic 路径一致
                        yield f"data: {json.dumps({'type': 'text_delta', 'text': payload['text']})}\n\n"
                    elif t in ("done", "error"):
                        yield chunk
                except Exception:
                    yield chunk
        return

    # ── Anthropic 模式：adaptive thinking + 工具调用循环 ─────────────────
    client = get_client()
    max_tool_iterations = 4
    for _ in range(max_tool_iterations):
        with client.messages.stream(
            model=MODEL_PRIMARY,
            max_tokens=MAX_TOKENS_HEALTH,
            thinking={"type": "adaptive"},
            system=system_prompt,
            tools=HEALTH_TOOLS,  # type: ignore[arg-type]
            messages=messages,   # type: ignore[arg-type]
        ) as stream:
            tool_use_blocks = []

            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield f"data: {json.dumps({'type': 'delta', 'text': event.delta.text})}\n\n"

            final_msg = stream.get_final_message()
            collected_content = final_msg.content

            for block in collected_content:
                if block.type == "tool_use":
                    tool_use_blocks.append(block)
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': block.name})}\n\n"

        if not tool_use_blocks:
            break

        tool_results = []
        for tu in tool_use_blocks:
            result_str = await _execute_health_tool(tu.name, tu.input, user_id, db)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result_str,
            })

        messages.append({"role": "assistant", "content": collected_content})  # type: ignore[arg-type]
        messages.append({"role": "user", "content": tool_results})

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def analyze_medication(user_id: str, drugs: list[str], db: AsyncSession) -> dict:
    """
    药物相互作用分析
    Claude 使用 adaptive thinking 综合分析多药配伍风险
    """
    client = get_client()
    drugs_str = "、".join(drugs)
    prompt = f"请分析以下药物同时服用的安全性：{drugs_str}"

    # 先调用工具获取数据库禁忌信息
    db_result = await check_drug_interaction(drugs)

    response = client.messages.create(
        model=MODEL_PRIMARY,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system="""你是药学专家，专门为老年患者提供用药安全建议。
分析药物配伍时，需考虑：相互作用机制、严重程度、替代方案、服药间隔建议。
回复语言通俗易懂，老人能看懂。""",
        messages=[
            {"role": "user", "content": f"{prompt}\n\n药物数据库查询结果：{json.dumps(db_result, ensure_ascii=False)}"}
        ],
    )
    analysis = next((b.text for b in response.content if b.type == "text"), "")
    return {
        "drugs": drugs,
        "database_result": db_result,
        "ai_analysis": analysis,
    }
