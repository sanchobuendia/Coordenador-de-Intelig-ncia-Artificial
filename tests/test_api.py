from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_evaluate_endpoint():
    response = client.post(
        "/evaluate",
        json={
            "sessionId": "S_api",
            "messages": [
                "human: Oi, me chamo Ana e quero uma pós em Saúde Mental.",
                "ai: Olá, Ana! Posso te enviar o material e te encaminhar para a especialista.",
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["session_id"] == "S_api"


def test_evaluate_requires_both_roles():
    response = client.post(
        "/evaluate",
        json={"sessionId": "S_invalid", "messages": ["human: Oi", "human: Tudo bem?"]},
    )
    assert response.status_code == 422
    assert response.json()["success"] is False
