from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_chat_endpoint():
    r = client.post("/chat", json={"message": "I lost my card"})
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert "messages" in data 