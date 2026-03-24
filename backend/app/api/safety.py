"""
安全防护 API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.safety.fraud_detector import analyze_fraud, check_content_safety

router = APIRouter(prefix="/safety", tags=["安全防护"])


class FraudCheckRequest(BaseModel):
    content: str          # 可疑消息/通话内容描述


class ContentCheckRequest(BaseModel):
    content: str          # 待审查的 UGC 内容


@router.post("/fraud/check")
async def fraud_check(req: FraudCheckRequest):
    """
    AI 防诈骗检测
    两阶段：Haiku 快速分类 → 高风险升级 Opus 深度分析
    返回风险等级和具体建议
    """
    result = await analyze_fraud(req.content)
    return result.model_dump()


@router.post("/content/check")
async def content_safety_check(req: ContentCheckRequest):
    """
    UGC 内容安全审查
    Claude Haiku + 结构化输出，高吞吐量低延迟
    """
    result = await check_content_safety(req.content)
    return result.model_dump()
