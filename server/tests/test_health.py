from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_health_ok_when_database_answers(monkeypatch):
    monkeypatch.setattr(main, "database_ok", lambda: True)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"api": "ok", "db": "ok"}


def test_health_503_when_database_down(monkeypatch):
    monkeypatch.setattr(main, "database_ok", lambda: False)
    res = client.get("/api/health")
    assert res.status_code == 503
    assert res.json() == {"api": "ok", "db": "down"}


def test_database_ok_false_without_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main.database_ok() is False
