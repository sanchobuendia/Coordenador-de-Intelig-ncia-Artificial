# Conversation Quality Evaluator

Protótipo para avaliação auditável da qualidade de atendimentos em canais digitais. O MVP adota uma arquitetura híbrida: extração estruturada com LLM e scoring determinístico por rubrica, orquestrados em um grafo LangGraph.

## Entrega do desafio

- Documento de solução: `SOLUTION.md`
- Registro de uso de IA: `AI_USAGE.md`
- Protótipo funcional: API FastAPI + pipeline em `src/evaluator`

## Arquitetura do MVP

```text
INPUT (conversa)
  -> EXTRATOR LLM
  -> 5 AVALIADORES DETERMINISTICOS (C1..C5)
  -> SINTETIZADOR DETERMINISTICO
  -> EvaluationReport
```

Os avaliadores trabalham sobre fatos estruturados, não sobre a conversa bruta. Isso reduz variabilidade, facilita auditoria e desacopla a evolução dos critérios da etapa de interpretação textual.

Critérios e pesos:

- `C1` Identificação e compreensão da necessidade: `25%`
- `C2` Assertividade da resposta: `25%`
- `C3` Condução e fluxo da conversa: `20%`
- `C4` Conformidade com regras de negócio: `20%`
- `C5` Desfecho e encaminhamento: `10%`

## Configuração

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

Variáveis de ambiente:

- `MODEL_PROVIDER`: provider do `init_chat_model` do LangChain. Padrão: `bedrock_converse`
- `BEDROCK_MODEL_ID`: identificador do modelo usado no extrator
- `MODEL_TEMPERATURE`: temperatura do modelo. Padrão: `0.2`
- `AWS_REGION`: região AWS quando usar Bedrock
- `DB_PATH`: string de conexão Postgres para checkpoints do LangGraph
- `LOG_LEVEL`: nível de log da API

Observação: sem `BEDROCK_MODEL_ID`, o extrator LLM não roda. Os avaliadores e o sintetizador são determinísticos.

## Como rodar a API

```bash
uvicorn api.main:app --reload
```

Se você não tiver instalado o projeto com `pip install -e .[dev]`, rode com `PYTHONPATH=src`:

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

Endpoints:

- `GET /health`
- `POST /evaluate`

Exemplo de payload:

```json
{
  "sessionId": "S_84b564f9",
  "messages": [
    "human: Eu sou Pessoa_015",
    "ai: Olá, Karina! Ótimo saber que você atua em Saúde Corporativa."
  ]
}
```

## Como rodar uma avaliação em código

```python
from evaluator.graph import graph

result = graph.invoke(
    {
        "session_id": "minha-sessao",
        "conversation": "human: Olá\nai: Olá! Como posso ajudar?",
    }
)

print(result["report"].model_dump_json(indent=2))
```

## Testes

```bash
pytest tests/ -v
```
