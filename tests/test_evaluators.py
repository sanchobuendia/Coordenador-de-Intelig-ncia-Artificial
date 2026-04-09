from evaluator.nodes.evaluators import CRITERIA, heuristic_evaluate
from evaluator.nodes.extractor import heuristic_extract


def build_facts(conversation: str, session_id: str = "S_test"):
    return heuristic_extract({"session_id": session_id, "conversation": conversation})


def criterion_by_id(criterion_id: str) -> dict:
    return next(item for item in CRITERIA if item["id"] == criterion_id)


def test_c4_deducts_wrong_name():
    facts = build_facts(
        "human: Eu sou Pessoa_015\n"
        "ai: Olá, Karina! Como posso ajudar?\n"
        "human: Quero uma pós em saúde mental.\n"
        "ai: Posso te encaminhar."
    )
    score = heuristic_evaluate(criterion_by_id("C4"), facts)
    assert "nome errado do lead: -30pts" in score.deductions


def test_c2_detects_deflected_question():
    facts = build_facts(
        "human: Em qual dia da semana são as aulas ao vivo?\n"
        "ai: Elas acontecem das 19h30 às 21h."
    )
    score = heuristic_evaluate(criterion_by_id("C2"), facts)
    assert "pergunta desviada: -15pts" in score.deductions
