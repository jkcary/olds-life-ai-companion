"""社交交友 API 路由"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.social.matcher import (
    FriendMatchProfile, analyze_friend_match,
    recommend_circles, parse_friend_search_query,
)

router = APIRouter(prefix="/social", tags=["社交交友"])


class MatchRequest(BaseModel):
    user: FriendMatchProfile
    candidate: FriendMatchProfile


class CircleRequest(BaseModel):
    user_id: str
    hobbies: list[str]
    personality_desc: str = ""
    already_joined: list[str] = []


class FriendSearchRequest(BaseModel):
    query: str          # "我想找80年代在哈尔滨铁路局工作过的老同事"


@router.post("/match/analyze")
async def analyze_match(req: MatchRequest):
    """AI 好友匹配分析：生成共同话题和破冰建议"""
    result = await analyze_friend_match(req.user, req.candidate)
    return result.model_dump()


@router.post("/circles/recommend")
async def circle_recommend(req: CircleRequest):
    """AI 圈子推荐：根据兴趣和性格推荐最适合的3个圈子"""
    results = await recommend_circles(
        req.user_id, req.hobbies, req.personality_desc, req.already_joined
    )
    return [r.model_dump() for r in results]


@router.post("/friends/search/parse")
async def parse_search(req: FriendSearchRequest):
    """将自然语言找老朋友描述解析为结构化搜索条件"""
    result = await parse_friend_search_query(req.query)
    return result
