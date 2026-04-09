from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from evaluator.schemas import CriterionScore, EvaluationReport, ExtractedFacts, SafetyAnalysis


class GraphState(TypedDict, total=False):
    conversation: str
    original_conversation: str
    session_id: str
    security: SafetyAnalysis
    extracted_facts: ExtractedFacts
    criterion_scores: Annotated[list[CriterionScore], operator.add]
    report: EvaluationReport
