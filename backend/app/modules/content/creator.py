"""
生活分享内容创作模块
AI 原生设计：
  - Vlog：Claude 根据标签生成标题、描述、字幕文案，降低老人创作门槛
  - 每日问候：Claude 结合节气/天气/用户记忆生成个性化问候语
  - 日记总结：Claude 将用户语音转文字后，自动生成结构化日记条目
"""
import json
import re
from datetime import date, datetime, UTC
from pydantic import BaseModel

from app.core.claude_client import get_client, MODEL_PRIMARY, MODEL_FAST
from app.core.ai_provider import get_active_provider, chat_complete


def _extract_json(text: str) -> dict:
    """从文本中提取 JSON 对象（非 Anthropic 提供商回退）"""
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        return json.loads(m.group())
    raise ValueError(f"无法从回复中解析 JSON: {text[:200]}")


# 24 节气（用于个性化问候）
SOLAR_TERMS = {
    (1, 5): "小寒", (1, 20): "大寒",
    (2, 4): "立春", (2, 19): "雨水",
    (3, 6): "惊蛰", (3, 21): "春分",
    (4, 5): "清明", (4, 20): "谷雨",
    (5, 6): "立夏", (5, 21): "小满",
    (6, 6): "芒种", (6, 21): "夏至",
    (7, 7): "小暑", (7, 23): "大暑",
    (8, 7): "立秋", (8, 23): "处暑",
    (9, 8): "白露", (9, 23): "秋分",
    (10, 8): "寒露", (10, 23): "霜降",
    (11, 7): "立冬", (11, 22): "小雪",
    (12, 7): "大雪", (12, 22): "冬至",
}


def get_current_solar_term(today: date | None = None) -> str | None:
    today = today or date.today()
    for (m, d_day), name in SOLAR_TERMS.items():
        term_date = date(today.year, m, d_day)
        if abs((today - term_date).days) <= 3:
            return name
    return None


class VlogMetadata(BaseModel):
    title: str                  # 视频标题
    description: str            # 视频简介（适合发圈子）
    tags: list[str]             # 话题标签
    caption_script: str         # 字幕/旁白文案
    background_music_mood: str  # 推荐背景音乐风格


class DailyGreeting(BaseModel):
    greeting_text: str          # 主要问候语
    health_tip: str             # 今日养生建议
    solar_term_note: str | None # 节气相关内容
    activity_suggestion: str    # 今日活动建议
    seasonal_recipe: str        # 时令养生食谱
    outfit_color: str           # 穿衣颜色搭配
    activity_direction: str     # 健康活动方位
    reading_guide: str          # 读书指导
    buddhist_guide: str         # 佛经诵读指导
    taoist_guide: str           # 道教经典指导
    christian_guide: str        # 基督教灵修指导
    seasonal_produce: str       # 时令蔬菜水果
    travel_spots: str           # 时令旅游景点


class DiaryEntry(BaseModel):
    title: str
    summary: str                # AI 生成的日记摘要
    mood_analysis: str          # 情绪分析
    key_moments: list[str]      # 关键时刻列表
    formatted_entry: str        # 格式化日记正文


async def generate_vlog_metadata(
    content_tags: list[str],    # ["做饭", "红烧肉", "厨房", "家常菜"]
    raw_description: str,       # 用户口述的视频内容
    duration_seconds: int = 60,
) -> VlogMetadata:
    """
    Vlog 内容 AI 生成
    Claude 把老人的口述变成专业的视频文案，降低发布门槛
    """
    tags_str = "、".join(content_tags)
    duration_str = f"{duration_seconds // 60}分{duration_seconds % 60}秒" if duration_seconds >= 60 else f"{duration_seconds}秒"

    prompt = f"""你是一位专门帮老年人制作生活Vlog的助理。请根据以下信息生成视频相关文案。

视频内容标签：{tags_str}
用户描述：{raw_description}
视频时长：{duration_str}

要求：
1. 标题要温暖接地气，吸引同龄人，不超过20字
2. 简介要像老朋友分享，自然亲切，不超过100字
3. 话题标签3-5个，适合老年社区
4. 字幕/旁白文案：帮用户把口述整理成流畅的视频旁白
5. 背景音乐风格：根据内容推荐（如"轻松民乐"/"温馨流行老歌"/"舒缓纯音乐"）

只返回 JSON，不要有任何其他文字：
{{
  "title": "视频标题",
  "description": "视频简介",
  "tags": ["标签1", "标签2", "标签3"],
  "caption_script": "字幕旁白文案",
  "background_music_mood": "背景音乐风格建议"
}}"""

    if get_active_provider() != "anthropic":
        text = await chat_complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        return VlogMetadata(**_extract_json(text))

    try:
        client = get_client()
        response = client.messages.create(
            model=MODEL_FAST,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "caption_script": {"type": "string"},
                            "background_music_mood": {"type": "string"},
                        },
                        "required": ["title", "description", "tags",
                                     "caption_script", "background_music_mood"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        text = next(b.text for b in response.content if b.type == "text")
        return VlogMetadata(**json.loads(text))
    except Exception as e:
        err = str(e)
        if "api_key" in err.lower() or "authentication" in err.lower() or "401" in err:
            raise ValueError("Anthropic API Key 未配置，请在顶部配置 API Key")
        raise


async def generate_daily_greeting(
    user_nickname: str,
    user_profile_summary: str,
    session: str = "morning",
    weather_desc: str | None = None,
    city: str | None = None,
) -> DailyGreeting:
    """
    每日个性化问候生成（扩展版）
    包含养生食谱、穿衣搭配、活动方位、文化修养、时令蔬果、旅游景点
    """
    today = datetime.now(UTC).strftime("%Y年%m月%d日")
    solar_term = get_current_solar_term()
    solar_str = f"当前节气：{solar_term}，" if solar_term else ""
    weather_str = f"天气：{weather_desc}，" if weather_desc else ""
    city_str = f"所在城市：{city}，" if city else ""
    session_str = "早安" if session == "morning" else "晚安"

    prompt = f"""你是一位博学温暖的老年生活顾问，为用户生成{session_str}的全面每日生活指南。

用户昵称：{user_nickname}
用户信息：{user_profile_summary or '普通老年用户'}
{city_str}{weather_str}{solar_str}
今天日期：{today}

请生成完整的每日指南，所有内容贴合时令节气、天气、文化传统。

只返回 JSON，不要有任何其他文字：
{{
  "greeting_text": "温暖问候语（60字以内，像子女发的消息，亲切自然）",
  "health_tip": "今日养生核心建议（30字以内，结合节气）",
  "solar_term_note": "节气养生要点（有节气时填写，否则为null）",
  "activity_suggestion": "今日活动建议（20字以内，具体简单）",
  "seasonal_recipe": "时令养生食谱（具体菜名+主要做法，80字以内，结合节气和天气）",
  "outfit_color": "今日穿衣颜色搭配（结合五行节气天气，推荐颜色+款式理由，50字以内）",
  "activity_direction": "今日健康活动最佳方位（结合节气五行方位，告知向哪个方向散步锻炼，30字以内）",
  "reading_guide": "今日读书指导（推荐1-2本具体书目或篇章+适合阅读时段，40字以内）",
  "buddhist_guide": "佛经诵读指导（推荐具体经名如《心经》《大悲咒》+功德说明+最佳诵读时段，60字以内）",
  "taoist_guide": "道教经典指导（推荐具体经名如《道德经》某章+修炼要点+打坐/导引建议，60字以内）",
  "christian_guide": "基督教灵修指导（推荐具体圣经章节+默想主题+祈祷建议，60字以内）",
  "seasonal_produce": "本季时令蔬菜水果（3-5种当季食材+养生功效，60字以内）",
  "travel_spots": "时令旅游景点（2-3个最适合本季节游览的景点+推荐理由+注意事项，100字以内）"
}}"""

    _required = ["greeting_text","health_tip","solar_term_note","activity_suggestion",
                 "seasonal_recipe","outfit_color","activity_direction","reading_guide",
                 "buddhist_guide","taoist_guide","christian_guide","seasonal_produce","travel_spots"]

    if get_active_provider() != "anthropic":
        text = await chat_complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
        )
        return DailyGreeting(**_extract_json(text))

    try:
        client = get_client()
        response = client.messages.create(
            model=MODEL_FAST,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {k: {"type": "string"} if k != "solar_term_note"
                                       else {"type": ["string", "null"]} for k in _required},
                        "required": _required,
                        "additionalProperties": False,
                    },
                }
            },
        )
        text = next(b.text for b in response.content if b.type == "text")
        return DailyGreeting(**json.loads(text))
    except Exception as e:
        err = str(e)
        if "api_key" in err.lower() or "authentication" in err.lower() or "401" in err:
            raise ValueError("Anthropic API Key 未配置，请在顶部配置 API Key")
        raise


async def process_voice_diary(
    voice_transcript: str,      # 语音识别后的文字
    user_nickname: str,
    record_date: str | None = None,
) -> DiaryEntry:
    """
    语音日记 AI 整理
    老人说完，Claude 帮整理成结构化、可读性强的日记
    """
    today = record_date or datetime.now(UTC).strftime("%Y年%m月%d日")

    system = f"你是{user_nickname}的私人日记助理，帮助将口述内容整理为优美的日记。风格：温暖、真实、有生活气息，保留口语的亲切感，但文字更流畅。"
    user_msg = f"""请将以下口述内容整理为日记（{today}）：

{voice_transcript}

只返回 JSON，不要有任何其他文字：
{{
  "title": "日记标题（10字以内）",
  "summary": "一句话摘要（20字以内）",
  "mood_analysis": "情绪分析（如：愉快、平静、有些思念）",
  "key_moments": ["关键时刻1", "关键时刻2"],
  "formatted_entry": "整理后的完整日记正文"
}}"""

    if get_active_provider() != "anthropic":
        text = await chat_complete(
            messages=[{"role": "user", "content": user_msg}],
            system=system,
            max_tokens=1024,
        )
        return DiaryEntry(**_extract_json(text))

    try:
        client = get_client()
        response = client.messages.create(
            model=MODEL_PRIMARY,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "mood_analysis": {"type": "string"},
                            "key_moments": {"type": "array", "items": {"type": "string"}},
                            "formatted_entry": {"type": "string"},
                        },
                        "required": ["title", "summary", "mood_analysis",
                                     "key_moments", "formatted_entry"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        text = next(b.text for b in response.content if b.type == "text")
        return DiaryEntry(**json.loads(text))
    except Exception as e:
        err = str(e)
        if "api_key" in err.lower() or "authentication" in err.lower() or "401" in err:
            raise ValueError("Anthropic API Key 未配置，请在顶部配置 API Key")
        raise
