from evaluator.nodes import synthesizer as synthesizer_module
from evaluator.nodes.synthesizer import build_executive_summary, build_improvements, build_strengths, classify, heuristic_synthesize
from evaluator.schemas import (
    AssertivenessAnalysis,
    ComplianceAnalysis,
    ConversationMetadata,
    CriterionScore,
    ExtractedFacts,
    FlowAnalysis,
    LeadProfile,
    QualificationAnalysis,
    ResolutionAnalysis,
)


def build_facts(session_id: str = "S_syn") -> ExtractedFacts:
    return ExtractedFacts(
        metadata=ConversationMetadata(session_id=session_id, total_turns=2, lead_turn_count=1, bot_turn_count=1),
        lead_profile=LeadProfile(lead_name_informed="Ana", lead_area_of_interest="Saúde Mental"),
        qualification=QualificationAnalysis(),
        assertiveness=AssertivenessAnalysis(),
        flow=FlowAnalysis(flow_progression=["saudação", "cta"]),
        compliance=ComplianceAnalysis(),
        resolution=ResolutionAnalysis(resolution_status="resolved_in_chat", cta_present=True, last_message_sender="bot"),
    )


def build_score(criterion_id: str, score: float, deductions=None) -> CriterionScore:
    names = {
        "C1": "Identificação e compreensão da necessidade",
        "C2": "Assertividade da resposta",
        "C3": "Condução e fluxo da conversa",
        "C4": "Conformidade com regras de negócio",
        "C5": "Desfecho e encaminhamento",
    }
    return CriterionScore(
        criterion_id=criterion_id,
        criterion_name=names[criterion_id],
        score=score,
        justification=f"justificativa {criterion_id}",
        deductions=deductions or [],
    )


def test_classify_thresholds():
    assert classify(39.9) == "critico"
    assert classify(59.9) == "atencao"
    assert classify(74.9) == "regular"
    assert classify(89.9) == "bom"
    assert classify(90.0) == "excelente"


def test_build_strengths_and_improvements():
    scores = {
        "C1": build_score("C1", 95),
        "C2": build_score("C2", 85),
        "C3": build_score("C3", 40, ["perda de contexto: -20pts"]),
        "C4": build_score("C4", 60, ["nome errado do lead: -25pts"]),
        "C5": build_score("C5", 70),
    }
    strengths = build_strengths(scores)
    improvements = build_improvements(scores)
    assert len(strengths) == 3
    assert strengths[0].startswith("C1")
    assert any("corrigir" in item for item in improvements)
    summary = build_executive_summary(scores, "bom", "material_sent")
    assert "material_sent" in summary
    assert "C1" in summary


def test_heuristic_synthesize_builds_weighted_report():
    scores = [
        build_score("C1", 100),
        build_score("C2", 100),
        build_score("C3", 80),
        build_score("C4", 80),
        build_score("C5", 90),
    ]
    original = synthesizer_module.llm_executive_summary
    synthesizer_module.llm_executive_summary = lambda report: "Resumo executivo do atendimento."
    try:
        report = heuristic_synthesize("S_syn", build_facts(), scores)
    finally:
        synthesizer_module.llm_executive_summary = original
    assert report.session_id == "S_syn"
    assert report.score_final == 91.0
    assert report.classification == "excelente"
    assert report.executive_summary == "Resumo executivo do atendimento."
    assert len(report.strengths) == 3
    assert len(report.improvement_areas) == 3


def test_heuristic_synthesize_falls_back_when_llm_summary_fails():
    scores = [
        build_score("C1", 90),
        build_score("C2", 80, ["pergunta desviada: -10pts"]),
        build_score("C3", 70),
        build_score("C4", 60),
        build_score("C5", 90),
    ]
    original = synthesizer_module.llm_executive_summary
    synthesizer_module.llm_executive_summary = lambda report: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        report = heuristic_synthesize("S_syn", build_facts(), scores)
    finally:
        synthesizer_module.llm_executive_summary = original
    assert report.executive_summary
    assert "status final do atendimento" in report.executive_summary.lower()
