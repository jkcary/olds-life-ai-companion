"""
全栈集成测试 — 打真实运行中的服务器（不调用 Claude API）
测试所有路由的：可达性、请求验证、响应格式
"""
import pytest
import httpx

BASE = "http://localhost:8000"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "running"
    assert d["version"] == "1.1.0"
    assert "demo" in d


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_demo_page_served(client):
    r = client.get("/demo")
    assert r.status_code == 200
    assert "银龄AI伴伴" in r.text
    assert "text/html" in r.headers["content-type"]


def test_openapi_docs(client):
    r = client.get("/docs")
    assert r.status_code == 200


def test_openapi_json_has_all_routes(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    expected = [
        "/api/v1/chat/stream",
        "/api/v1/health/consult/stream",
        "/api/v1/safety/fraud/check",
        "/api/v1/social/match/analyze",
        "/api/v1/social/circles/recommend",
        "/api/v1/navigation/route/plan",
        "/api/v1/content/vlog/generate",
        "/api/v1/content/greeting/daily",
        "/api/v1/content/diary/process",
    ]
    for path in expected:
        assert path in paths, f"路由未注册: {path}"


# ── 请求验证（422）——不需要 API Key ──

def test_chat_stream_requires_message(client):
    r = client.post("/api/v1/chat/stream", json={})
    assert r.status_code == 422

def test_chat_stream_requires_user_id(client):
    r = client.post("/api/v1/chat/stream", json={"message": "你好"})
    assert r.status_code == 422

def test_chat_stream_valid_request_accepted(client):
    """有效请求应被接受（200），SSE 端点用流式读取避免 incomplete chunked read"""
    with client.stream("POST", "/api/v1/chat/stream",
                       json={"user_id": "integ_test", "message": "你好"}) as r:
        # 200 = accepted and streaming; 500 = API key not configured — both are not 422
        assert r.status_code != 422

def test_health_consult_requires_message(client):
    r = client.post("/api/v1/health/consult/stream", json={"user_id": "x"})
    assert r.status_code == 422

def test_fraud_check_requires_content(client):
    r = client.post("/api/v1/safety/fraud/check", json={})
    assert r.status_code == 422

def test_fraud_check_valid_accepted(client):
    r = client.post("/api/v1/safety/fraud/check",
                    json={"content": "您好，我是公安局的"})
    assert r.status_code != 422

def test_social_match_requires_body(client):
    r = client.post("/api/v1/social/match/analyze", json={})
    assert r.status_code == 422

def test_vlog_generate_requires_fields(client):
    r = client.post("/api/v1/content/vlog/generate", json={})
    assert r.status_code == 422

def test_vlog_valid_accepted(client):
    r = client.post("/api/v1/content/vlog/generate", json={
        "content_tags": ["做饭", "红烧肉"],
        "raw_description": "今天做了红烧肉"
    })
    assert r.status_code != 422

def test_greeting_requires_nickname(client):
    r = client.post("/api/v1/content/greeting/daily", json={})
    assert r.status_code == 422

def test_navigation_requires_fields(client):
    r = client.post("/api/v1/navigation/route/plan", json={})
    assert r.status_code == 422

def test_navigation_valid_accepted(client):
    r = client.post("/api/v1/navigation/route/plan", json={
        "origin_desc": "中山公园东门",
        "destination_desc": "最近的人民医院",
    })
    assert r.status_code != 422
