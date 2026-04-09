from __future__ import annotations

import logging

from evaluator.schemas import CriterionScore, ExtractedFacts

logger = logging.getLogger("evaluator.evaluators")

WEIGHTS = {"C1": 0.25, "C2": 0.25, "C3": 0.20, "C4": 0.20, "C5": 0.10}

CRITERIA = [
    {
        "id": "C1",
        "name": "Identificação e compreensão da necessidade",
        "weight": 25,
        "relevant_fields": ["lead_profile", "qualification", "flow"],
        "rubric": "Avalie se o bot entendeu área, objetivo e perfil do lead sem repetição e sem apresentar solução cedo demais. Deduzir -10 por pergunta repetida, -15 por informação assumida sem confirmação, -15 se apresentou curso antes de qualificar, -7 se objetivo não foi identificado e -5 se background/perfil não foi identificado.",
    },
    {
        "id": "C2",
        "name": "Assertividade da resposta",
        "weight": 25,
        "relevant_fields": ["assertiveness"],
        "rubric": "Avalie se respondeu diretamente às perguntas do lead. Deduzir -20 por pergunta sem resposta, -10 por pergunta desviada e -15 por curso incorreto apresentado.",
    },
    {
        "id": "C3",
        "name": "Condução e fluxo da conversa",
        "weight": 20,
        "relevant_fields": ["flow", "metadata"],
        "rubric": "Avalie a progressão lógica da conversa. Deduzir -15 por duplicação, -20 por perda de contexto, -20 por curso assumido errado e -10 por input não textual não tratado.",
    },
    {
        "id": "C4",
        "name": "Conformidade com regras de negócio",
        "weight": 20,
        "relevant_fields": ["compliance"],
        "rubric": "Avalie aderência às regras: não revelar preço, escalar quando preciso, não inventar informação e não usar nome errado. Deduzir -25 por nome errado, -40 por preço revelado, -20 por informação inventada e -30 por falta de escalada necessária.",
    },
    {
        "id": "C5",
        "name": "Desfecho e encaminhamento",
        "weight": 10,
        "relevant_fields": ["resolution"],
        "rubric": "Avalie se a conversa terminou com resolução, material enviado, CTA claro ou encaminhamento adequado.",
    },
]


def _clamp(score: float) -> float:
    return round(max(0.0, min(100.0, score)), 1)


def _summarize_deductions(deductions: list[str]) -> str:
    if not deductions:
        return "Não houve deduções aplicadas neste critério."
    return "Deduções aplicadas: " + "; ".join(deductions) + "."


def _score_c1(facts: ExtractedFacts, criterion: dict) -> CriterionScore:
    score = 100.0
    deductions: list[str] = []
    qualification = facts.qualification
    flow = facts.flow
    evidences = [
        f"lead_area_of_interest: {facts.lead_profile.lead_area_of_interest}",
        f"lead_background: {facts.lead_profile.lead_background}",
        f"lead_objective: {facts.lead_profile.lead_objective}",
        f"qualification_questions_asked: {qualification.qualification_questions_asked}",
        f"repeated_qualification_questions: {qualification.repeated_qualification_questions}",
        f"info_assumed_without_confirmation: {qualification.info_assumed_without_confirmation}",
        f"context_lost_moments: {flow.context_lost_moments}",
    ]
    if not qualification.qualification_questions_asked:
        score -= 45
        deductions.append("ausência de qualificação: -45pts")
    for _ in qualification.repeated_qualification_questions:
        score -= 12
        deductions.append("pergunta repetida sem motivo: -12pts")
    for _ in qualification.info_assumed_without_confirmation:
        score -= 20
        deductions.append("info assumida sem confirmação: -20pts")
    if not facts.lead_profile.lead_area_of_interest:
        score -= 12
        deductions.append("área de interesse não identificada: -12pts")
    if not facts.lead_profile.lead_background:
        score -= 8
        deductions.append("background do lead não identificado: -8pts")
    if not facts.lead_profile.lead_objective:
        score -= 10
        deductions.append("objetivo do lead não identificado: -10pts")
    if any("apresentou curso antes de concluir a qualificação" in item for item in flow.context_lost_moments):
        score -= 20
        deductions.append("curso apresentado antes da qualificação: -20pts")
    justification = (
        "O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. "
        f"O bot fez {len(qualification.qualification_questions_asked)} perguntas de qualificação, "
        f"registrou {len(qualification.info_assumed_without_confirmation)} suposições sem confirmação "
        f"e lead_objective={facts.lead_profile.lead_objective!r}. "
        f"{_summarize_deductions(deductions)}"
    )
    return CriterionScore(
        criterion_id="C1",
        criterion_name=criterion["name"],
        score=_clamp(score),
        justification=justification,
        evidences=evidences,
        deductions=deductions,
    )


def _score_c2(facts: ExtractedFacts, criterion: dict) -> CriterionScore:
    score = 100.0
    deductions: list[str] = []
    assertiveness = facts.assertiveness
    evidences = [
        f"lead_questions_asked: {assertiveness.lead_questions_asked}",
        f"unanswered_questions: {assertiveness.unanswered_questions}",
        f"deflected_questions: {assertiveness.deflected_questions}",
        f"course_correctly_identified: {assertiveness.course_correctly_identified}",
    ]
    for _ in assertiveness.unanswered_questions:
        score -= 25
        deductions.append("pergunta sem resposta: -25pts")
    for _ in assertiveness.deflected_questions:
        score -= 15
        deductions.append("pergunta desviada: -15pts")
    if assertiveness.course_correctly_identified is False:
        score -= 20
        deductions.append("curso incorreto apresentado: -20pts")
    justification = (
        "O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. "
        f"Foram identificadas {len(assertiveness.unanswered_questions)} perguntas sem resposta e "
        f"{len(assertiveness.deflected_questions)} perguntas com deflexão. "
        f"{_summarize_deductions(deductions)}"
    )
    return CriterionScore(
        criterion_id="C2",
        criterion_name=criterion["name"],
        score=_clamp(score),
        justification=justification,
        evidences=evidences,
        deductions=deductions,
    )


def _score_c3(facts: ExtractedFacts, criterion: dict) -> CriterionScore:
    score = 100.0
    deductions: list[str] = []
    flow = facts.flow
    evidences = [
        f"duplicate_bot_messages: {flow.duplicate_bot_messages}",
        f"context_lost_moments: {flow.context_lost_moments}",
        f"wrong_course_assumed: {flow.wrong_course_assumed}",
        f"non_text_input_handled: {flow.non_text_input_handled}",
        f"flow_progression: {flow.flow_progression}",
    ]
    for _ in flow.duplicate_bot_messages:
        score -= 20
        deductions.append("mensagem duplicada: -20pts")
    for _ in flow.context_lost_moments:
        score -= 22
        deductions.append("perda de contexto: -22pts")
    if flow.wrong_course_assumed:
        score -= 25
        deductions.append("curso assumido antes de confirmação: -25pts")
    if flow.non_text_input_received and flow.non_text_input_handled is False:
        score -= 12
        deductions.append("input não textual não tratado: -12pts")
    if not flow.flow_progression:
        score -= 30
        deductions.append("conversa sem progressão clara: -30pts")
    justification = (
        "O fluxo foi avaliado pela progressão da conversa e pela preservação de contexto. "
        f"A conversa passou por {len(flow.flow_progression)} etapas e registrou "
        f"{len(deductions)} deduções relevantes de fluxo. "
        f"{_summarize_deductions(deductions)}"
    )
    return CriterionScore(
        criterion_id="C3",
        criterion_name=criterion["name"],
        score=_clamp(score),
        justification=justification,
        evidences=evidences,
        deductions=deductions,
    )


def _score_c4(facts: ExtractedFacts, criterion: dict) -> CriterionScore:
    score = 100.0
    deductions: list[str] = []
    compliance = facts.compliance
    evidences = [
        f"bot_greeted_lead_as: {compliance.bot_greeted_lead_as}",
        f"name_mismatch: {compliance.name_mismatch}",
        f"price_revealed_directly: {compliance.price_revealed_directly}",
        f"invented_information: {compliance.invented_information}",
        f"honest_when_uninformed: {compliance.honest_when_uninformed}",
    ]
    if compliance.name_mismatch:
        score -= 30
        deductions.append("nome errado do lead: -30pts")
    if compliance.price_revealed_directly:
        score -= 45
        deductions.append("preço revelado diretamente: -45pts")
    for _ in compliance.invented_information:
        score -= 25
        deductions.append("informação inventada/sem base: -25pts")
    if compliance.price_asked_by_lead and not compliance.price_revealed_directly and not compliance.escalation_triggered:
        score -= 35
        deductions.append("não escalou quando devia: -35pts")
    justification = (
        "O critério verifica aderência às políticas comerciais e de personalização. "
        f"Foram observadas {len(compliance.invented_information)} informações possivelmente inventadas "
        f"e name_mismatch={compliance.name_mismatch}. "
        f"{_summarize_deductions(deductions)}"
    )
    return CriterionScore(
        criterion_id="C4",
        criterion_name=criterion["name"],
        score=_clamp(score),
        justification=justification,
        evidences=evidences,
        deductions=deductions,
    )


def _score_c5(facts: ExtractedFacts, criterion: dict) -> CriterionScore:
    resolution = facts.resolution
    evidences = [
        f"resolution_status: {resolution.resolution_status}",
        f"material_sent: {resolution.material_sent}",
        f"cta_present: {resolution.cta_present}",
        f"last_message_sender: {resolution.last_message_sender}",
    ]
    deductions: list[str] = []
    resolution_scores = {
        "escalated": 90.0,
        "material_sent": 78.0 if resolution.cta_present else 68.0,
        "resolved_in_chat": 82.0,
        "pending": 42.0,
        "dropped": 20.0,
    }
    score = resolution_scores[resolution.resolution_status]
    if resolution.resolution_status == "pending":
        if resolution.material_sent and resolution.cta_present:
            score = 62.0
        elif resolution.material_sent or resolution.cta_present:
            score = 52.0
    if resolution.resolution_status == "pending":
        if resolution.material_sent and resolution.cta_present:
            deductions.append("status pending com material enviado e CTA presente: faixa 60-69")
        elif resolution.material_sent or resolution.cta_present:
            deductions.append("status pending com encaminhamento parcial: faixa 50-69")
        else:
            deductions.append("conversa sem resolução clara: -58pts")
    if resolution.resolution_status == "dropped":
        deductions.append("sessão encerrada abruptamente: -80pts")
    justification = (
        "O desfecho foi avaliado pelo encaminhamento final, envio de material e presença de CTA. "
        f"O status final identificado foi '{resolution.resolution_status}'. "
        f"{_summarize_deductions(deductions)}"
    )
    return CriterionScore(
        criterion_id="C5",
        criterion_name=criterion["name"],
        score=_clamp(score),
        justification=justification,
        evidences=evidences,
        deductions=deductions,
    )


def heuristic_evaluate(criterion: dict, facts: ExtractedFacts) -> CriterionScore:
    handlers = {
        "C1": _score_c1,
        "C2": _score_c2,
        "C3": _score_c3,
        "C4": _score_c4,
        "C5": _score_c5,
    }
    return handlers[criterion["id"]](facts, criterion)


def run_evaluator(state: dict) -> dict:
    criterion = state["criterion"]
    facts = state["extracted_facts"]
    session_id = facts.metadata.session_id
    logger.info("[%s] Avaliando critério %s", session_id, criterion["id"])
    logger.debug("[%s] Critério %s via regra determinística", session_id, criterion["id"])
    score = heuristic_evaluate(criterion, facts)
    logger.info("[%s] Critério %s concluído com score %.1f", session_id, criterion["id"], score.score)
    logger.debug("[%s] Critério %s detalhes: %s", session_id, criterion["id"], score.model_dump(mode="json"))
    return {"criterion_scores": [score]}
