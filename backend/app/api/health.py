"""
健康医疗 API 路由
"""
import json, re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.schema import get_db
from app.modules.health.advisor import health_consult_stream, analyze_medication
from app.modules.health.tools import trigger_sos, set_medication_reminder
from app.core.ai_provider import chat_complete

router = APIRouter(prefix="/health", tags=["健康医疗"])


class ConsultRequest(BaseModel):
    user_id: str
    message: str
    history: list[dict] = []


class MedicationCheckRequest(BaseModel):
    user_id: str
    drugs: list[str]


class SOSRequest(BaseModel):
    user_id: str
    emergency_type: str = "other"
    message: str = ""


class ReminderRequest(BaseModel):
    user_id: str
    drug_name: str
    times: list[str]
    dosage: str
    notes: str | None = None


@router.post("/consult/stream")
async def health_consult(req: ConsultRequest, db: AsyncSession = Depends(get_db)):
    """
    AI 健康问诊（流式）
    使用 adaptive thinking 进行深度医疗推理
    """
    return StreamingResponse(
        health_consult_stream(req.user_id, req.message, req.history, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/medication/check")
async def check_medication(req: MedicationCheckRequest, db: AsyncSession = Depends(get_db)):
    """药物相互作用 AI 分析"""
    result = await analyze_medication(req.user_id, req.drugs, db)
    return result


@router.post("/sos")
async def emergency_sos(req: SOSRequest, db: AsyncSession = Depends(get_db)):
    """
    SOS 紧急求救
    PRD P0 功能：必须 100% 可靠，无容错
    """
    result = await trigger_sos(db, req.user_id, req.emergency_type, req.message)
    return result


@router.post("/reminder")
async def set_reminder(req: ReminderRequest, db: AsyncSession = Depends(get_db)):
    """设置用药提醒"""
    result = await set_medication_reminder(
        db, req.user_id, req.drug_name, req.times, req.dosage, req.notes
    )
    return result


class MemoryExtractRequest(BaseModel):
    user_message: str
    ai_response: str
    existing_memory: dict = {}


@router.post("/memory/extract")
async def memory_extract(req: MemoryExtractRequest):
    """
    从对话中提取健康档案信息
    自动识别慢性病、用药、过敏史、症状，合并到已有档案
    """
    existing = json.dumps(req.existing_memory, ensure_ascii=False) if req.existing_memory else "暂无"
    prompt = f"""从以下一次对话中提取用户的健康相关信息，补充到健康档案。

用户说：{req.user_message[:400]}
AI医生回复：{req.ai_response[:400]}

当前档案：{existing}

提取规则：
- 只提取用户明确说出或AI确认的信息，不猜测
- conditions：慢性病、已确诊疾病（如"高血压"、"糖尿病"）
- medications：正在服用的药物（如"氨氯地平5mg"）
- allergies：药物或食物过敏
- symptoms：本次提到的症状（如"膝盖疼3天"）
- notes：其他重要健康信息

只返回 JSON，如无新信息则返回 {{"no_update": true}}：
{{
  "conditions": ["..."],
  "medications": ["..."],
  "allergies": ["..."],
  "symptoms": ["..."],
  "notes": "..."
}}"""
    try:
        text = await chat_complete(messages=[{"role": "user", "content": prompt}], max_tokens=300)
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            data = json.loads(m.group())
            return data
        return {"no_update": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:100])
