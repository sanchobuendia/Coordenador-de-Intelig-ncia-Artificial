from evaluator.schemas import EvaluationRequest, EvaluationResponse
from evaluator.schemas import ErrorDetail
from evaluator.schemas import EvaluationReport


def test_evaluation_request_to_text():
    request = EvaluationRequest(
        sessionId="S_1",
        messages=[
            "human: Olá",
            "ai: Oi",
        ],
    )
    assert request.to_conversation_text() == "human: Olá\nai: Oi"


def test_evaluation_request_requires_both_roles():
    try:
        EvaluationRequest(sessionId="S_2", messages=["human: Olá", "human: Tudo bem?"])
    except Exception as exc:
        assert "human" in str(exc)
        assert "ai" in str(exc)
    else:
        raise AssertionError("Validation should have failed")


def test_evaluation_request_requires_prefixed_messages():
    try:
        EvaluationRequest(sessionId="S_3", messages=["Olá", "ai: Oi"])
    except Exception as exc:
        assert "formato" in str(exc)
    else:
        raise AssertionError("Validation should have failed")


def test_response_and_error_schemas_accept_payloads():
    assert EvaluationResponse.model_fields["success"].default is True
    assert ErrorDetail(error="x").success is False
    assert "score_final" in EvaluationReport.model_fields
    assert "executive_summary" in EvaluationReport.model_fields
