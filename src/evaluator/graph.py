from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager

from langgraph.constants import Send
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from evaluator.config import get_settings
from evaluator.nodes.evaluators import CRITERIA, run_evaluator
from evaluator.nodes.extractor import run_extractor
from evaluator.nodes.synthesizer import run_synthesizer
from evaluator.state import GraphState

ALLOWED_MSGPACK_MODULES = [
    ("evaluator.schemas", "EvaluationReport"),
    ("evaluator.schemas", "ExtractedFacts"),
    ("evaluator.schemas", "CriterionScore"),
]


def route_to_evaluators(state: GraphState) -> list[Send]:
    return [
        Send("evaluator", {"criterion": criterion, "extracted_facts": state["extracted_facts"]})
        for criterion in CRITERIA
    ]


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)
    builder.add_node("extractor", run_extractor)
    builder.add_node("evaluator", run_evaluator)
    builder.add_node("synthesizer", run_synthesizer)
    builder.set_entry_point("extractor")
    builder.add_conditional_edges("extractor", route_to_evaluators, ["evaluator"])
    builder.add_edge("evaluator", "synthesizer")
    builder.add_edge("synthesizer", END)
    return builder


def compile_graph(checkpointer=None):
    return build_graph().compile(checkpointer=checkpointer)


def build_checkpoint_serde() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK_MODULES)


@contextmanager
def persistent_graph():
    settings = get_settings()
    db_path = settings.DB_PATH.strip()
    if not db_path:
        yield compile_graph()
        return

    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(db_path, serde=build_checkpoint_serde()) as checkpointer:
        checkpointer.setup()
        yield compile_graph(checkpointer=checkpointer)


@asynccontextmanager
async def apersistent_graph():
    settings = get_settings()
    db_path = settings.DB_PATH.strip()
    if not db_path:
        yield compile_graph()
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(db_path, serde=build_checkpoint_serde()) as checkpointer:
        await checkpointer.setup()
        yield compile_graph(checkpointer=checkpointer)


graph = compile_graph()
