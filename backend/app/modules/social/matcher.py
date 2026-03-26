"""
社交交友模块
AI 原生设计：
  - Claude 分析两个用户档案，生成人性化的共同话题和破冰建议
  - 兴趣圈子推荐：Claude 根据用户行为和偏好动态推荐，非规则过滤
  - 找老朋友：Claude 理解模糊描述（"80年代在武汉纺织厂工作的"），生成
    结构化搜索条件
"""
import json
from pydantic import BaseModel

from app.core.claude_client import get_client, MODEL_PRIMARY, MODEL_FAST


class FriendMatchProfile(BaseModel):
    user_id: str
    nickname: str
    age: int
    hometown: str | None = None
    work_history: str | None = None        # "1978-1995年在上海第一钢铁厂工作"
    school_history: str | None = None
    hobbies: list[str] = []
    era_keywords: list[str] = []           # ["知青", "改革开放", "下岗再就业"]


class MatchResult(BaseModel):
    score: int                              # 0-100 匹配度
    common_topics: list[str]               # Claude 生成的共同话题
    icebreaker: str                         # Claude 生成的开场白建议
    reason: str                             # 匹配原因说明


class CircleRecommendation(BaseModel):
    circle_id: str
    name: str
    description: str
    why_recommended: str                    # Claude 解释为什么推荐这个圈子
    estimated_engagement: str              # "高度活跃" / "适合安静浏览"


# 预设兴趣圈子（真实场景存数据库）
PRESET_CIRCLES = [
    {"id": "taichi", "name": "太极拳爱好者", "tags": ["运动", "健身", "传统武术", "养生"]},
    {"id": "square_dance", "name": "广场舞大家庭", "tags": ["舞蹈", "音乐", "社交", "健身"]},
    {"id": "photography", "name": "夕阳摄影师", "tags": ["摄影", "旅游", "艺术", "自然"]},
    {"id": "fishing", "name": "垂钓俱乐部", "tags": ["钓鱼", "户外", "安静", "自然"]},
    {"id": "cooking", "name": "银龄厨艺坊", "tags": ["烹饪", "美食", "传统食谱", "分享"]},
    {"id": "calligraphy", "name": "书法墨香阁", "tags": ["书法", "国画", "传统文化", "艺术"]},
    {"id": "singing", "name": "老歌新唱", "tags": ["唱歌", "音乐", "怀旧", "合唱"]},
    {"id": "gardening", "name": "阳台花园", "tags": ["园艺", "花卉", "种植", "自然"]},
    {"id": "mahjong", "name": "麻将茶友会", "tags": ["麻将", "棋牌", "益智", "社交"]},
    {"id": "health_talk", "name": "健康养生汇", "tags": ["健康", "养生", "慢病管理", "中医"]},
    {"id": "travel", "name": "银发旅行团", "tags": ["旅游", "摄影", "历史", "文化"]},
    {"id": "knitting", "name": "编织温暖", "tags": ["针织", "手工", "创作", "送礼"]},
]


async def analyze_friend_match(
    user_profile: FriendMatchProfile,
    candidate_profile: FriendMatchProfile,
) -> MatchResult:
    """
    AI 好友匹配分析
    Claude 扮演资深社交顾问，分析两人的共同经历和话题契合度
    """
    client = get_client()

    prompt = f"""你是一位资深的老年社交顾问，请分析以下两位老年人的匹配度。

【用户A】
昵称：{user_profile.nickname}，年龄：{user_profile.age}岁
家乡：{user_profile.hometown or '未填写'}
工作经历：{user_profile.work_history or '未填写'}
学习经历：{user_profile.school_history or '未填写'}
兴趣爱好：{', '.join(user_profile.hobbies) or '未填写'}
时代关键词：{', '.join(user_profile.era_keywords) or '未填写'}

【用户B】
昵称：{candidate_profile.nickname}，年龄：{candidate_profile.age}岁
家乡：{candidate_profile.hometown or '未填写'}
工作经历：{candidate_profile.work_history or '未填写'}
学习经历：{candidate_profile.school_history or '未填写'}
兴趣爱好：{', '.join(candidate_profile.hobbies) or '未填写'}
时代关键词：{', '.join(candidate_profile.era_keywords) or '未填写'}

请以 JSON 格式返回：
{{
  "score": 匹配度0-100的整数,
  "common_topics": ["共同话题1", "共同话题2", "共同话题3"],
  "icebreaker": "一句自然的开场白建议，语气像老朋友，不超过50字",
  "reason": "匹配原因，一两句话说清楚"
}}"""

    response = client.messages.create(
        model=MODEL_PRIMARY,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "integer"},
                        "common_topics": {"type": "array", "items": {"type": "string"}},
                        "icebreaker": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["score", "common_topics", "icebreaker", "reason"],
                    "additionalProperties": False,
                },
            }
        },
    )
    text = next(b.text for b in response.content if b.type == "text")
    return MatchResult(**json.loads(text))


async def recommend_circles(
    user_id: str,
    hobbies: list[str],
    personality_desc: str,
    already_joined: list[str],
) -> list[CircleRecommendation]:
    """
    AI 圈子推荐
    Claude 理解用户性格和兴趣，从候选列表中挑选最合适的 3 个圈子
    并用老人喜欢的语气解释推荐原因
    """
    client = get_client()

    available = [c for c in PRESET_CIRCLES if c["id"] not in already_joined]
    circles_desc = "\n".join(
        f"- {c['id']}: {c['name']}（标签：{', '.join(c['tags'])}）"
        for c in available
    )

    prompt = f"""你是一位了解老年人心理的社群顾问。请根据用户情况，从候选圈子中推荐最适合的3个。

【用户兴趣爱好】{', '.join(hobbies) or '未填写'}
【用户性格描述】{personality_desc or '未填写'}

【可加入的圈子】
{circles_desc}

要求：
1. 只推荐3个最合适的
2. 推荐原因要温暖、具体，像朋友介绍一样
3. 评估参与积极性（高度活跃/适合安静浏览/可尝试新体验）

以 JSON 数组返回：
[
  {{
    "circle_id": "圈子ID",
    "name": "圈子名称",
    "description": "一句话介绍",
    "why_recommended": "推荐原因，30字以内，亲切自然",
    "estimated_engagement": "高度活跃/适合安静浏览/可尝试新体验"
  }}
]"""

    response = client.messages.create(
        model=MODEL_FAST,      # Haiku 足够处理推荐逻辑
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "circle_id": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "why_recommended": {"type": "string"},
                            "estimated_engagement": {"type": "string"},
                        },
                        "required": ["circle_id", "name", "description", "why_recommended", "estimated_engagement"],
                        "additionalProperties": False,
                    },
                },
            }
        },
    )
    text = next(b.text for b in response.content if b.type == "text")
    return [CircleRecommendation(**item) for item in json.loads(text)]


async def parse_friend_search_query(natural_query: str) -> dict:
    """
    将老人的自然语言搜索解析为结构化条件
    例："我想找80年代在哈尔滨铁路局工作过的老同事"
    → {"city": "哈尔滨", "work_unit": "铁路局", "era": "1980s"}
    """
    client = get_client()

    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=256,
        system="你是搜索解析助手，将老年人的自然语言搜索需求解析为结构化字段。",
        messages=[{
            "role": "user",
            "content": f"""解析以下搜索需求，提取关键信息：
"{natural_query}"

以 JSON 返回（字段值不确定时填 null）：
{{
  "city": "城市",
  "province": "省份",
  "work_unit": "工作单位关键词",
  "school": "学校名称",
  "era_start": 年份整数或null,
  "era_end": 年份整数或null,
  "occupation": "职业",
  "keywords": ["其他关键词"]
}}"""
        }],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": ["string", "null"]},
                        "province": {"type": ["string", "null"]},
                        "work_unit": {"type": ["string", "null"]},
                        "school": {"type": ["string", "null"]},
                        "era_start": {"type": ["integer", "null"]},
                        "era_end": {"type": ["integer", "null"]},
                        "occupation": {"type": ["string", "null"]},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["city", "province", "work_unit", "school",
                                 "era_start", "era_end", "occupation", "keywords"],
                    "additionalProperties": False,
                },
            }
        },
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
