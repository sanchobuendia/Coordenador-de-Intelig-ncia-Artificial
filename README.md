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
    "human: Eu sou Pessoa_006",
    "ai: Olá, Pessoa_006, eu sou a Beatriz, consultora de carreira da +A Code Academy. Vi que você tem interesse em uma pós-graduação. Me conta: você já tem um curso em mente?",
    "human: Reposta da mensagem:  Olá! Ficamos muito felizes pelo seu interesse na Pós +A Code Academy Digital. 😊\n\nSou consultora de carreiras e estou aqui para garantir que esta experiência seja incrível desde o seu início.\n\nEstou à disposição para auxiliar com tudo que você precisa saber sobre a nossa pós-graduação, ok?\n\n*Para já iniciarmos, que tal você me falar qual é a sua formação acadêmica?* 🤔 Resposta:  Possuo graduação em Redes de Computadores e estou graduando em Defesa Cibernética",
    "ai: Entendi, você já tem uma base sólida em tecnologia e segurança da informação. Pensando na sua carreira, você busca uma especialização para crescer na área técnica mesmo ou pensa em migrar para funções de gestão e liderança?",
    "human: Reposta da mensagem:  Olá, Pessoa_006, eu sou a Beatriz, consultora de carreira da +A Code Academy. Vi que você tem interesse em uma pós-graduação. Me conta: você já tem um curso em mente? Resposta:  Me interesso por IA aplicada em Cybersecurity",
    "ai: Ótima escolha! O curso \"IA e Cibersegurança: Automação e Eficiência para Segurança Digital\" é voltado justamente para profissionais que querem aplicar Inteligência Artificial em defesa cibernética e automação de processos de segurança. Você verá conteúdos sobre antecipação de riscos, automação de defesas, detecção de vulnerabilidades e respostas estratégicas a ameaças digitais.\nVou te passar um diferencial exclusivo para você se matricular na nossa Escola de IA! Não é apenas um curso, você fará parte de um ecossistema vivo de aprendizagem:\n✔️ Comunidade ativa com trocas reais\n✔️ Desafios práticos para aplicar IA na prática\n✔️ Entrevistas com especialistas do mercado\n✔️ Atualizações frequentes sobre as transformações da IA\n✔️ Curadoria Exclusiva de Ferramentas de IA, Agentes, prompts e tutoriais para o seu dia a dia profissional\nDepois de conferir o material, posso te explicar como funciona a matrícula e as próximas etapas. Posso te ajudar agora mesmo a seguir com sua inscrição?",
    "human: Sim, quero saber mais",
    "ai: Aqui estão mais informações sobre o curso, conforme solicitado:\n\n✔️ 100% online –  sem encontros presenciais\n✔️ Duração de 10 meses, com acesso liberado por até 24 meses\n✔️ Carga horária total de 360h\n✔️ Estrutura com 12 disciplinas (5 aulas em cada disciplina + 1 avaliação online por módulo)\n✔️ Ao final, você realiza um Projeto de Aplicação prático de 72h, no lugar do TCC tradicional.\n🧑‍🏫 Cada disciplina terá:\n\n— 3 aulas gravadas, com professores que são referência de mercado, trazendo conteúdo direto ao ponto.\n— 2 aulas ao vivo, com especialistas da +A Code Academy — ótimas oportunidades pra tirar dúvidas, trocar experiências e até interagir com colegas da área.\n📌 E se não conseguir assistir ao vivo, tudo bem!\nAs aulas ficam gravadas pra você acessar quando e quantas vezes quiser, no seu ritmo.\n\nAs aulas ao vivo vão ocorrer as quartas-feiras, das 19h30 as 21h.\nVocê irá visualizar o Calendário Acadêmico na plataforma para verificar as datas das aulas ao vivo e se programar para assistir caso desejar.\n🎓 O certificado é com titularidade de especialista Lato Sensu reconhecido pelo MEC, emitido como presencial sem menções de digital, online ou EAD.\n\nAcesse a apresentação completa da pós pelo PDF: [Ver PDF do curso](https://lead-recovery-99[TELEFONE].s3.us-east-1.amazonaws.com/conteudo-rag/13873/PDF/IA%20e%20Ciberseguran%C3%A7a.pdf)\n\nFicou com alguma dúvida ou gostaria de saber detalhes específicos do curso? Me avise para eu te ajudar nas próximas etapas!"
  ],
  "sessionId": "S_cb815acbtt1"
}
```

Resposta completa observada:

```json
{
  "success": true,
  "data": {
    "session_id": "S_cb815acbtt1",
    "evaluated_at": "2026-04-09T17:35:49Z",
    "score_final": 99,
    "classification": "excelente",
    "executive_summary": "Atendimento muito bem conduzido, com qualificação adequada do lead, oferta aderente ao interesse em IA aplicada à cibersegurança e bom nível de personalização. Não foram identificadas falhas de conformidade, perda de contexto ou respostas desviadas ao longo da conversa. O caso terminou com envio de material e CTA claro para próximos passos, o que sustenta avaliação excelente, embora sem um fechamento comercial mais conclusivo.",
    "scores": {
      "C1": {
        "criterion_id": "C1",
        "criterion_name": "Identificação e compreensão da necessidade",
        "score": 100,
        "justification": "O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. O bot fez 2 perguntas de qualificação, registrou 0 suposições sem confirmação e lead_objective='Aplicar Inteligência Artificial em defesa cibernética e automação de processos de segurança'. Não houve deduções aplicadas neste critério.",
        "evidences": [
          "lead_area_of_interest: IA aplicada em Cybersecurity",
          "lead_background: Graduação em Redes de Computadores. Graduando em Defesa Cibernética.",
          "lead_objective: Aplicar Inteligência Artificial em defesa cibernética e automação de processos de segurança",
          "qualification_questions_asked: ['você já tem um curso em mente?', 'você busca uma especialização para crescer na área técnica mesmo ou pensa em migrar para funções de gestão e liderança?']",
          "repeated_qualification_questions: []",
          "info_assumed_without_confirmation: []",
          "context_lost_moments: []"
        ],
        "deductions": []
      },
      "C2": {
        "criterion_id": "C2",
        "criterion_name": "Assertividade da resposta",
        "score": 100,
        "justification": "O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 0 perguntas sem resposta e 0 perguntas com deflexão. Não houve deduções aplicadas neste critério.",
        "evidences": [
          "lead_questions_asked: ['Sim, quero saber mais']",
          "unanswered_questions: []",
          "deflected_questions: []",
          "course_correctly_identified: True"
        ],
        "deductions": []
      },
      "C3": {
        "criterion_id": "C3",
        "criterion_name": "Condução e fluxo da conversa",
        "score": 100,
        "justification": "O fluxo foi avaliado pela progressão da conversa e pela preservação de contexto. A conversa passou por 10 etapas e registrou 0 deduções relevantes de fluxo. Não houve deduções aplicadas neste critério.",
        "evidences": [
          "duplicate_bot_messages: []",
          "context_lost_moments: []",
          "wrong_course_assumed: False",
          "non_text_input_handled: None",
          "flow_progression: ['Bot saudou lead e mencionou interesse em pós-graduação', 'Bot perguntou se lead tinha curso em mente', 'Lead informou formação acadêmica (Redes de Computadores e Defesa Cibernética)', 'Bot qualificou objetivo de carreira (técnico vs gestão)', 'Lead expressou interesse em IA aplicada em Cybersecurity', 'Bot apresentou curso específico: IA e Cibersegurança', 'Bot descreveu diferenciais e ecossistema de aprendizagem', 'Bot ofereceu CTA para matrícula', 'Lead respondeu positivamente pedindo mais informações', 'Bot forneceu detalhes completos do curso e link para PDF']"
        ],
        "deductions": []
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
        "score": 90,
        "justification": "O desfecho foi avaliado pelo encaminhamento final, envio de material e presença de CTA. O status final identificado foi 'material_sent'. Não houve deduções aplicadas neste critério.",
        "evidences": [
          "resolution_status: material_sent",
          "material_sent: True",
          "cta_present: True",
          "last_message_sender: bot"
        ],
        "deductions": []
      }
    },
    "extracted_facts": {
      "metadata": {
        "session_id": "Pessoa_006",
        "total_turns": 8,
        "lead_turn_count": 4,
        "bot_turn_count": 4
      },
      "lead_profile": {
        "lead_name_informed": "Pessoa_006",
        "lead_area_of_interest": "IA aplicada em Cybersecurity",
        "lead_background": "Graduação em Redes de Computadores. Graduando em Defesa Cibernética.",
        "lead_objective": "Aplicar Inteligência Artificial em defesa cibernética e automação de processos de segurança",
        "lead_already_works_in_area": true
      },
      "qualification": {
        "qualification_questions_asked": [
          "você já tem um curso em mente?",
          "você busca uma especialização para crescer na área técnica mesmo ou pensa em migrar para funções de gestão e liderança?"
        ],
        "repeated_qualification_questions": [],
        "info_assumed_without_confirmation": []
      },
      "assertiveness": {
        "lead_questions_asked": [
          "Sim, quero saber mais"
        ],
        "unanswered_questions": [],
        "deflected_questions": [],
        "course_correctly_identified": true,
        "course_presented": [
          "IA e Cibersegurança: Automação e Eficiência para Segurança Digital"
        ],
        "course_not_found": false
      },
      "flow": {
        "duplicate_bot_messages": [],
        "context_lost_moments": [],
        "wrong_course_assumed": false,
        "wrong_course_assumed_evidence": null,
        "non_text_input_received": false,
        "non_text_input_handled": null,
        "flow_progression": [
          "Bot saudou lead e mencionou interesse em pós-graduação",
          "Bot perguntou se lead tinha curso em mente",
          "Lead informou formação acadêmica (Redes de Computadores e Defesa Cibernética)",
          "Bot qualificou objetivo de carreira (técnico vs gestão)",
          "Lead expressou interesse em IA aplicada em Cybersecurity",
          "Bot apresentou curso específico: IA e Cibersegurança",
          "Bot descreveu diferenciais e ecossistema de aprendizagem",
          "Bot ofereceu CTA para matrícula",
          "Lead respondeu positivamente pedindo mais informações",
          "Bot forneceu detalhes completos do curso e link para PDF"
        ]
      },
      "compliance": {
        "bot_greeted_lead_as": "Pessoa_006",
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
      "C1 com score 100.0: O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. O bot fez 2 perguntas de qualificação, registrou 0 suposições sem confirmação e lead_objective='Aplicar Inteligência Artificial em defesa cibernética e automação de processos de segurança'. Não houve deduções aplicadas neste critério.",
      "C2 com score 100.0: O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 0 perguntas sem resposta e 0 perguntas com deflexão. Não houve deduções aplicadas neste critério.",
      "C3 com score 100.0: O fluxo foi avaliado pela progressão da conversa e pela preservação de contexto. A conversa passou por 10 etapas e registrou 0 deduções relevantes de fluxo. Não houve deduções aplicadas neste critério."
    ],
    "improvement_areas": [
      "C5: aprofundar o critério 'Desfecho e encaminhamento'.",
      "C1: aprofundar o critério 'Identificação e compreensão da necessidade'.",
      "C2: aprofundar o critério 'Assertividade da resposta'."
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
