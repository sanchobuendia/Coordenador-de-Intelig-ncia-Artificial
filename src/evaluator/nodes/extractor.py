from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable

from dotenv import load_dotenv

from evaluator.config import build_chat_model_with_fallback
from evaluator.prompts import EXTRACTOR_PROMPT
from evaluator.schemas import (
    AssertivenessAnalysis,
    ComplianceAnalysis,
    ConversationMetadata,
    ExtractedFacts,
    FlowAnalysis,
    LeadProfile,
    QualificationAnalysis,
    ResolutionAnalysis,
)

load_dotenv()

logger = logging.getLogger("evaluator.extractor")

COURSE_KEYWORDS = {
    "saude mental": "Saúde Mental",
    "saúde mental": "Saúde Mental",
    "saude corporativa": "Saúde Corporativa",
    "saúde corporativa": "Saúde Corporativa",
    "gestao hospitalar": "Gestão Hospitalar",
    "gestão hospitalar": "Gestão Hospitalar",
    "engenharia de software": "Engenharia de Software",
    "ciencia de dados": "Ciência de Dados",
    "ciência de dados": "Ciência de Dados",
    "educacao inclusiva": "Educação Inclusiva",
    "educação inclusiva": "Educação Inclusiva",
    "tea": "TEA, TDAH e Inclusão: Saúde, Família e Sociedade",
    "tdah": "TEA, TDAH e Inclusão: Saúde, Família e Sociedade",
    "inclusao: saude, familia e sociedade": "TEA, TDAH e Inclusão: Saúde, Família e Sociedade",
    "inclusão: saúde, família e sociedade": "TEA, TDAH e Inclusão: Saúde, Família e Sociedade",
    "transicao energetica": "Transição Energética",
    "transição energética": "Transição Energética",
}

MATERIAL_TOKENS = [
    "material",
    "catálogo",
    "catalogo",
    "brochura",
    "pdf",
    "link",
    "links",
    "vídeo",
    "video",
]

CTA_TOKENS = [
    "quer",
    "posso te encaminhar",
    "vamos seguir",
    "vamos agendar",
    "posso prosseguir",
    "próximos passos",
    "proximos passos",
    "me avise",
    "tirar alguma dúvida",
    "tirar alguma duvida",
    "processo de matrícula",
    "processo de matricula",
]


@dataclass
class Turn:
    role: str
    content: str


def parse_conversation(conversation: str) -> list[Turn]:
    turns: list[Turn] = []
    for raw_line in conversation.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        role, content = line.split(":", 1)
        role = role.strip().lower()
        if role not in {"human", "ai"}:
            continue
        turns.append(Turn(role=role, content=content.strip()))
    return turns


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def unique_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def detect_name(text: str) -> str | None:
    patterns = [
        r"\beu sou ([\w_À-ÿ-]+)",
        r"\bme chamo ([\w_À-ÿ-]+)",
        r"\bmeu nome é ([\w_À-ÿ-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,!?")
    return None


def detect_greeting_name(text: str) -> str:
    match = re.search(r"\bol[aá],?\s+([\w_À-ÿ-]+)", text, re.IGNORECASE)
    return match.group(1).strip(" .,!?") if match else ""


def detect_area(text: str) -> str:
    lowered = normalize_text(text)
    for keyword, label in COURSE_KEYWORDS.items():
        if keyword in lowered:
            return label
    if "pós" in lowered or "pos" in lowered:
        return "Pós-graduação"
    return ""


def extract_course_mentions(text: str) -> list[str]:
    lowered = normalize_text(text)
    matches = [label for keyword, label in COURSE_KEYWORDS.items() if keyword in lowered]
    if not matches:
        quoted = re.findall(r'"([^"]+)"', text)
        matches.extend(item.strip() for item in quoted if item.strip())
    return unique_preserve(matches)


def extract_lead_interest(text: str) -> str:
    normalized = normalize_text(text)
    area = detect_area(text)
    if area:
        return area
    if normalized.startswith("dentro de "):
        return text.split(" ", 2)[-1].strip()
    return ""


def interests_are_compatible(lead_interest: str, course_name: str) -> bool:
    lead_normalized = normalize_text(lead_interest)
    course_normalized = normalize_text(course_name)
    if not lead_normalized or not course_normalized:
        return False
    if lead_normalized in course_normalized or course_normalized in lead_normalized:
        return True
    compatibility_pairs = [
        ("ed inclusiva", "inclus"),
        ("educacao inclusiva", "inclus"),
        ("educação inclusiva", "inclus"),
    ]
    return any(source in lead_normalized and target in course_normalized for source, target in compatibility_pairs)


def extract_lead_background(human_turns: list[Turn]) -> str | None:
    role: str | None = None
    formations: list[str] = []
    other_background: list[str] = []
    for turn in human_turns:
        content = turn.content.strip()
        normalized = normalize_text(content)
        if normalized.startswith("reposta da mensagem") or normalized.startswith("resposta da mensagem"):
            continue
        if any(token in normalized for token in ["trânsito", "transito", "te chamo", "vejo o vídeo", "vejo o video"]):
            continue
        if any(token in normalized for token in ["sou diretora", "sou diretor", "sou coordenadora", "sou coordenador", "sou gestora", "sou gestor"]):
            role = content
            continue
        if normalized in {"atuo", "trabalho na área", "trabalho na area"}:
            other_background.append(content)
            continue
        if "\n" in content or any(token in normalized for token in ["pedagogia", "mba", "graduação", "graduacao", "pós", " pos ", "formação", "formacao"]):
            parts = [part.strip(" .") for part in content.splitlines() if part.strip()]
            formations.extend(parts or [content])

    formations = unique_preserve(formations)
    other_background = unique_preserve(other_background)

    summary_parts: list[str] = []
    if role:
        summary_parts.append(role.rstrip("."))
    if formations:
        summary_parts.append(f"Formação: {', '.join(formations)}")
    if other_background:
        summary_parts.extend(item.rstrip(".") for item in other_background)
    return ". ".join(summary_parts) if summary_parts else None


def extract_lead_objective(human_turns: list[Turn]) -> str | None:
    objective_tokens = [
        "objetivo",
        "quero",
        "busco",
        "buscar",
        "pretendo",
        "migrar",
        "transição",
        "transicao",
        "crescer",
        "desenvolver",
        "desenvolvimento",
        "conquistar",
        "mudar",
        "especializar",
        "autodesenvolvimento",
    ]
    for turn in human_turns:
        normalized = normalize_text(turn.content)
        if any(token in normalized for token in objective_tokens):
            return turn.content.strip()
    return None


def compute_flow_progression(turns: list[Turn], escalation_triggered: bool = False) -> list[str]:
    steps: list[str] = []
    for turn in turns:
        content = normalize_text(turn.content)
        if turn.role == "ai" and ("olá" in content or "ola" in content):
            steps.append("saudação")
        if turn.role == "ai" and "?" in turn.content:
            steps.append("qualificação")
        if turn.role == "ai" and extract_course_mentions(turn.content):
            steps.append("apresentação_curso")
        if turn.role == "ai" and any(token in content for token in MATERIAL_TOKENS):
            steps.append("envio_material")
        if turn.role == "ai" and escalation_triggered and any(token in content for token in ["encaminhar", "transferir", "passar", "acionar"]):
            steps.append("escalada")
        if turn.role == "ai" and any(token in content for token in CTA_TOKENS):
            steps.append("cta")
        if turn.role == "ai" and any(token in content for token in ["fico à disposição", "fico a disposição", "até mais", "até breve"]):
            steps.append("encerramento")
    return unique_preserve(steps)


def heuristic_extract(state: dict) -> ExtractedFacts:
    session_id = state["session_id"]
    conversation = state["conversation"]
    turns = parse_conversation(conversation)
    human_turns = [turn for turn in turns if turn.role == "human"]
    ai_turns = [turn for turn in turns if turn.role == "ai"]

    lead_name = ""
    for turn in human_turns:
        maybe_name = detect_name(turn.content)
        if maybe_name:
            lead_name = maybe_name
            break

    lead_area = ""
    for turn in human_turns:
        lead_area = extract_lead_interest(turn.content)
        if lead_area:
            break
    lead_background = extract_lead_background(human_turns)
    lead_objective = extract_lead_objective(human_turns)

    qualification_questions = [turn.content for turn in ai_turns if "?" in turn.content]
    repeated_qualification: list[str] = []
    seen_questions: set[str] = set()
    for question in qualification_questions:
        normalized = normalize_text(question)
        if normalized in seen_questions:
            repeated_qualification.append(question)
        seen_questions.add(normalized)

    greeting_name = detect_greeting_name(ai_turns[0].content) if ai_turns else ""
    assumptions: list[str] = []
    if greeting_name and lead_name and normalize_text(greeting_name) != normalize_text(lead_name):
        assumptions.append(f"bot chamou lead de '{greeting_name}' sem o lead informar esse nome")

    invented_information: list[str] = []
    for turn in ai_turns:
        content = normalize_text(turn.content)
        if "você atua em" in content and not any("atuo em" in normalize_text(h.content) or "trabalho com" in normalize_text(h.content) for h in human_turns):
            invented_information.append(turn.content)

    lead_questions = [turn.content for turn in human_turns if "?" in turn.content]
    unanswered_questions: list[str] = []
    deflected_questions: list[str] = []
    course_presented = unique_preserve([label for turn in ai_turns for label in extract_course_mentions(turn.content)])

    for index, turn in enumerate(human_turns):
        if "?" not in turn.content:
            continue
        turn_position = turns.index(turn)
        next_ai = next((candidate for candidate in turns[turn_position + 1 :] if candidate.role == "ai"), None)
        if next_ai is None:
            unanswered_questions.append(turn.content)
            continue
        human_normalized = normalize_text(turn.content)
        ai_normalized = normalize_text(next_ai.content)
        if any(token in human_normalized for token in ["dia", "semana"]) and any(token in ai_normalized for token in ["19h", "20h", "horário", "horario"]) and "dia" not in ai_normalized and "semana" not in ai_normalized:
            deflected_questions.append(turn.content)
            continue
        if any(token in human_normalized for token in ["preço", "valor", "mensalidade"]) and not any(token in ai_normalized for token in ["especialista", "consultor", "posso encaminhar", "não posso informar"]):
            unanswered_questions.append(turn.content)

    wrong_course_assumed = False
    wrong_course_evidence = None
    human_area_mentions = unique_preserve(filter(None, (extract_lead_interest(turn.content) for turn in human_turns)))
    ai_area_mentions = unique_preserve(filter(None, (next(iter(extract_course_mentions(turn.content)), "") for turn in ai_turns)))
    if human_area_mentions and ai_area_mentions and not interests_are_compatible(human_area_mentions[0], ai_area_mentions[0]):
        wrong_course_assumed = True
        wrong_course_evidence = ai_turns[0].content if ai_turns else None
    elif not human_area_mentions and ai_area_mentions:
        wrong_course_assumed = True
        wrong_course_evidence = ai_turns[0].content if ai_turns else None

    duplicate_messages: list[str] = []
    seen_ai_messages: set[str] = set()
    for index, turn in enumerate(turns):
        if turn.role != "ai":
            continue
        normalized = normalize_text(turn.content)
        if normalized in seen_ai_messages:
            duplicate_messages.append(turn.content)
        seen_ai_messages.add(normalized)
        if index > 0 and turns[index - 1].role == "ai":
            duplicate_messages.append(turn.content)

    non_text_received = any("[imagem]" in normalize_text(turn.content) or "[audio]" in normalize_text(turn.content) for turn in human_turns)
    non_text_handled = None
    if non_text_received:
        non_text_handled = any("não consigo visualizar" in normalize_text(turn.content) or "descreva" in normalize_text(turn.content) for turn in ai_turns)

    price_asked = any(any(token in normalize_text(turn.content) for token in ["preço", "valor", "mensalidade"]) for turn in human_turns)
    price_revealed = any(any(token in normalize_text(turn.content) for token in ["r$", "reais", "mensalidade de", "valor é"]) for turn in ai_turns)
    escalation_turn = next(
        (
            turn
            for turn in ai_turns
            if any(token in normalize_text(turn.content) for token in ["especialista", "consultor", "time comercial", "atendente humano"])
            and any(token in normalize_text(turn.content) for token in ["encaminhar", "transferir", "passar", "acionar"])
        ),
        None,
    )
    honest_turn = next((turn for turn in ai_turns if any(token in normalize_text(turn.content) for token in ["não encontrei", "não localizei", "não tenho essa informação", "não consegui confirmar"])), None)

    lead_last_message = next((turn.content for turn in reversed(turns) if turn.role == "human"), "")
    bot_last_message = next((turn.content for turn in reversed(turns) if turn.role == "ai"), "")
    last_message_sender = turns[-1].role if turns else "lead"
    material_sent = any(any(token in normalize_text(turn.content) for token in MATERIAL_TOKENS) for turn in ai_turns)
    cta_present = any(any(token in normalize_text(turn.content) for token in CTA_TOKENS) for turn in ai_turns)
    lead_signaled_follow_up = any(
        any(token in normalize_text(turn.content) for token in ["te chamo", "volto aqui", "depois vejo", "quando conseguir", "falo depois"])
        for turn in human_turns
    )

    context_lost_moments: list[str] = []
    first_course_position = next((index for index, turn in enumerate(turns) if turn.role == "ai" and extract_course_mentions(turn.content)), None)
    first_background_position = next(
        (
            index
            for index, turn in enumerate(turns)
            if turn.role == "human"
            and any(token in normalize_text(turn.content) for token in ["atuo", "trabalho", "sou ", "formação", "pedagogia", "mba", "objetivo"])
        ),
        None,
    )
    if first_course_position is not None and first_background_position is not None and first_course_position < first_background_position:
        context_lost_moments.append("bot apresentou curso antes de concluir a qualificação do lead")

    if lead_signaled_follow_up:
        resolution_status = "pending"
    elif escalation_turn:
        resolution_status = "escalated"
    elif material_sent:
        resolution_status = "material_sent"
    elif last_message_sender == "ai" and cta_present:
        resolution_status = "resolved_in_chat"
    elif last_message_sender == "human":
        resolution_status = "pending"
    else:
        resolution_status = "dropped"

    extracted = ExtractedFacts(
        metadata=ConversationMetadata(
            session_id=session_id,
            total_turns=len(turns),
            lead_turn_count=len(human_turns),
            bot_turn_count=len(ai_turns),
        ),
        lead_profile=LeadProfile(
            lead_name_informed=lead_name,
            lead_area_of_interest=lead_area,
            lead_background=lead_background,
            lead_objective=lead_objective,
            lead_already_works_in_area=None,
        ),
        qualification=QualificationAnalysis(
            qualification_questions_asked=qualification_questions,
            repeated_qualification_questions=repeated_qualification,
            info_assumed_without_confirmation=assumptions,
        ),
        assertiveness=AssertivenessAnalysis(
            lead_questions_asked=lead_questions,
            unanswered_questions=unanswered_questions,
            deflected_questions=deflected_questions,
            course_correctly_identified=None if not ai_area_mentions else not wrong_course_assumed,
            course_presented=course_presented,
            course_not_found=not bool(course_presented),
        ),
        flow=FlowAnalysis(
            duplicate_bot_messages=duplicate_messages,
            context_lost_moments=context_lost_moments,
            wrong_course_assumed=wrong_course_assumed,
            wrong_course_assumed_evidence=wrong_course_evidence,
            non_text_input_received=non_text_received,
            non_text_input_handled=non_text_handled,
            flow_progression=compute_flow_progression(turns, escalation_triggered=escalation_turn is not None),
        ),
        compliance=ComplianceAnalysis(
            bot_greeted_lead_as=greeting_name,
            name_mismatch=bool(assumptions),
            price_asked_by_lead=price_asked,
            price_revealed_directly=price_revealed,
            escalation_triggered=escalation_turn is not None,
            escalation_trigger_reason=escalation_turn.content if escalation_turn else None,
            invented_information=unique_preserve(invented_information),
            honest_when_uninformed=True if honest_turn else None,
        ),
        resolution=ResolutionAnalysis(
            resolution_status=resolution_status,
            material_sent=material_sent,
            cta_present=cta_present,
            last_message_sender="bot" if last_message_sender == "ai" else "lead",
            lead_last_message=lead_last_message,
            bot_last_message=bot_last_message,
        ),
    )
    return extracted


def llm_extract(state: dict) -> ExtractedFacts:
    model = build_chat_model_with_fallback().with_structured_output(ExtractedFacts)
    schema = json.dumps(ExtractedFacts.model_json_schema(), ensure_ascii=False)
    prompt = EXTRACTOR_PROMPT.format(conversation=state["conversation"], schema=schema)
    return model.invoke(prompt)


def run_extractor(state: dict) -> dict:
    logger.info("[%s] Iniciando extração", state["session_id"])
    logger.debug("[%s] Extração via LLM", state["session_id"])
    extracted = llm_extract(state)
    logger.info("[%s] Extração concluída", state["session_id"])
    logger.debug("[%s] Fatos extraídos: %s", state["session_id"], extracted.model_dump(mode="json"))
    return {"extracted_facts": extracted}
