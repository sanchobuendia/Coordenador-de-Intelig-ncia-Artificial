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
