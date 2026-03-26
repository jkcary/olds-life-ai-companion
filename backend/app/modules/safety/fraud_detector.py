"""
AI 安全防护模块
AI 原生设计：
  - Anthropic 模式：两阶段（Haiku 初筛 + Opus 深度分析）+ 结构化输出
  - 其他供应商：单次调用，从文本中提取 JSON
"""
import json
import re
from pydantic import BaseModel

import anthropic

from app.core.claude_client import get_client, MODEL_PRIMARY, MODEL_FAST, MAX_TOKENS_SAFETY
from app.core.ai_provider import get_active_provider, chat_complete
from app.core.system_prompts import SAFETY_SYSTEM, CONTENT_SAFETY_SYSTEM


class FraudAnalysisResult(BaseModel):
    risk_level: str           # high / medium / low / none
    fraud_type: str | None    # 诈骗类型
    evidence: list[str]       # 风险信号列表
    recommendation: str       # 给用户的建议
    action: str               # warn / alert / safe
    report_to_platform: bool  # 是否上报平台


class ContentSafetyResult(BaseModel):
    safe: bool
    risk_level: str           # high / medium / low / none
    risk_type: str | None
    action: str               # approve / review / reject
    reason: str


def _extract_json(text: str) -> dict:
    """从文本中提取第一个 JSON 对象"""
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found in response")


async def analyze_fraud(content: str) -> FraudAnalysisResult:
    """
    防诈骗分析
    - Anthropic：两阶段（Haiku 初筛 + Opus 深度分析）+ 结构化输出
    - 其他供应商：单次调用，解析 JSON
    """
    active = get_active_provider()
    if active != "anthropic":
        return await _analyze_fraud_generic(content)

    client = get_client()
    today_str = __import__("datetime").datetime.now().strftime("%Y年%m月%d日")
    system = SAFETY_SYSTEM.format(date=today_str)

    # 阶段1：Haiku 快速分类（低延迟）
    quick_response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=MAX_TOKENS_SAFETY,
        system=system + "\n\n请快速判断风险等级，只输出：high/medium/low/none，不要其他内容。",
        messages=[{"role": "user", "content": f"分析以下内容的诈骗风险：\n{content}"}],
    )
    quick_level = next((b.text.strip().lower() for b in quick_response.content if b.type == "text"), "unknown")

    # 阶段2：若高风险，Opus 深度分析
    analysis_model = MODEL_PRIMARY if quick_level in ("high", "medium") else MODEL_FAST
    max_tokens_deep = 1024 if quick_level in ("high", "medium") else MAX_TOKENS_SAFETY

    response = client.messages.create(
        model=analysis_model,
        max_tokens=max_tokens_deep,
        thinking={"type": "adaptive"} if quick_level == "high" else anthropic.NOT_GIVEN,  # type: ignore[arg-type]
        system=system,
        messages=[
            {
                "role": "user",
                "content": f"""分析以下内容是否为诈骗，请以 JSON 格式返回结果：
{content}

JSON 格式：
{{
  "risk_level": "high/medium/low/none",
  "fraud_type": "诈骗类型或null",
  "evidence": ["风险信号1", "风险信号2"],
  "recommendation": "给老年用户的具体建议",
  "action": "warn/alert/safe",
  "report_to_platform": true/false
}}""",
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "risk_level": {"type": "string", "enum": ["high", "medium", "low", "none"]},
                        "fraud_type": {"type": ["string", "null"]},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                        "recommendation": {"type": "string"},
                        "action": {"type": "string", "enum": ["warn", "alert", "safe"]},
                        "report_to_platform": {"type": "boolean"},
                    },
                    "required": ["risk_level", "fraud_type", "evidence", "recommendation", "action", "report_to_platform"],
                    "additionalProperties": False,
                },
            }
        },
    )

    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        return FraudAnalysisResult(
            risk_level="unknown",
            fraud_type=None,
            evidence=[],
            recommendation="无法分析，请谨慎对待",
            action="warn",
            report_to_platform=False,
        )

    data = json.loads(text_block.text)
    return FraudAnalysisResult(**data)


async def _analyze_fraud_generic(content: str) -> FraudAnalysisResult:
    """非 Anthropic 供应商的防诈骗分析（单次调用，解析 JSON）"""
    today_str = __import__("datetime").datetime.now().strftime("%Y年%m月%d日")
    prompt = f"""你是一位温柔耐心、专门保护老年人的防诈骗顾问，今天是{today_str}。
请分析以下内容是否存在诈骗风险。

重要要求：
- evidence（分析理由）：用温和、通俗的语言解释为什么有风险，帮助老人理解，不要恐吓
- recommendation（应对建议）：语气像对待自己家里长辈一样亲切，给出具体可操作的保护建议，让老人感到被关心而不是被批评

内容：{content}

严格按 JSON 格式返回，不要加任何额外文字：
{{
  "risk_level": "high/medium/low/none",
  "fraud_type": "诈骗类型描述或null",
  "evidence": ["风险信号1（通俗解释）", "风险信号2"],
  "recommendation": "亲切温和的建议，帮助老人保护自己",
  "action": "warn/alert/safe",
  "report_to_platform": true或false
}}"""
    try:
        text = await chat_complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        data = _extract_json(text)
        # 确保必要字段存在
        data.setdefault("evidence", [])
        data.setdefault("report_to_platform", False)
        return FraudAnalysisResult(**data)
    except Exception as e:
        return FraudAnalysisResult(
            risk_level="unknown",
            fraud_type=None,
            evidence=[],
            recommendation=f"分析失败（{str(e)[:50]}），请谨慎对待该信息",
            action="warn",
            report_to_platform=False,
        )


async def check_content_safety(content: str) -> ContentSafetyResult:
    """
    UGC 内容安全审查
    使用 Claude Haiku + 结构化输出实现高吞吐量审核
    """
    client = get_client()

    response = client.messages.create(
        model=MODEL_FAST,   # Haiku：快速审核，控制成本
        max_tokens=256,
        system=CONTENT_SAFETY_SYSTEM,
        messages=[{"role": "user", "content": f"审查以下内容：\n{content}"}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "safe": {"type": "boolean"},
                        "risk_level": {"type": "string", "enum": ["high", "medium", "low", "none"]},
                        "risk_type": {"type": ["string", "null"]},
                        "action": {"type": "string", "enum": ["approve", "review", "reject"]},
                        "reason": {"type": "string"},
                    },
                    "required": ["safe", "risk_level", "risk_type", "action", "reason"],
                    "additionalProperties": False,
                },
            }
        },
    )

    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        return ContentSafetyResult(
            safe=False, risk_level="unknown", risk_type=None,
            action="review", reason="审核失败，人工复查"
        )

    data = json.loads(text_block.text)
    return ContentSafetyResult(**data)
