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
    assert "extracted_facts" not in payload["data"]
    assert "evidences" not in payload["data"]["scores"]["C1"]
    assert "deductions" not in payload["data"]["scores"]["C1"]
    assert payload["data"]["executive_summary"]


def test_evaluate_endpoint_verbose_mode():
    response = client.post(
        "/evaluate?verbose=true",
        json={
            "sessionId": "S_api_verbose",
            "messages": [
                "human: Oi, me chamo Ana e quero uma pós em Saúde Mental.",
                "ai: Olá, Ana! Posso te enviar o material e te encaminhar para a especialista.",
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["session_id"] == "S_api_verbose"
    assert "extracted_facts" in payload["data"]
    assert "security" in payload["data"]["extracted_facts"]
    assert "evidences" in payload["data"]["scores"]["C1"]
    assert "deductions" in payload["data"]["scores"]["C1"]


def test_evaluate_endpoint_verbose_masks_sensitive_data():
    response = client.post(
        "/evaluate?verbose=true",
        json={
            "sessionId": "S_api_masked",
            "messages": [
                "human: Eu sou Ana e meu CPF é 123.456.789-00 e telefone 11998765432",
                "ai: Olá, Ana! Posso te encaminhar para especialista.",
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    security = payload["data"]["extracted_facts"]["security"]
    assert security["sensitive_data_redacted"] is True
    assert "cpf" in security["redacted_entities"]
    assert "phone" in security["redacted_entities"]


def test_evaluate_requires_both_roles():
    response = client.post(
        "/evaluate",
        json={"sessionId": "S_invalid", "messages": ["human: Oi", "human: Tudo bem?"]},
    )
    assert response.status_code == 422
    assert response.json()["success"] is False
