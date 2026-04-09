from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

import json

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadProfile(BaseModel):
    lead_name_informed: str = ""
    lead_area_of_interest: str = ""
    lead_background: Optional[str] = None
    lead_objective: Optional[str] = None
    lead_already_works_in_area: Optional[bool] = None


class QualificationAnalysis(BaseModel):
    qualification_questions_asked: list[str] = Field(default_factory=list)
    repeated_qualification_questions: list[str] = Field(default_factory=list)
    info_assumed_without_confirmation: list[str] = Field(default_factory=list)


class AssertivenessAnalysis(BaseModel):
    lead_questions_asked: list[str] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)
    deflected_questions: list[str] = Field(default_factory=list)
    course_correctly_identified: Optional[bool] = None
    course_presented: list[str] = Field(default_factory=list)
    course_not_found: bool = False


class FlowAnalysis(BaseModel):
    duplicate_bot_messages: list[str] = Field(default_factory=list)
    context_lost_moments: list[str] = Field(default_factory=list)
    wrong_course_assumed: bool = False
    wrong_course_assumed_evidence: Optional[str] = None
    non_text_input_received: bool = False
    non_text_input_handled: Optional[bool] = None
    flow_progression: list[str] = Field(default_factory=list)


class ComplianceAnalysis(BaseModel):
    bot_greeted_lead_as: str = ""
    name_mismatch: bool = False
    price_asked_by_lead: bool = False
    price_revealed_directly: bool = False
    escalation_triggered: bool = False
    escalation_trigger_reason: Optional[str] = None
    invented_information: list[str] = Field(default_factory=list)
    honest_when_uninformed: Optional[bool] = None


class ResolutionAnalysis(BaseModel):
    resolution_status: Literal["escalated", "material_sent", "resolved_in_chat", "dropped", "pending"] = "pending"
    material_sent: bool = False
    cta_present: bool = False
    last_message_sender: Literal["bot", "lead"] = "lead"
    lead_last_message: str = ""
    bot_last_message: str = ""


class SafetyAnalysis(BaseModel):
    prompt_injection_detected: bool = False
    prompt_injection_signals: list[str] = Field(default_factory=list)
    sensitive_data_redacted: bool = False
    redacted_entities: list[str] = Field(default_factory=list)
    redaction_count: int = 0
    conversation_sanitized: bool = False


class ConversationMetadata(BaseModel):
    session_id: str
    total_turns: int
    lead_turn_count: int
    bot_turn_count: int


class ExtractedFacts(BaseModel):
    metadata: ConversationMetadata
    lead_profile: LeadProfile
    qualification: QualificationAnalysis
    assertiveness: AssertivenessAnalysis
    flow: FlowAnalysis
    compliance: ComplianceAnalysis
    resolution: ResolutionAnalysis
    security: SafetyAnalysis = Field(default_factory=SafetyAnalysis)


class CriterionScore(BaseModel):
    criterion_id: Literal["C1", "C2", "C3", "C4", "C5"]
    criterion_name: str
    score: float = Field(ge=0.0, le=100.0)
    justification: str
    evidences: list[str] | None = Field(default_factory=list)
    deductions: list[str] | None = Field(default_factory=list)

    @field_validator("evidences", "deductions", mode="before")
    @classmethod
    def coerce_list_fields(cls, value):
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            if stripped.startswith("[") and stripped.endswith("]"):
                inner = stripped[1:-1].strip()
                if not inner:
                    return []
                return [part.strip().strip('"').strip("'") for part in inner.split(",") if part.strip()]
            return [stripped]
        return value


Classification = Literal["critico", "atencao", "regular", "bom", "excelente"]


class EvaluationReport(BaseModel):
    session_id: str
    evaluated_at: str
    score_final: float = Field(ge=0.0, le=100.0)
    classification: Classification
    executive_summary: str = ""
    scores: dict[str, CriterionScore]
    extracted_facts: ExtractedFacts | None = None
    strengths: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)

    @field_validator("evaluated_at")
    @classmethod
    def validate_iso_date(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    def to_executive_view(self) -> "EvaluationReport":
        compact_scores = {
            criterion_id: score.model_copy(update={"evidences": None, "deductions": None})
            for criterion_id, score in self.scores.items()
        }
        return self.model_copy(update={"scores": compact_scores, "extracted_facts": None})


class EvaluationRequest(BaseModel):
    """Body do POST /evaluate."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "sessionId": "S_cb815acb",
                "messages": [
                            "human: Eu sou Pessoa_001",
                            "ai: Olá, Pessoa_001, eu sou a Beatriz, consultora de carreira da +A Code Academy. Vi que você tem interesse em uma pós-graduação. Me conta: você já tem um curso em mente?",
                            "human: Transição energética",
                            "ai: Ótima escolha! Esse tema está em destaque devido às mudanças globais na área de energia. Para entender como essa pós pode trazer resultados reais para sua carreira: você já atua no setor de energia, ou está pensando em migrar para essa área?",
                            "human: Atuo",
                            "ai: Ótimo, isso torna sua experiência ainda mais relevante para o curso. Qual é o principal objetivo que você busca ao se especializar em Transição Energética? Por exemplo, desenvolver competências específicas, crescer na empresa ou explorar novas áreas do setor.",
                            "human: Autodesenvolvimento",
                            "ai: Entendi, investir no autodesenvolvimento é fundamental para se destacar profissionalmente. Pensando nisso, o que você espera conquistar ou mudar em sua trajetória ao se especializar nessa área?"
                            ],
            }
        },
    )

    session_id: str = Field(
        min_length=1,
        alias="sessionId",
        description="Identificador único da sessão",
    )
    messages: list[str] = Field(
        min_length=2,
        description="Lista de mensagens em ordem cronológica",
    )

    @field_validator("messages")
    @classmethod
    def must_have_both_roles(cls, value: list[str]) -> list[str]:
        roles: set[str] = set()
        for message in value:
            if ":" not in message:
                raise ValueError("Cada mensagem deve seguir o formato 'human: ...' ou 'ai: ...'")
            role, content = message.split(":", 1)
            role = role.strip().lower()
            if role not in {"human", "ai"}:
                raise ValueError("Cada mensagem deve começar com 'human:' ou 'ai:'")
            if not content.strip():
                raise ValueError("Cada mensagem deve conter conteúdo após o papel")
            roles.add(role)
        if "human" not in roles or "ai" not in roles:
            raise ValueError("A conversa deve conter mensagens de 'human' e 'ai'")
        return value

    def to_conversation_text(self) -> str:
        return "\n".join(message.strip() for message in self.messages)


class EvaluationResponse(BaseModel):
    """Envelope de resposta bem-sucedida."""

    success: bool = True
    data: EvaluationReport


class ErrorDetail(BaseModel):
    """Envelope de resposta de erro."""

    success: bool = False
    error: str
    detail: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
