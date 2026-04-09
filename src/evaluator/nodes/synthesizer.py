from __future__ import annotations

import json
import logging

from evaluator.config import build_chat_model_with_fallback
from evaluator.nodes.evaluators import WEIGHTS
from evaluator.prompts import SYNTHESIZER_PROMPT
from evaluator.schemas import CriterionScore, EvaluationReport, ExtractedFacts, utc_now_iso

logger = logging.getLogger("evaluator.synthesizer")


def classify(score: float) -> str:
    if score < 50:
        return "critico"
    if score < 70:
        return "atencao"
    if score < 85:
        return "regular"
    if score < 95:
        return "bom"
    return "excelente"


def apply_score_caps(score: float, extracted_facts: ExtractedFacts) -> float:
    caps: list[float] = []
    if extracted_facts.compliance.name_mismatch:
        caps.append(75.0)
    if extracted_facts.flow.wrong_course_assumed:
        caps.append(70.0)
    if extracted_facts.assertiveness.unanswered_questions:
        caps.append(78.0)
    if extracted_facts.flow.duplicate_bot_messages and extracted_facts.resolution.resolution_status == "pending":
        caps.append(82.0)
    if extracted_facts.qualification.info_assumed_without_confirmation and extracted_facts.resolution.resolution_status == "pending":
        caps.append(84.0)
    return min([score, *caps]) if caps else score


def build_strengths(scores: dict[str, CriterionScore]) -> list[str]:
    best = sorted(scores.values(), key=lambda item: item.score, reverse=True)[:3]
    return [f"{item.criterion_id} com score {item.score:.1f}: {item.justification}" for item in best]


def build_improvements(scores: dict[str, CriterionScore]) -> list[str]:
    worst = sorted(scores.values(), key=lambda item: item.score)[:3]
    items: list[str] = []
    for score in worst:
        deductions = score.deductions or []
        if deductions:
            items.append(f"{score.criterion_id}: corrigir {'; '.join(deductions)}")
        else:
            items.append(f"{score.criterion_id}: aprofundar o critério '{score.criterion_name}'.")
    return items


def build_executive_summary(scores: dict[str, CriterionScore], classification: str, resolution_status: str) -> str:
    best = max(scores.values(), key=lambda item: item.score)
    worst = min(scores.values(), key=lambda item: item.score)
    strengths = "sem deduções relevantes" if not (best.deductions or []) else f"com destaque para {best.criterion_id}"
    attention = (
        "Sem pontos críticos identificados."
        if not (worst.deductions or [])
        else f"Principal atenção em {worst.criterion_id}: {'; '.join(worst.deductions or [])}."
    )
    return (
        f"Atendimento classificado como {classification}, com score final {sum(scores[item].score * weight for item, weight in WEIGHTS.items()):.1f}. "
        f"O melhor desempenho apareceu em {best.criterion_id} ({best.criterion_name}), {strengths}. "
        f"{attention} "
        f"O status final do atendimento foi '{resolution_status}'."
    )


def _content_to_text(response) -> str:
    if isinstance(response, str):
        return response.strip()
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            text = getattr(item, "text", None)
            if text:
                parts.append(str(text))
                continue
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return " ".join(part.strip() for part in parts if part and part.strip()).strip()
    return str(content).strip()


def llm_executive_summary(report: EvaluationReport) -> str:
    model = build_chat_model_with_fallback()
    prompt = SYNTHESIZER_PROMPT.format(report_json=json.dumps(report.model_dump(mode="json"), ensure_ascii=False))
    response = model.invoke(prompt)
    return _content_to_text(response)


def heuristic_synthesize(session_id: str, extracted_facts: ExtractedFacts, criterion_scores: list[CriterionScore]) -> EvaluationReport:
    scores = {score.criterion_id: score for score in criterion_scores}
    weighted = sum(scores[criterion_id].score * weight for criterion_id, weight in WEIGHTS.items())
    final_score = round(apply_score_caps(weighted, extracted_facts), 1)
    report = EvaluationReport(
        session_id=session_id,
        evaluated_at=utc_now_iso(),
        score_final=final_score,
        classification=classify(final_score),
        scores=scores,
        extracted_facts=extracted_facts,
        strengths=build_strengths(scores),
        improvement_areas=build_improvements(scores),
    )
    try:
        report.executive_summary = llm_executive_summary(report)
    except Exception as exc:  # pragma: no cover - exercised via monkeypatch in tests
        logger.warning("[%s] Falha ao gerar resumo executivo via LLM; usando fallback determinístico: %s", session_id, exc)
        report.executive_summary = build_executive_summary(scores, report.classification, extracted_facts.resolution.resolution_status)
    return report


def run_synthesizer(state: dict) -> dict:
    session_id = state["session_id"]
    extracted_facts = state["extracted_facts"]
    criterion_scores = state["criterion_scores"]
    logger.info("[%s] Iniciando síntese final", session_id)
    logger.debug("[%s] Síntese com sumarização executiva via LLM e fallback determinístico", session_id)
    report = heuristic_synthesize(session_id, extracted_facts, criterion_scores)
    logger.info("[%s] Síntese concluída com score %.1f", session_id, report.score_final)
    logger.debug("[%s] Relatório sintetizado: %s", session_id, report.model_dump(mode="json"))
    return {"report": report}
