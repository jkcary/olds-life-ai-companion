"""出行出游 API 路由"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.modules.navigation.advisor import (
    plan_navigation, explain_attraction_stream, plan_senior_travel,
    resolve_destination,
)

router = APIRouter(prefix="/navigation", tags=["出行出游"])


class NavigationRequest(BaseModel):
    origin_desc: str            # "我在中山公园东门"
    destination_desc: str       # "最近的三甲医院"
    user_mobility: str = "normal"   # normal / limited / wheelchair


class AttractionRequest(BaseModel):
    attraction_name: str
    user_interests: list[str] = []


class TravelRequest(BaseModel):
    destination: str
    days: int
    health_conditions: list[str] = []
    travel_style: str = "comfortable"


class DestinationResolveRequest(BaseModel):
    query: str
    origin: str | None = None


@router.post("/destination/resolve")
async def destination_resolve(req: DestinationResolveRequest):
    """AI 目的地验证：模糊描述 → 明确地点候选列表"""
    try:
        result = await resolve_destination(req.query, req.origin)
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/route/plan")
async def route_plan(req: NavigationRequest):
    """AI 语音找路：口语化描述 → 适老化导航步骤"""
    try:
        result = await plan_navigation(
            req.origin_desc, req.destination_desc, req.user_mobility
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/attraction/explain/stream")
async def attraction_explain(req: AttractionRequest):
    """景区 AI 讲解（流式）：博学导游风格"""
    return StreamingResponse(
        explain_attraction_stream(req.attraction_name, req.user_interests),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/travel/plan")
async def travel_plan(req: TravelRequest):
    """老年旅游行程规划：每天≤6小时，午间必休息"""
    result = await plan_senior_travel(
        req.destination, req.days, req.health_conditions, req.travel_style
    )
    return result.model_dump()
