"""
API 路由基础测试（不调用真实 Claude API）
测试路由注册、请求解析、响应结构
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "银龄AI伴伴后端"
    assert data["ai_model"] == "claude-opus-4-6"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_stream_requires_body(client: AsyncClient):
    """缺少必填字段时应返回 422"""
    resp = await client.post("/api/v1/chat/stream", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_message_requires_body(client: AsyncClient):
    resp = await client.post("/api/v1/chat/message", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_consult_requires_body(client: AsyncClient):
    resp = await client.post("/api/v1/health/consult/stream", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_fraud_check_requires_content(client: AsyncClient):
    resp = await client.post("/api/v1/safety/fraud/check", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_content_check_requires_content(client: AsyncClient):
    resp = await client.post("/api/v1/safety/content/check", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sos_requires_user_id(client: AsyncClient):
    resp = await client.post("/api/v1/health/sos", json={})
    assert resp.status_code == 422
