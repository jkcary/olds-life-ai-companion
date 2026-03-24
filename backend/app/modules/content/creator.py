"""
生活分享内容创作模块
AI 原生设计：
  - Vlog：Claude 根据标签生成标题、描述、字幕文案，降低老人创作门槛
  - 每日问候：Claude 结合节气/天气/用户记忆生成个性化问候语
  - 日记总结：Claude 将用户语音转文字后，自动生成结构化日记条目
"""
import json
from datetime import date, datetime, UTC
from pydantic import BaseModel

from app.core.claude_client import get_client, MODEL_PRIMARY, MODEL_FAST


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
    client = get_client()

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

以 JSON 返回：
{{
  "title": "视频标题",
  "description": "视频简介",
  "tags": ["标签1", "标签2", "标签3"],
  "caption_script": "字幕旁白文案",
  "background_music_mood": "背景音乐风格建议"
}}"""

    response = client.messages.create(
        model=MODEL_FAST,           # Haiku 处理内容生成，控制成本
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


async def generate_daily_greeting(
    user_nickname: str,
    user_profile_summary: str,
    session: str = "morning",      # morning / evening
    weather_desc: str | None = None,
) -> DailyGreeting:
    """
    每日个性化问候生成
    结合节气、天气、用户记忆，让每次问候都不一样
    由后台定时任务（每天7点/20点）调用
    """
    client = get_client()

    today = datetime.now(UTC).strftime("%Y年%m月%d日")
    solar_term = get_current_solar_term()
    solar_str = f"今天临近{solar_term}节气，" if solar_term else ""
    weather_str = f"今天天气{weather_desc}，" if weather_desc else ""
    session_str = "早上好" if session == "morning" else "晚上好"

    prompt = f"""为老年用户生成一条{session_str}的个性化问候。

用户昵称：{user_nickname}
用户信息：{user_profile_summary}
今天日期：{today}
{solar_str}{weather_str}

要求：
- 问候语温暖亲切，像子女发来的消息
- 结合节气或天气给出实用的养生提示
- 活动建议要具体、简单易行
- 整体语气积极向上，不超过120字

以 JSON 返回：
{{
  "greeting_text": "主要问候语（60字以内）",
  "health_tip": "今日养生建议（30字以内）",
  "solar_term_note": "节气相关内容或null",
  "activity_suggestion": "今日活动建议（20字以内）"
}}"""

    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "greeting_text": {"type": "string"},
                        "health_tip": {"type": "string"},
                        "solar_term_note": {"type": ["string", "null"]},
                        "activity_suggestion": {"type": "string"},
                    },
                    "required": ["greeting_text", "health_tip",
                                 "solar_term_note", "activity_suggestion"],
                    "additionalProperties": False,
                },
            }
        },
    )
    text = next(b.text for b in response.content if b.type == "text")
    return DailyGreeting(**json.loads(text))


async def process_voice_diary(
    voice_transcript: str,      # 语音识别后的文字
    user_nickname: str,
    record_date: str | None = None,
) -> DiaryEntry:
    """
    语音日记 AI 整理
    老人说完，Claude 帮整理成结构化、可读性强的日记
    """
    client = get_client()

    today = record_date or datetime.now(UTC).strftime("%Y年%m月%d日")

    response = client.messages.create(
        model=MODEL_PRIMARY,
        max_tokens=1024,
        system=f"""你是{user_nickname}的私人日记助理，帮助将口述内容整理为优美的日记。
风格：温暖、真实、有生活气息，保留口语的亲切感，但文字更流畅。""",
        messages=[{
            "role": "user",
            "content": f"""请将以下口述内容整理为日记（{today}）：

{voice_transcript}

以 JSON 返回：
{{
  "title": "日记标题（10字以内）",
  "summary": "一句话摘要（20字以内）",
  "mood_analysis": "情绪分析（如：愉快、平静、有些思念）",
  "key_moments": ["关键时刻1", "关键时刻2"],
  "formatted_entry": "整理后的完整日记正文"
}}"""
        }],
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
