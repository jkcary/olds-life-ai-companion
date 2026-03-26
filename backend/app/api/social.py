"""社交交友 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.social.matcher import (
    FriendMatchProfile, analyze_friend_match,
    recommend_circles, parse_friend_search_query,
)

router = APIRouter(prefix="/social", tags=["社交交友"])


class MatchRequest(BaseModel):
    user: FriendMatchProfile
    candidate: FriendMatchProfile
    purpose: str = "交友"


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
    from fastapi import HTTPException
    try:
        result = await analyze_friend_match(req.user, req.candidate, req.purpose)
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败：{str(e)[:100]}")


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


class ExtractProfileRequest(BaseModel):
    type: str       # "image" | "url" | "file"
    content: str    # base64 data URI, URL string, or plain text


@router.post("/extract-profile")
async def extract_profile(req: ExtractProfileRequest):
    """多模态个人信息提取：从图片/网页/文件中提取用户档案文字"""
    from app.core.claude_client import get_client, MODEL_PRIMARY
    from app.core.ai_provider import get_active_provider, chat_complete

    fmt_prompt = (
        "请根据内容提取个人信息，输出简洁描述（一行即可），格式示例：\n"
        "王大爷 72岁 爱钓鱼太极拳 哈尔滨人\n"
        "若信息不完整请合理推断。只返回描述文字，不要解释。"
    )

    active = get_active_provider()

    if req.type == "image":
        b64 = req.content
        media_type = "image/jpeg"
        if b64.startswith("data:"):
            media_type = b64.split(";")[0].split(":")[1]
            b64 = b64.split(",", 1)[1]
        if active != "anthropic":
            raise HTTPException(status_code=400, detail="图片识别需要 Anthropic API，请切换供应商")
        client = get_client()
        response = client.messages.create(
            model=MODEL_PRIMARY, max_tokens=200,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": fmt_prompt},
            ]}],
        )
        result = response.content[0].text.strip()

    elif req.type == "url":
        import httpx, re
        url = req.content.strip()
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as hc:
                resp = await hc.get(url, headers={"User-Agent": "Mozilla/5.0"})
                raw = resp.text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"无法访问网页：{e}")
        clean = re.sub(r'<[^>]+>', ' ', raw)
        clean = re.sub(r'\s+', ' ', clean).strip()[:2000]
        try:
            result = await chat_complete(
                messages=[{"role": "user", "content": f"网页内容：\n{clean}\n\n{fmt_prompt}"}],
                max_tokens=200,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        result = result.strip()

    elif req.type == "file":
        content = req.content[:3000]
        try:
            result = await chat_complete(
                messages=[{"role": "user", "content": f"文件内容：\n{content}\n\n{fmt_prompt}"}],
                max_tokens=200,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        result = result.strip()

    else:
        raise HTTPException(status_code=400, detail="不支持的类型，支持 image/url/file")

    return {"profile": result}
