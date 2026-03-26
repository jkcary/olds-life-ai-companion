"""
出行出游 AI 导航顾问
AI 原生设计：
  - Claude 将老人的口语化目的地描述理解为可导航的地点
  - 生成适老化步骤（比普通导航慢30%、优先无障碍路线）
  - 景区 AI 讲解：Claude 扮演导游，根据景点生成适合老年人的讲解词
  - 旅游行程规划：每天不超过6小时，午间必有休息
"""
import json
from collections.abc import AsyncGenerator
from pydantic import BaseModel

from app.core.claude_client import get_client, MODEL_PRIMARY, MODEL_FAST


NAVIGATION_SYSTEM = """你是"银龄AI导游"，专门为中国老年人提供出行导航和旅游服务。

导航原则：
1. 语言简单清晰，每条指示不超过20字
2. 提前300米提醒转弯（普通导航是200米）
3. 优先推荐无障碍路线：有电梯、坡道、避开楼梯
4. 步行段超过500米时主动提示休息点
5. 公交换乘说清楚：几路车、哪个门上、坐几站
6. 全程用"您"称呼老人，语气像子女陪伴
"""


class NavigationStep(BaseModel):
    step_no: int
    instruction: str           # 导航指令
    distance_m: int            # 本步骤距离（米）
    landmark: str | None       # 参考地标
    accessibility_note: str | None  # 无障碍提示


class NavigationPlan(BaseModel):
    destination: str
    total_distance_m: int
    estimated_minutes: int
    route_type: str            # "步行" / "公交+步行" / "出租车建议"
    steps: list[NavigationStep]
    rest_points: list[str]     # 建议休息的地点


class TravelItinerary(BaseModel):
    destination: str
    days: int
    daily_plans: list[dict]    # 每天的行程
    accessibility_summary: str
    health_tips: list[str]


async def plan_navigation(
    origin_desc: str,          # "我在中山公园东门"
    destination_desc: str,     # "最近的三甲医院"
    user_mobility: str = "normal",  # normal / limited / wheelchair
) -> NavigationPlan:
    """
    AI 语音找路
    Claude 理解口语化描述，生成适老化导航步骤
    """
    client = get_client()

    mobility_note = {
        "normal": "用户行动正常",
        "limited": "用户行动不便，需减少步行，优先电梯和坡道",
        "wheelchair": "用户使用轮椅，必须全程无障碍路线",
    }.get(user_mobility, "用户行动正常")

    prompt = f"""请为老年用户规划出行路线。

出发地描述：{origin_desc}
目的地描述：{destination_desc}
行动能力：{mobility_note}

请生成适老化导航方案，每步骤指令简洁明了，以 JSON 返回：
{{
  "destination": "解析后的目的地名称",
  "total_distance_m": 总距离整数,
  "estimated_minutes": 预计分钟整数,
  "route_type": "步行/公交+步行/出租车建议",
  "steps": [
    {{
      "step_no": 步骤编号,
      "instruction": "导航指令，不超过25字",
      "distance_m": 本段距离,
      "landmark": "参考地标或null",
      "accessibility_note": "无障碍提示或null"
    }}
  ],
  "rest_points": ["建议休息地点1", "建议休息地点2"]
}}"""

    response = client.messages.create(
        model=MODEL_PRIMARY,
        max_tokens=1024,
        system=NAVIGATION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "destination": {"type": "string"},
                        "total_distance_m": {"type": "integer"},
                        "estimated_minutes": {"type": "integer"},
                        "route_type": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step_no": {"type": "integer"},
                                    "instruction": {"type": "string"},
                                    "distance_m": {"type": "integer"},
                                    "landmark": {"type": ["string", "null"]},
                                    "accessibility_note": {"type": ["string", "null"]},
                                },
                                "required": ["step_no", "instruction", "distance_m",
                                             "landmark", "accessibility_note"],
                                "additionalProperties": False,
                            },
                        },
                        "rest_points": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["destination", "total_distance_m", "estimated_minutes",
                                 "route_type", "steps", "rest_points"],
                    "additionalProperties": False,
                },
            }
        },
    )
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    data["steps"] = [NavigationStep(**s) for s in data["steps"]]
    return NavigationPlan(**data)


async def explain_attraction_stream(
    attraction_name: str,
    user_interests: list[str],
) -> AsyncGenerator[str, None]:
    """
    景区 AI 讲解（流式）
    Claude 扮演博学的导游，以老年人喜欢的方式介绍景点
    融入历史故事、文化典故、养生知识等老人感兴趣的内容
    """
    client = get_client()

    interests_str = "、".join(user_interests) if user_interests else "历史文化"
    system = f"""你是一位博学温和的老年旅游专业导游。
讲解风格：
- 结合历史故事和民间传说，让老人听得入迷
- 联系用户兴趣（{interests_str}）选择切入角度
- 适当穿插养生知识（如景点的气候、适合的活动）
- 语速暗示：讲解词节奏舒缓，便于老人理解
- 每段讲解300字以内，用自然段落分开"""

    with client.messages.stream(
        model=MODEL_PRIMARY,
        max_tokens=800,
        system=system,
        messages=[{
            "role": "user",
            "content": f"请为我讲解【{attraction_name}】，语气亲切，像导游现场讲解一样。"
        }],
    ) as stream:
        for event in stream:
            if (event.type == "content_block_delta"
                    and event.delta.type == "text_delta"):
                yield f"data: {json.dumps({'type': 'delta', 'text': event.delta.text})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def plan_senior_travel(
    destination: str,
    days: int,
    health_conditions: list[str],   # ["高血压", "膝关节不好"]
    travel_style: str = "comfortable",  # comfortable / active
) -> TravelItinerary:
    """
    老年旅游行程规划
    每天游览不超过6小时，午间必休息，考虑健康状况定制
    """
    client = get_client()

    health_str = "、".join(health_conditions) if health_conditions else "无特殊健康问题"
    style_desc = "舒适悠闲（减少步行）" if travel_style == "comfortable" else "适度活跃"

    prompt = f"""为老年人规划{destination} {days}天旅游行程。

健康状况：{health_str}
旅行风格：{style_desc}

行程规划原则：
1. 每天游览时间不超过6小时（上午3小时，下午3小时）
2. 午饭后必须安排1-2小时午休
3. 景点选择考虑无障碍设施，标注轮椅可达性
4. 每天包含：早餐推荐、上午景点、午休、下午景点、晚餐推荐
5. 根据健康状况调整活动强度

以 JSON 返回：
{{
  "destination": "{destination}",
  "days": {days},
  "daily_plans": [
    {{
      "day": 1,
      "morning": "上午安排",
      "lunch": "午餐推荐",
      "rest": "午休安排",
      "afternoon": "下午安排",
      "dinner": "晚餐推荐",
      "health_tips": "当天健康提示"
    }}
  ],
  "accessibility_summary": "无障碍设施总体说明",
  "health_tips": ["整体健康建议1", "整体健康建议2", "整体健康建议3"]
}}"""

    response = client.messages.create(
        model=MODEL_PRIMARY,
        max_tokens=2048,
        thinking={"type": "adaptive"},   # 复杂行程规划用自适应思考
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "destination": {"type": "string"},
                        "days": {"type": "integer"},
                        "daily_plans": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "day": {"type": "integer"},
                                    "morning": {"type": "string"},
                                    "lunch": {"type": "string"},
                                    "rest": {"type": "string"},
                                    "afternoon": {"type": "string"},
                                    "dinner": {"type": "string"},
                                    "health_tips": {"type": "string"},
                                },
                                "required": ["day", "morning", "lunch", "rest",
                                             "afternoon", "dinner", "health_tips"],
                                "additionalProperties": False,
                            },
                        },
                        "accessibility_summary": {"type": "string"},
                        "health_tips": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["destination", "days", "daily_plans",
                                 "accessibility_summary", "health_tips"],
                    "additionalProperties": False,
                },
            }
        },
    )
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    return TravelItinerary(**data)
