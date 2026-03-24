"""
健康医疗 API 路由
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.schema import get_db
from app.modules.health.advisor import health_consult_stream, analyze_medication
from app.modules.health.tools import trigger_sos, set_medication_reminder

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
