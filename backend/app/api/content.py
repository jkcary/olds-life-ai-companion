"""生活分享内容创作 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.content.creator import (
    generate_vlog_metadata, generate_daily_greeting,
    process_voice_diary,
)

router = APIRouter(prefix="/content", tags=["生活分享"])


class VlogRequest(BaseModel):
    content_tags: list[str]
    raw_description: str
    duration_seconds: int = 60


class GreetingRequest(BaseModel):
    user_id: str = ""
    user_nickname: str
    user_profile_summary: str = ""
    session: str = "morning"
    weather_desc: str | None = None
    city: str | None = None


class DiaryRequest(BaseModel):
    voice_transcript: str
    user_nickname: str
    record_date: str | None = None


def _friendly_error(e: Exception) -> str:
    msg = str(e)
    if "api_key" in msg.lower() or "authentication" in msg.lower() or "401" in msg or "api key" in msg.lower():
        return "API Key 未配置或无效，请在顶部重新配置 AI 服务"
    return msg[:200]


@router.post("/vlog/generate")
async def vlog_generate(req: VlogRequest):
    """Vlog AI 文案生成：标题、简介、旁白、话题标签"""
    try:
        result = await generate_vlog_metadata(
            req.content_tags, req.raw_description, req.duration_seconds
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.post("/greeting/daily")
async def daily_greeting(req: GreetingRequest):
    """每日个性化问候生成（节气 + 天气 + 用户记忆）"""
    try:
        result = await generate_daily_greeting(
            req.user_nickname, req.user_profile_summary, req.session, req.weather_desc, req.city
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.post("/diary/process")
async def diary_process(req: DiaryRequest):
    """语音日记 AI 整理：口述 → 结构化日记"""
    try:
        result = await process_voice_diary(
            req.voice_transcript, req.user_nickname, req.record_date
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))
