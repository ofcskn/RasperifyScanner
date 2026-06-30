import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from main import app
from app.models.database import init_db, engine, Base
from app.services.auth import auth_service
from app.services.ai.base import AnalysisResult


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_token(client):
    from app.models.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await auth_service.create_user(db, "admin", "password123")
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "password123"})
    return resp.json()["access_token"]


async def test_health_endpoint(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_login_success(client):
    from app.models.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await auth_service.create_user(db, "user1", "pass")
    resp = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client):
    from app.models.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await auth_service.create_user(db, "user2", "correct")
    resp = await client.post("/api/v1/auth/login", json={"username": "user2", "password": "wrong"})
    assert resp.status_code == 401


async def test_analyze_requires_auth(client):
    resp = await client.post("/api/v1/analyze", json={"frame_base64": "abc"})
    assert resp.status_code == 403


async def test_analyze_with_auth(client, auth_token):
    mock_result = AnalysisResult(provider="gemini", raw_response="{}", detections=[], metrics={})
    with patch("app.services.pipeline.multi_ai_service.analyze", new_callable=AsyncMock, return_value=mock_result):
        resp = await client.post(
            "/api/v1/analyze",
            json={"frame_base64": "dGVzdA=="},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert resp.status_code == 202


async def test_results_list_requires_auth(client):
    resp = await client.get("/api/v1/results")
    assert resp.status_code == 403


async def test_manual_scan_bypasses_motion_gate():
    """A manual (forced) scan must produce a result even on a static scene,
    while an automated run on the same static scene is still motion-gated.
    Regression guard for "Run Scan Now -> No analysis results yet"."""
    from app.services.pipeline import AnalysisPipelineController

    ctrl = AnalysisPipelineController()
    ctrl._last_frame_b64 = "dGVzdA=="  # prime baseline so the motion gate is armed

    snapshot = {"people_live": 0, "people_cumulative": 0, "detections": []}
    ai = AnalysisResult(provider="onnx-yolo", raw_response="{}", detections=[], metrics={})

    with patch("app.services.pipeline._frame_diff", return_value=0.0), \
         patch("app.services.pipeline.detection_service.snapshot", return_value=snapshot), \
         patch("app.services.pipeline.multi_ai_service.analyze", new_callable=AsyncMock, return_value=ai), \
         patch("app.services.pipeline.connection_service.broadcast", new_callable=AsyncMock):
        # Automated run, identical frame → gate skips, nothing persisted.
        gated = await ctrl.run(frame_base64="dGVzdA==")
        assert gated["event"] == "no_motion"

        # Manual run, identical frame → force past the gate, analysis persisted.
        forced = await ctrl.run(frame_base64="dGVzdA==", force=True)
        assert forced["event"] == "analysis_complete"
        assert forced["id"] is not None
