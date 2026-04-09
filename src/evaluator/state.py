from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from evaluator.schemas import CriterionScore, EvaluationReport, ExtractedFacts


class GraphState(TypedDict, total=False):
    conversation: str
    session_id: str
    extracted_facts: ExtractedFacts
    criterion_scores: Annotated[list[CriterionScore], operator.add]
    report: EvaluationReport
