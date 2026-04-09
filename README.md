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

## Exemplo completo

Exemplo real de requisicao enviada ao endpoint `POST /evaluate`:

```json
{
  "messages": [
    "human: Eu sou Pessoa_002",
    "ai: Olá, Pessoa_002! Eu sou a Beatriz, consultora de carreira da +A Code Academy. Vi que você tem interesse em uma pós-graduação. Você já tem algum curso em mente ou gostaria de ajuda para escolher?",
    "human: Dentro de Ed inclusiva",
    "ai: Entendi seu interesse em abordar temas de educação inclusiva. Temos uma pós em \"TEA, TDAH e Inclusão: Saúde, Família e Sociedade\", que pode ser relevante para esse campo.\nPosso te perguntar qual sua área de formação ou atuação para entender como essa especialização pode ajudar nos seus objetivos?",
    "human: Reposta da mensagem:  Entendi seu interesse em abordar temas de educação inclusiva. Temos uma pós em \"TEA, TDAH e Inclusão: Saúde, Família e Sociedade\", que pode ser relevante para esse campo. Resposta:  Sim",
    "human: Sou diretora escolar",
    "ai: Só para confirmar, quando você respondeu 'sim', está dizendo que já atua ou tem formação na área de educação inclusiva? Assim consigo te direcionar melhor.",
    "human: Pedagogia \nPós em educação brasileira \nMBA em gestão escolar",
    "ai: Ótimo saber que você é diretora escolar! Muitos profissionais de gestão na educação buscam essa especialização para promover práticas mais inclusivas nas escolas.\nTem algum desafio específico ou objetivo que te motivou a buscar o curso de TEA, TDAH e Inclusão?",
    "human: Reposta da mensagem:  Só para confirmar, quando você respondeu 'sim', está dizendo que já atua ou tem formação na área de educação inclusiva? Assim consigo te direcionar melhor. Resposta:  Não . Sim para o interesse nesse curso",
    "ai: Sua formação é uma base sólida para liderar ações de inclusão escolar. A pós em TEA, TDAH e Inclusão: Saúde, Família e Sociedade aprofunda o olhar sobre políticas inclusivas, a integração de talentos neurodiversos, e prepara gestores para construir estratégias efetivas junto a equipes e famílias.\nVeja o vídeo de apresentação e acesse o material completo do curso nos links abaixo:\nSe quiser, posso te orientar para os próximos passos e os detalhes da matrícula. Posso prosseguir com seu cadastro ou prefere tirar alguma dúvida pontual sobre o programa?",
    "ai: Ótimo, já entendi que seu interesse é direcionado ao curso TEA, TDAH e Inclusão: Saúde, Família e Sociedade. Essa pós-graduação trabalha temas como neurodesenvolvimento, políticas públicas de inclusão, estratégias para integração de alunos neurodivergentes e o papel da família e da escola, sempre priorizando a construção de uma cultura inclusiva na gestão escolar.\nVocê pode conhecer detalhes da estrutura e forma de aplicação do curso neste vídeo de apresentação.\nE conferir a grade curricular e informações em PDF.\nSe quiser seguir para inscrição ou tirar dúvidas pontuais sobre valor, prazo ou formas de ingresso, me avise que já te passo as próximas orientações.",
    "human: Estou no trânsito agora . Chegando no trabalho vejo o vídeo e te chamo aqui",
    "ai: Perfeito, fique à vontade para assistir ao vídeo quando conseguir! Assim que estiver pronta, é só me chamar aqui para conversarmos sobre dúvidas ou sobre o processo de matrícula. Deixo aberto para avançarmos juntos quando for o melhor momento para você."
  ],
  "sessionId": "S_cb815acbt33"
}
```

Resposta completa observada:

```json
{
  "success": true,
  "data": {
    "session_id": "S_cb815acbt33",
    "evaluated_at": "2026-04-09T18:14:59Z",
    "score_final": 90.5,
    "classification": "excelente",
    "executive_summary": "O atendimento alcançou score de 90,5 pontos com classificação excelente. Os principais pontos fortes foram a assertividade perfeita na resposta às dúvidas do lead, total conformidade com regras de negócio e qualificação bem estruturada com 4 perguntas relevantes que mapearam corretamente o perfil de uma diretora escolar buscando especialização em TEA, TDAH e inclusão. Como pontos de atenção, o bot fez uma suposição sem confirmação sobre a aplicação profissional do conhecimento e enviou duas mensagens duplicadas consecutivas, impactando levemente o fluxo da conversa. O atendimento permanece em status pendente com material enviado e call-to-action presente, aguardando o retorno do lead após assistir ao vídeo apresentado.",
    "scores": {
      "C1": {
        "criterion_id": "C1",
        "criterion_name": "Identificação e compreensão da necessidade",
        "score": 85,
        "justification": "O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. O bot fez 4 perguntas de qualificação, registrou 1 suposições sem confirmação e lead_objective='Aprofundar conhecimento em TEA, TDAH e inclusão para promover práticas inclusivas nas escolas'. Deduções aplicadas: info assumida sem confirmação: -15pts.",
        "evidences": [
          "lead_area_of_interest: Educação inclusiva",
          "lead_background: Diretora escolar. Formação: Pedagogia, Pós em educação brasileira, MBA em gestão escolar",
          "lead_objective: Aprofundar conhecimento em TEA, TDAH e inclusão para promover práticas inclusivas nas escolas",
          "qualification_questions_asked: ['Você já tem algum curso em mente ou gostaria de ajuda para escolher?', 'Posso te perguntar qual sua área de formação ou atuação para entender como essa especialização pode ajudar nos seus objetivos?', \"Só para confirmar, quando você respondeu 'sim', está dizendo que já atua ou tem formação na área de educação inclusiva?\", 'Tem algum desafio específico ou objetivo que te motivou a buscar o curso de TEA, TDAH e Inclusão?']",
          "repeated_qualification_questions: []",
          "info_assumed_without_confirmation: ['Bot assumiu que o lead buscava especialização em educação inclusiva sem confirmar se era para aplicação profissional ou pessoal']",
          "context_lost_moments: []"
        ],
        "deductions": [
          "info assumida sem confirmação: -15pts"
        ]
      },
      "C2": {
        "criterion_id": "C2",
        "criterion_name": "Assertividade da resposta",
        "score": 100,
        "justification": "O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 0 perguntas sem resposta e 0 perguntas com deflexão. Não houve deduções aplicadas neste critério.",
        "evidences": [
          "lead_questions_asked: []",
          "unanswered_questions: []",
          "deflected_questions: []",
          "course_correctly_identified: True"
        ],
        "deductions": []
      },
      "C3": {
        "criterion_id": "C3",
        "criterion_name": "Condução e fluxo da conversa",
        "score": 85,
        "justification": "O fluxo foi avaliado pela progressão da conversa e pela preservação de contexto. A conversa passou por 11 etapas e registrou 1 deduções relevantes de fluxo. Deduções aplicadas: mensagem duplicada: -15pts.",
        "evidences": [
          "duplicate_bot_messages: ['Bot enviou duas mensagens consecutivas sobre o curso TEA, TDAH e Inclusão sem mensagem do lead entre elas (mensagens 5 e 6)']",
          "context_lost_moments: []",
          "wrong_course_assumed: False",
          "non_text_input_handled: None",
          "flow_progression: ['Saudação e identificação do interesse geral em pós-graduação', 'Lead menciona interesse em educação inclusiva', 'Bot apresenta curso específico: TEA, TDAH e Inclusão', 'Bot qualifica formação e atuação do lead', 'Lead confirma formação: Pedagogia, Pós em educação brasileira, MBA em gestão escolar', 'Bot qualifica objetivo específico do lead', 'Bot apresenta material do curso (vídeo e PDF)', 'Bot oferece próximos passos (cadastro ou dúvidas)', 'Bot reforça apresentação do curso com detalhes adicionais', 'Lead informa que está em trânsito e assistirá ao vídeo depois', 'Bot confirma disponibilidade para continuar quando o lead retornar']"
        ],
        "deductions": [
          "mensagem duplicada: -15pts"
        ]
      },
      "C4": {
        "criterion_id": "C4",
        "criterion_name": "Conformidade com regras de negócio",
        "score": 100,
        "justification": "O critério verifica aderência às políticas comerciais e de personalização. Foram observadas 0 informações possivelmente inventadas e name_mismatch=False. Não houve deduções aplicadas neste critério.",
        "evidences": [
          "bot_greeted_lead_as: Pessoa_006",
          "name_mismatch: False",
          "price_revealed_directly: False",
          "invented_information: []",
          "honest_when_uninformed: None"
        ],
        "deductions": []
      },
      "C5": {
        "criterion_id": "C5",
        "criterion_name": "Desfecho e encaminhamento",
        "score": 72,
        "justification": "O desfecho foi avaliado pelo encaminhamento final, envio de material e presença de CTA. O status final identificado foi 'pending'. Deduções aplicadas: status pending com material enviado e CTA presente: faixa 70-79.",
        "evidences": [
          "resolution_status: pending",
          "material_sent: True",
          "cta_present: True",
          "last_message_sender: bot"
        ],
        "deductions": [
          "status pending com material enviado e CTA presente: faixa 70-79"
        ]
      }
    },
    "extracted_facts": {
      "metadata": {
        "session_id": "Pessoa_002",
        "total_turns": 12,
        "lead_turn_count": 6,
        "bot_turn_count": 6
      },
      "lead_profile": {
        "lead_name_informed": "Pessoa_002",
        "lead_area_of_interest": "Educação inclusiva",
        "lead_background": "Diretora escolar. Formação: Pedagogia, Pós em educação brasileira, MBA em gestão escolar",
        "lead_objective": "Aprofundar conhecimento em TEA, TDAH e inclusão para promover práticas inclusivas nas escolas",
        "lead_already_works_in_area": true
      },
      "qualification": {
        "qualification_questions_asked": [
          "Você já tem algum curso em mente ou gostaria de ajuda para escolher?",
          "Posso te perguntar qual sua área de formação ou atuação para entender como essa especialização pode ajudar nos seus objetivos?",
          "Só para confirmar, quando você respondeu 'sim', está dizendo que já atua ou tem formação na área de educação inclusiva?",
          "Tem algum desafio específico ou objetivo que te motivou a buscar o curso de TEA, TDAH e Inclusão?"
        ],
        "repeated_qualification_questions": [],
        "info_assumed_without_confirmation": [
          "Bot assumiu que o lead buscava especialização em educação inclusiva sem confirmar se era para aplicação profissional ou pessoal"
        ]
      },
      "assertiveness": {
        "lead_questions_asked": [],
        "unanswered_questions": [],
        "deflected_questions": [],
        "course_correctly_identified": true,
        "course_presented": [
          "TEA, TDAH e Inclusão: Saúde, Família e Sociedade"
        ],
        "course_not_found": false
      },
      "flow": {
        "duplicate_bot_messages": [
          "Bot enviou duas mensagens consecutivas sobre o curso TEA, TDAH e Inclusão sem mensagem do lead entre elas (mensagens 5 e 6)"
        ],
        "context_lost_moments": [],
        "wrong_course_assumed": false,
        "wrong_course_assumed_evidence": null,
        "non_text_input_received": false,
        "non_text_input_handled": null,
        "flow_progression": [
          "Saudação e identificação do interesse geral em pós-graduação",
          "Lead menciona interesse em educação inclusiva",
          "Bot apresenta curso específico: TEA, TDAH e Inclusão",
          "Bot qualifica formação e atuação do lead",
          "Lead confirma formação: Pedagogia, Pós em educação brasileira, MBA em gestão escolar",
          "Bot qualifica objetivo específico do lead",
          "Bot apresenta material do curso (vídeo e PDF)",
          "Bot oferece próximos passos (cadastro ou dúvidas)",
          "Bot reforça apresentação do curso com detalhes adicionais",
          "Lead informa que está em trânsito e assistirá ao vídeo depois",
          "Bot confirma disponibilidade para continuar quando o lead retornar"
        ]
      },
      "compliance": {
        "bot_greeted_lead_as": "Pessoa_002",
        "name_mismatch": false,
        "price_asked_by_lead": false,
        "price_revealed_directly": false,
        "escalation_triggered": false,
        "escalation_trigger_reason": null,
        "invented_information": [],
        "honest_when_uninformed": null
      },
      "resolution": {
        "resolution_status": "material_sent",
        "material_sent": true,
        "cta_present": true,
        "last_message_sender": "bot",
        "lead_last_message": "Sim, quero saber mais",
        "bot_last_message": "Ficou com alguma dúvida ou gostaria de saber detalhes específicos do curso? Me avise para eu te ajudar nas próximas etapas!"
      }
    },
    "strengths": [
      "C2 com score 100.0: O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 0 perguntas sem resposta e 0 perguntas com deflexão. Não houve deduções aplicadas neste critério.",
      "C4 com score 100.0: O critério verifica aderência às políticas comerciais e de personalização. Foram observadas 0 informações possivelmente inventadas e name_mismatch=False. Não houve deduções aplicadas neste critério.",
      "C1 com score 85.0: O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. O bot fez 4 perguntas de qualificação, registrou 1 suposições sem confirmação e lead_objective='Aprofundar conhecimento em TEA, TDAH e inclusão para promover práticas inclusivas nas escolas'. Deduções aplicadas: info assumida sem confirmação: -15pts."
    ],
    "improvement_areas": [
      "C5: corrigir status pending com material enviado e CTA presente: faixa 70-79",
      "C1: corrigir info assumida sem confirmação: -15pts",
      "C3: corrigir mensagem duplicada: -15pts"
    ]
  }
}
```

## Testes

```bash
pytest tests/ -v
```

## Docker

Build da imagem:

```bash
docker build -t conversation-quality-evaluator .
```

Subida da API:

```bash
docker run --rm -p 8000:8000 --env-file .env conversation-quality-evaluator
```

Se quiser subir sem arquivo `.env`, passe as variaveis necessarias com `-e`, por exemplo `BEDROCK_MODEL_ID`, `AWS_REGION`, `MODEL_PROVIDER`, `MODEL_TEMPERATURE`, `DB_PATH` e `LOG_LEVEL`.
