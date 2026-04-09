from __future__ import annotations

import logging

from evaluator.nodes.evaluators import WEIGHTS
from evaluator.schemas import CriterionScore, EvaluationReport, ExtractedFacts, utc_now_iso

logger = logging.getLogger("evaluator.synthesizer")


def classify(score: float) -> str:
    if score < 40:
        return "critico"
    if score < 60:
        return "atencao"
    if score < 75:
        return "regular"
    if score < 90:
        return "bom"
    return "excelente"


def build_strengths(scores: dict[str, CriterionScore]) -> list[str]:
    best = sorted(scores.values(), key=lambda item: item.score, reverse=True)[:3]
    return [f"{item.criterion_id} com score {item.score:.1f}: {item.justification}" for item in best]


def build_improvements(scores: dict[str, CriterionScore]) -> list[str]:
    worst = sorted(scores.values(), key=lambda item: item.score)[:3]
    items: list[str] = []
    for score in worst:
        if score.deductions:
            items.append(f"{score.criterion_id}: corrigir {'; '.join(score.deductions)}")
        else:
            items.append(f"{score.criterion_id}: aprofundar o critério '{score.criterion_name}'.")
    return items


def heuristic_synthesize(session_id: str, extracted_facts: ExtractedFacts, criterion_scores: list[CriterionScore]) -> EvaluationReport:
    scores = {score.criterion_id: score for score in criterion_scores}
    weighted = sum(scores[criterion_id].score * weight for criterion_id, weight in WEIGHTS.items())
    final_score = round(weighted, 1)
    return EvaluationReport(
        session_id=session_id,
        evaluated_at=utc_now_iso(),
        score_final=final_score,
        classification=classify(final_score),
        scores=scores,
        extracted_facts=extracted_facts,
        strengths=build_strengths(scores),
        improvement_areas=build_improvements(scores),
    )


def run_synthesizer(state: dict) -> dict:
    session_id = state["session_id"]
    extracted_facts = state["extracted_facts"]
    criterion_scores = state["criterion_scores"]
    logger.info("[%s] Iniciando síntese final", session_id)
    logger.debug("[%s] Síntese via regra determinística", session_id)
    report = heuristic_synthesize(session_id, extracted_facts, criterion_scores)
    logger.info("[%s] Síntese concluída com score %.1f", session_id, report.score_final)
    logger.debug("[%s] Relatório sintetizado: %s", session_id, report.model_dump(mode="json"))
    return {"report": report}
