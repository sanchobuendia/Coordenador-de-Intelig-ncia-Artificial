from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from evaluator.config import get_settings
from evaluator.graph import apersistent_graph
from evaluator.schemas import ErrorDetail, EvaluationRequest, EvaluationResponse

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger("api")


def _display_value(value: str, max_length: int = 120) -> str:
    if not value:
        return "<not-set>"
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}..."


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with apersistent_graph() as compiled_graph:
        app.state.graph = compiled_graph
        logger.info("Serviço iniciado — grafo LangGraph compilado")
        logger.info(
            "Configuração do modelo: AWS_REGION=%s MODEL_PROVIDER=%s BEDROCK_MODEL_ID=%s MODEL_TEMPERATURE=%s",
            _display_value(settings.AWS_REGION),
            _display_value(settings.MODEL_PROVIDER),
            _display_value(settings.BEDROCK_MODEL_ID),
            settings.MODEL_TEMPERATURE,
        )
        logger.debug("Configuração ativa: LOG_LEVEL=%s", settings.LOG_LEVEL)
        yield
        logger.info("Serviço encerrado")


app = FastAPI(
    title="Conversation Quality Evaluator",
    description="Avalia a qualidade de atendimento em conversas chatbot-lead",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post(
    "/evaluate",
    response_model=EvaluationResponse,
    responses={
        422: {"model": ErrorDetail, "description": "Payload inválido"},
        500: {"model": ErrorDetail, "description": "Erro interno no pipeline"},
    },
    summary="Avalia a qualidade de uma conversa",
)
async def evaluate(payload: EvaluationRequest, request: Request) -> EvaluationResponse:
    start = time.perf_counter()
    logger.info("[%s] Avaliação iniciada — %s mensagens", payload.session_id, len(payload.messages))
    logger.debug("[%s] Payload normalizado: %s", payload.session_id, payload.to_conversation_text())
    try:
        result = await request.app.state.graph.ainvoke(
            {
                "session_id": payload.session_id,
                "conversation": payload.to_conversation_text(),
            },
            config={"configurable": {"thread_id": payload.session_id}},
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("[%s] Falha no pipeline", payload.session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = time.perf_counter() - start
    logger.info(
        "[%s] Concluído em %.1fs — score=%s classification=%s",
        payload.session_id,
        elapsed,
        result["report"].score_final,
        result["report"].classification,
    )
    logger.debug("[%s] Relatório final gerado com %s critérios", payload.session_id, len(result["report"].scores))
    return EvaluationResponse(data=result["report"])


@app.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info("Payload inválido recebido em %s", request.url.path)
    logger.debug("Detalhes da validação: %s", exc)
    return JSONResponse(
        status_code=422,
        content=ErrorDetail(error="Payload inválido", detail=str(exc)).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code != 500:
        raise exc
    logger.info("Erro interno ao processar %s", request.url.path)
    logger.debug("Detalhe do erro interno: %s", exc.detail)
    return JSONResponse(
        status_code=500,
        content=ErrorDetail(error="Erro interno no pipeline", detail=str(exc.detail)).model_dump(),
    )
