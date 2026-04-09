from __future__ import annotations

import logging
import re

from evaluator.schemas import SafetyAnalysis

logger = logging.getLogger("evaluator.guardrails")

PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore (all|any|the|previous)?\s*instructions",
        r"ignore as instru[cç][oõ]es",
        r"desconsidere (todas as )?instru[cç][oõ]es",
        r"ignore (the )?system prompt",
        r"revele (o )?prompt",
        r"show (me )?(the )?prompt",
        r"developer message",
        r"mensagem de desenvolvedor",
        r"voc[eê] agora [ée] ",
        r"aja como ",
        r"finja ser ",
        r"tool call",
        r"use a ferramenta",
    ]
]

CPF_PATTERN = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CPF_LABELED_PATTERN = re.compile(r"(\bcpf(?:\s*[ée:]\s*|\s+))(\d{11}\b)", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4})-?\d{4}|\d{10,11})(?!\d)"
)

NAME_PATTERNS = [
    re.compile(r"(\beu sou\s+)([\w_À-ÿ-]+)", re.IGNORECASE),
    re.compile(r"(\bme chamo\s+)([\w_À-ÿ-]+)", re.IGNORECASE),
    re.compile(r"(\bmeu nome [ée]\s+)([\w_À-ÿ-]+)", re.IGNORECASE),
    re.compile(r"(\bol[aá],?\s+)([\w_À-ÿ-]+)", re.IGNORECASE),
]


def _collect_prompt_injection_signals(text: str) -> list[str]:
    signals: list[str] = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        for match in pattern.finditer(text):
            signals.append(match.group(0))
    return list(dict.fromkeys(signal.strip() for signal in signals if signal.strip()))


def _mask_names(text: str) -> tuple[str, int]:
    replacements = 0
    aliases: dict[str, str] = {}
    masked = text
    for pattern in NAME_PATTERNS:
        def repl(match: re.Match[str]) -> str:
            nonlocal replacements
            original_name = match.group(2).strip()
            key = original_name.casefold()
            if key not in aliases:
                aliases[key] = f"[REDACTED_NAME_{len(aliases) + 1}]"
            replacements += 1
            return f"{match.group(1)}{aliases[key]}"

        masked = pattern.sub(repl, masked)
    return masked, replacements


def sanitize_conversation(conversation: str) -> tuple[str, SafetyAnalysis]:
    prompt_signals = _collect_prompt_injection_signals(conversation)
    redacted_entities: list[str] = []

    sanitized = conversation

    sanitized, name_replacements = _mask_names(sanitized)
    if name_replacements:
        redacted_entities.append("name")

    cpf_matches = CPF_PATTERN.findall(sanitized)
    cpf_labeled_matches = CPF_LABELED_PATTERN.findall(sanitized)
    if cpf_matches or cpf_labeled_matches:
        sanitized = CPF_PATTERN.sub("[REDACTED_CPF]", sanitized)
        sanitized = CPF_LABELED_PATTERN.sub(r"\1[REDACTED_CPF]", sanitized)
        redacted_entities.append("cpf")

    email_matches = EMAIL_PATTERN.findall(sanitized)
    if email_matches:
        sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)
        redacted_entities.append("email")

    phone_matches = PHONE_PATTERN.findall(sanitized)
    if phone_matches:
        sanitized = PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)
        redacted_entities.append("phone")

    if prompt_signals:
        for signal in prompt_signals:
            sanitized = re.sub(re.escape(signal), "[PROMPT_INJECTION_SIGNAL]", sanitized, flags=re.IGNORECASE)

    analysis = SafetyAnalysis(
        prompt_injection_detected=bool(prompt_signals),
        prompt_injection_signals=prompt_signals,
        sensitive_data_redacted=bool(redacted_entities),
        redacted_entities=list(dict.fromkeys(redacted_entities)),
        redaction_count=name_replacements + len(cpf_matches) + len(cpf_labeled_matches) + len(email_matches) + len(phone_matches),
        conversation_sanitized=sanitized != conversation,
    )
    return sanitized, analysis


def run_guardrails(state: dict) -> dict:
    session_id = state["session_id"]
    logger.info("[%s] Aplicando guardrails de segurança", session_id)
    sanitized_conversation, analysis = sanitize_conversation(state["conversation"])
    if analysis.prompt_injection_detected:
        logger.warning("[%s] Sinais de prompt injection detectados: %s", session_id, analysis.prompt_injection_signals)
    if analysis.sensitive_data_redacted:
        logger.info("[%s] Dados sensíveis mascarados: %s", session_id, ", ".join(analysis.redacted_entities))
    return {
        "original_conversation": state["conversation"],
        "conversation": sanitized_conversation,
        "security": analysis,
    }
