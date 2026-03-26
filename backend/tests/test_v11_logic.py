"""
v1.1 业务逻辑单元测试（不依赖 Claude API）
测试纯 Python 逻辑：节气计算、工具参数验证、数据结构
"""
import pytest
from datetime import date
from unittest.mock import patch, AsyncMock

from app.modules.content.creator import get_current_solar_term, SOLAR_TERMS
from app.modules.social.matcher import PRESET_CIRCLES, FriendMatchProfile
from app.modules.navigation.advisor import NavigationStep, NavigationPlan


# ─── 节气计算 ────────────────────────────────────────────────────────────────

def test_solar_term_on_exact_date():
    """节气当天应能识别"""
    term = get_current_solar_term(today=date(2026, 3, 6))  # 惊蛰
    assert term == "惊蛰"


def test_solar_term_within_3_days():
    """节气前后3天内应能识别"""
    term = get_current_solar_term(today=date(2026, 3, 8))  # 惊蛰+2天
    assert term == "惊蛰"


def test_solar_term_out_of_range():
    """非节气期间返回 None"""
    term = get_current_solar_term(today=date(2026, 3, 15))  # 无节气
    assert term is None


def test_solar_terms_count():
    """确保24节气都定义了"""
    assert len(SOLAR_TERMS) == 24


# ─── 社交圈子数据 ────────────────────────────────────────────────────────────

def test_preset_circles_structure():
    for circle in PRESET_CIRCLES:
        assert "id" in circle
        assert "name" in circle
        assert "tags" in circle
        assert isinstance(circle["tags"], list)
        assert len(circle["tags"]) >= 2


def test_preset_circles_unique_ids():
    ids = [c["id"] for c in PRESET_CIRCLES]
    assert len(ids) == len(set(ids))


def test_preset_circles_count():
    assert len(PRESET_CIRCLES) >= 10


# ─── 数据模型验证 ────────────────────────────────────────────────────────────

def test_friend_match_profile_defaults():
    profile = FriendMatchProfile(user_id="u1", nickname="王阿姨", age=68)
    assert profile.hobbies == []
    assert profile.era_keywords == []
    assert profile.hometown is None


def test_friend_match_profile_full():
    profile = FriendMatchProfile(
        user_id="u2",
        nickname="李大爷",
        age=72,
        hometown="哈尔滨",
        work_history="1975-1995年在哈尔滨机车厂",
        hobbies=["钓鱼", "太极拳"],
        era_keywords=["知青"],
    )
    assert profile.age == 72
    assert "钓鱼" in profile.hobbies


def test_navigation_step_model():
    step = NavigationStep(
        step_no=1,
        instruction="沿中山路向北步行300米",
        distance_m=300,
        landmark="中山公园大门",
        accessibility_note="有坡道，轮椅可通行",
    )
    assert step.step_no == 1
    assert step.distance_m == 300


def test_navigation_plan_model():
    plan = NavigationPlan(
        destination="人民医院",
        total_distance_m=800,
        estimated_minutes=15,
        route_type="步行",
        steps=[
            NavigationStep(
                step_no=1,
                instruction="向前直走500米",
                distance_m=500,
                landmark=None,
                accessibility_note=None,
            )
        ],
        rest_points=["中山公园长椅"],
    )
    assert plan.total_distance_m == 800
    assert len(plan.steps) == 1
    assert len(plan.rest_points) == 1


# ─── 社交模块过滤逻辑 ────────────────────────────────────────────────────────

def test_already_joined_filter():
    """已加入圈子不应出现在候选列表中"""
    joined = {"taichi", "singing"}
    available = [c for c in PRESET_CIRCLES if c["id"] not in joined]
    available_ids = {c["id"] for c in available}
    assert "taichi" not in available_ids
    assert "singing" not in available_ids
    assert len(available) == len(PRESET_CIRCLES) - 2
