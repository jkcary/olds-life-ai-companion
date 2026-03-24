"""
用户记忆管理
Claude 通过工具调用来读写记忆，实现真正的个性化陪伴
"""
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def save_memory(
    db: AsyncSession,
    user_id: str,
    category: str,
    key: str,
    value: str,
    note: str | None = None,
) -> dict:
    """工具执行函数：保存用户记忆"""
    await db.execute(
        text("""
            INSERT INTO user_memories (user_id, category, key, value, note, updated_at)
            VALUES (:user_id, :category, :key, :value, :note, :updated_at)
            ON CONFLICT (user_id, category, key)
            DO UPDATE SET value = :value, note = :note, updated_at = :updated_at
        """),
        {
            "user_id": user_id,
            "category": category,
            "key": key,
            "value": value,
            "note": note,
            "updated_at": datetime.utcnow().isoformat(),
        },
    )
    await db.commit()
    return {"success": True, "message": f"已记住：{key} = {value}"}


async def get_memory(
    db: AsyncSession,
    user_id: str,
    category: str = "all",
) -> dict:
    """工具执行函数：读取用户记忆"""
    if category == "all":
        result = await db.execute(
            text("SELECT category, key, value, note FROM user_memories WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
    else:
        result = await db.execute(
            text("""
                SELECT category, key, value, note FROM user_memories
                WHERE user_id = :user_id AND category = :category
            """),
            {"user_id": user_id, "category": category},
        )
    rows = result.fetchall()
    memories: dict[str, dict] = {}
    for row in rows:
        cat, key, value, note = row
        if cat not in memories:
            memories[cat] = {}
        memories[cat][key] = {"value": value, "note": note}
    return memories


async def log_mood(
    db: AsyncSession,
    user_id: str,
    mood: str,
    trigger: str | None = None,
) -> dict:
    """工具执行函数：记录情绪"""
    await db.execute(
        text("""
            INSERT INTO mood_logs (user_id, mood, trigger, logged_at)
            VALUES (:user_id, :mood, :trigger, :logged_at)
        """),
        {
            "user_id": user_id,
            "mood": mood,
            "trigger": trigger,
            "logged_at": datetime.utcnow().isoformat(),
        },
    )
    await db.commit()
    return {"success": True, "mood_logged": mood}


async def get_user_profile_summary(db: AsyncSession, user_id: str) -> str:
    """生成用户画像摘要，注入 Claude 系统提示词"""
    memories = await get_memory(db, user_id, "all")
    if not memories:
        return "新用户，尚无个人信息记录"

    parts = []
    personal = memories.get("personal", {})
    if personal.get("name"):
        parts.append(f"姓名：{personal['name']['value']}")

    family = memories.get("family", {})
    if family:
        family_desc = "、".join(f"{k}：{v['value']}" for k, v in family.items())
        parts.append(f"家庭：{family_desc}")

    health = memories.get("health", {})
    if health:
        health_desc = "、".join(f"{k}：{v['value']}" for k, v in health.items())
        parts.append(f"健康状况：{health_desc}")

    hobby = memories.get("hobby", {})
    if hobby:
        hobbies = "、".join(v["value"] for v in hobby.values())
        parts.append(f"兴趣爱好：{hobbies}")

    return "；".join(parts) if parts else "已建立用户档案"
