"""
数据库层测试：记忆、情绪、健康工具
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.modules.companion.memory import save_memory, get_memory, log_mood, get_user_profile_summary
from app.modules.health.tools import (
    check_drug_interaction,
    set_medication_reminder,
    get_health_records,
)


# ─── 记忆模块 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_get_memory(db_session: AsyncSession):
    result = await save_memory(db_session, "u1", "personal", "name", "王阿姨")
    assert result["success"] is True

    memories = await get_memory(db_session, "u1", "personal")
    assert memories["personal"]["name"]["value"] == "王阿姨"


@pytest.mark.asyncio
async def test_memory_upsert(db_session: AsyncSession):
    """同一 key 再次写入应更新而非新增"""
    await save_memory(db_session, "u2", "personal", "name", "李大爷")
    await save_memory(db_session, "u2", "personal", "name", "李老先生")

    memories = await get_memory(db_session, "u2", "personal")
    assert memories["personal"]["name"]["value"] == "李老先生"


@pytest.mark.asyncio
async def test_get_memory_all(db_session: AsyncSession):
    await save_memory(db_session, "u3", "hobby", "dancing", "广场舞")
    await save_memory(db_session, "u3", "health", "bp", "高血压")

    all_mem = await get_memory(db_session, "u3", "all")
    assert "hobby" in all_mem
    assert "health" in all_mem


@pytest.mark.asyncio
async def test_log_mood(db_session: AsyncSession):
    result = await log_mood(db_session, "u1", "happy", "今天天气好")
    assert result["success"] is True
    assert result["mood_logged"] == "happy"


@pytest.mark.asyncio
async def test_user_profile_summary_new_user(db_session: AsyncSession):
    summary = await get_user_profile_summary(db_session, "new_user_999")
    assert "新用户" in summary


@pytest.mark.asyncio
async def test_user_profile_summary_with_data(db_session: AsyncSession):
    await save_memory(db_session, "u4", "personal", "name", "张奶奶")
    await save_memory(db_session, "u4", "hobby", "knitting", "织毛衣")
    summary = await get_user_profile_summary(db_session, "u4")
    assert "张奶奶" in summary


# ─── 药物禁忌 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_drug_interaction_known_pair():
    result = await check_drug_interaction(["阿司匹林", "华法林"])
    assert result["interactions_found"] == 1
    assert result["safe"] is False
    assert result["interactions"][0]["severity"] == "high"


@pytest.mark.asyncio
async def test_drug_interaction_safe_pair():
    result = await check_drug_interaction(["维生素C", "钙片"])
    assert result["safe"] is True
    assert result["interactions_found"] == 0


@pytest.mark.asyncio
async def test_drug_interaction_requires_two():
    result = await check_drug_interaction(["阿司匹林"])
    assert "需要至少两种药物" in result["message"]


@pytest.mark.asyncio
async def test_drug_interaction_multiple():
    """三种药，其中一对有禁忌"""
    result = await check_drug_interaction(["阿司匹林", "华法林", "维生素C"])
    assert result["interactions_found"] >= 1


# ─── 用药提醒 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_medication_reminder(db_session: AsyncSession):
    result = await set_medication_reminder(
        db_session, "u1", "拜阿司匹灵", ["08:00", "20:00"], "1片", "饭后服用"
    )
    assert result["success"] is True
    assert "拜阿司匹灵" in result["message"]


@pytest.mark.asyncio
async def test_medication_reminder_upsert(db_session: AsyncSession):
    """重复设置同一药物应覆盖旧数据"""
    await set_medication_reminder(db_session, "u5", "二甲双胍", ["07:00"], "500mg")
    await set_medication_reminder(db_session, "u5", "二甲双胍", ["08:00", "18:00"], "500mg")

    records = await get_health_records(db_session, "u5", "medication")
    times = [r["time"] for r in records["medications"]]
    assert "07:00" not in times
    assert "08:00" in times


# ─── 健康档案 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_health_records_empty(db_session: AsyncSession):
    records = await get_health_records(db_session, "unknown_user", "all")
    assert isinstance(records, dict)


@pytest.mark.asyncio
async def test_get_health_records_medication(db_session: AsyncSession):
    await set_medication_reminder(db_session, "u6", "降压药", ["09:00"], "1片")
    records = await get_health_records(db_session, "u6", "medication")
    assert "medications" in records
    assert len(records["medications"]) >= 1
