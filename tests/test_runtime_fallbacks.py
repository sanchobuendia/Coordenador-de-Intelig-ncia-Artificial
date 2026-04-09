from evaluator.nodes.extractor import run_extractor


def test_run_extractor_falls_back_to_heuristic_when_llm_fails(monkeypatch):
    monkeypatch.setattr("evaluator.nodes.extractor.llm_extract", lambda state: (_ for _ in ()).throw(RuntimeError("boom")))
    result = run_extractor(
        {
            "session_id": "S_fallback",
            "conversation": "human: Eu sou Ana\nai: Olá, Ana! Posso te enviar o material.",
        }
    )
    assert result["extracted_facts"].metadata.session_id == "S_fallback"


def test_run_extractor_preserves_security_analysis(monkeypatch):
    monkeypatch.setattr("evaluator.nodes.extractor.llm_extract", lambda state: (_ for _ in ()).throw(RuntimeError("boom")))
    result = run_extractor(
        {
            "session_id": "S_security",
            "conversation": "human: Eu sou [REDACTED_NAME]\nai: Olá, [REDACTED_NAME]!",
            "security": {
                "prompt_injection_detected": True,
                "prompt_injection_signals": ["ignore instructions"],
                "sensitive_data_redacted": True,
                "redacted_entities": ["name"],
                "redaction_count": 2,
                "conversation_sanitized": True,
            },
        }
    )
    assert result["extracted_facts"].security.prompt_injection_detected is True
    assert result["extracted_facts"].security.sensitive_data_redacted is True
