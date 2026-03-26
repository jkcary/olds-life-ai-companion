"""
v1.1 新路由注册和请求校验测试（不调用真实 Claude API）
"""
import pytest
from httpx import AsyncClient


# ─── 社交交友 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_match_analyze_requires_body(client: AsyncClient):
    resp = await client.post("/api/v1/social/match/analyze", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_circle_recommend_requires_user_id(client: AsyncClient):
    resp = await client.post("/api/v1/social/circles/recommend", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_friend_search_parse_requires_query(client: AsyncClient):
    resp = await client.post("/api/v1/social/friends/search/parse", json={})
    assert resp.status_code == 422


# ─── 出行出游 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_route_plan_requires_fields(client: AsyncClient):
    resp = await client.post("/api/v1/navigation/route/plan", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_attraction_explain_requires_name(client: AsyncClient):
    resp = await client.post("/api/v1/navigation/attraction/explain/stream", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_travel_plan_requires_fields(client: AsyncClient):
    resp = await client.post("/api/v1/navigation/travel/plan", json={})
    assert resp.status_code == 422


# ─── 生活分享 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vlog_generate_requires_fields(client: AsyncClient):
    resp = await client.post("/api/v1/content/vlog/generate", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_greeting_requires_nickname(client: AsyncClient):
    resp = await client.post("/api/v1/content/greeting/daily", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_diary_requires_transcript(client: AsyncClient):
    resp = await client.post("/api/v1/content/diary/process", json={})
    assert resp.status_code == 422


# ─── 路由注册完整性 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_openapi_includes_all_v11_routes(client: AsyncClient):
    """确认所有 v1.1 路由都注册到 OpenAPI 文档"""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]

    expected = [
        "/api/v1/social/match/analyze",
        "/api/v1/social/circles/recommend",
        "/api/v1/social/friends/search/parse",
        "/api/v1/navigation/route/plan",
        "/api/v1/navigation/attraction/explain/stream",
        "/api/v1/navigation/travel/plan",
        "/api/v1/content/vlog/generate",
        "/api/v1/content/greeting/daily",
        "/api/v1/content/diary/process",
    ]
    for path in expected:
        assert path in paths, f"路由未注册: {path}"
