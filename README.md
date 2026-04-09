# Conversation Quality Evaluator

Protótipo para avaliação auditável da qualidade de atendimentos em canais digitais. O MVP adota uma arquitetura híbrida: extração estruturada com LLM, scoring determinístico por rubrica e síntese executiva com LLM, orquestrados em um grafo LangGraph.

## Entrega do desafio

- Documento de solução: `SOLUTION.md`
- Registro de uso de IA: `AI_USAGE.md`
- Protótipo funcional: API FastAPI + pipeline em `src/evaluator`

## Arquitetura do MVP

```text
INPUT (conversa)
  -> GUARDRAILS (mascaramento de PII + neutralizacao de prompt injection)
  -> EXTRATOR LLM
  -> 5 AVALIADORES DETERMINISTICOS (C1..C5)
  -> SINTETIZADOR (RESUMO EXECUTIVO VIA LLM)
  -> EvaluationReport
```

Os avaliadores trabalham sobre fatos estruturados, não sobre a conversa bruta. Isso reduz variabilidade, facilita auditoria e desacopla a evolução dos critérios da etapa de interpretação textual. O score permanece determinístico; a LLM no sintetizador é usada apenas para gerar um `executive_summary` legível para o avaliador humano.

Guardrails implementados no MVP:

- mascaramento de dados sensiveis antes do extrator e dos logs tecnicos
- pseudonimizacao de nomes preservando consistencia para detectar `name_mismatch`
- redacao de CPF, telefone e email
- deteccao e neutralizacao de sinais comuns de prompt injection
- trilha de seguranca em `extracted_facts.security` no modo detalhado

Esses controles cobrem explicitamente dois riscos mencionados no desafio:

- conversas com dados sensiveis, reduzindo exposicao de nome, CPF, telefone e email
- tentativas de prompt injection no texto da conversa, neutralizadas antes da chamada ao modelo

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

Modo de resposta:

- padrão: resposta executiva, mais enxuta, sem `extracted_facts`, `evidences` e `deductions`
- `POST /evaluate?verbose=true`: resposta completa para auditoria, incluindo `extracted_facts.security`

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

## Exemplos

O endpoint `POST /evaluate` retorna por padrao uma visao executiva. Para auditoria completa, use `POST /evaluate?verbose=true`.

### Exemplo com score alto

Entrada completa:

```json
{
  "messages": [
    "human: Eu sou Pessoa_005",
    "ai: Olá, Pessoa_005, eu sou a Beatriz, consultora de carreira da +A Code Academy. Vi que você tem interesse em uma pós-graduação. Me conta: você já tem um curso em mente?",
    "human: Cuidador de idoso",
    "ai: Entendi sua busca pelo tema de cuidados com idosos. Muitos profissionais da área procuram especialização para aprimorar o atendimento e criar novas oportunidades. Você já atua com idosos atualmente ou está pensando em entrar nesse mercado?",
    "human: Já atuo",
    "ai: Que ótimo saber que você já atua na área! A pós-graduação em Saúde do Idoso: Cuidando da Mente e do Corpo é pensada justamente para profissionais como você, que desejam aprofundar os conhecimentos para melhorar a qualidade de vida, autonomia e saúde mental dos idosos. O curso é 100% online e voltado para práticas atuais de promoção da saúde.\nSeparei o material oficial com todos os detalhes do curso: Depois de dar uma olhada, posso te ajudar a avançar na inscrição ou tirar dúvidas sobre as próximas etapas. Vamos avançar hoje mesmo?"
  ],
  "sessionId": "S_cb815acb4"
}
```

Saida completa:

```json
{
  "success": true,
  "data": {
    "session_id": "S_cb815acb4",
    "evaluated_at": "2026-04-09T19:24:45Z",
    "score_final": 97.8,
    "classification": "excelente",
    "executive_summary": "O atendimento alcançou score excelente de 97,8 pontos, com desempenho perfeito na qualificação do lead, assertividade das respostas e condução da conversa. O bot identificou corretamente que o lead é um profissional experiente em cuidados com idosos buscando aprofundar conhecimentos, apresentou a pós-graduação em Saúde do Idoso de forma alinhada ao perfil e manteve fluxo consistente sem perder contexto. O único ponto de atenção está no desfecho, que atingiu 78 pontos, sugerindo oportunidade de melhoria no encaminhamento final. O atendimento foi finalizado com envio de material e call-to-action presente, posicionando o lead adequadamente para as próximas etapas.",
    "scores": {
      "C1": {
        "criterion_id": "C1",
        "criterion_name": "Identificação e compreensão da necessidade",
        "score": 100,
        "justification": "O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. O bot fez 2 perguntas de qualificação, registrou 0 suposições sem confirmação e lead_objective='Aprofundar conhecimentos e aprimorar o atendimento na área de cuidados com idosos'. Não houve deduções aplicadas neste critério."
      },
      "C2": {
        "criterion_id": "C2",
        "criterion_name": "Assertividade da resposta",
        "score": 100,
        "justification": "O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 0 perguntas sem resposta e 0 perguntas com deflexão. Não houve deduções aplicadas neste critério."
      },
      "C3": {
        "criterion_id": "C3",
        "criterion_name": "Condução e fluxo da conversa",
        "score": 100,
        "justification": "O fluxo foi avaliado pela progressão da conversa e pela preservação de contexto. A conversa passou por 8 etapas e registrou 0 deduções relevantes de fluxo. Não houve deduções aplicadas neste critério."
      },
      "C4": {
        "criterion_id": "C4",
        "criterion_name": "Conformidade com regras de negócio",
        "score": 100,
        "justification": "O critério verifica aderência às políticas comerciais e de personalização. Foram observadas 0 informações possivelmente inventadas e name_mismatch=False. Não houve deduções aplicadas neste critério."
      },
      "C5": {
        "criterion_id": "C5",
        "criterion_name": "Desfecho e encaminhamento",
        "score": 78,
        "justification": "O desfecho foi avaliado pelo encaminhamento final, envio de material e presença de CTA. O status final identificado foi 'material_sent'. Não houve deduções aplicadas neste critério."
      }
    },
    "strengths": [
      "C1 com score 100.0: O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. O bot fez 2 perguntas de qualificação, registrou 0 suposições sem confirmação e lead_objective='Aprofundar conhecimentos e aprimorar o atendimento na área de cuidados com idosos'. Não houve deduções aplicadas neste critério.",
      "C2 com score 100.0: O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 0 perguntas sem resposta e 0 perguntas com deflexão. Não houve deduções aplicadas neste critério.",
      "C3 com score 100.0: O fluxo foi avaliado pela progressão da conversa e pela preservação de contexto. A conversa passou por 8 etapas e registrou 0 deduções relevantes de fluxo. Não houve deduções aplicadas neste critério."
    ],
    "improvement_areas": [
      "C5: aprofundar o critério 'Desfecho e encaminhamento'.",
      "C1: aprofundar o critério 'Identificação e compreensão da necessidade'.",
      "C2: aprofundar o critério 'Assertividade da resposta'."
    ]
  }
}
```

### Exemplo com score baixo

Entrada completa:

```json
{
  "messages": [
    "human: Eu sou Pessoa_008",
    "human: Tenho interesse em pós em neurociência. Quais vc tem e valores?",
    "ai: Pessoa_008, temos várias opções de pós-graduação relacionadas à neurociência: Neurociência Aplicada: Produtividade e Performance Humana, Neurociência e Comportamento Alimentar, Neurociência, Psicologia Positiva e Mindfulness, Neurobranding e Neuromarketing: Estratégias de Engajamento Sensorial, Neuroarquitetura, Bem-estar e Experiência do Usuário e Neurocomunicação: Estratégias para Narrativas de Impacto.\nOs valores e detalhes do investimento são apresentados diretamente por um especialista. Para garantir um atendimento personalizado, posso agendar a transferência do seu atendimento para um especialista.\nTem preferência por algum desses temas para aprofundarmos e direcionar a conversa?",
    "human: Pelos nomes, me interesse por:\nNeurociência, psicologia positiva e mindfulness e neurocomunicacao.",
    "human: Mas gostaria de entender melhor",
    "human: E ver os valores",
    "ai: Ótimos interesses! Separei dois materiais para que você conheça melhor cada curso:\n\n- Neurociência, Psicologia Positiva e Mindfulness: PDF de Apresentação | Vídeo do coordenador\n- Neurocomunicação: Estratégias para Narrativas de Impacto: PDF de Apresentação\nPara valores e detalhes do investimento, direciono você para um atendimento personalizado com um especialista. Gostaria de agendar o melhor horário para essa conversa? Assim conseguimos esclarecer todas as dúvidas e avançar para a sua matrícula.",
    "ai: Veja os principais detalhes sobre as pós que você mencionou:\n\n📚 Pós em Neurociência, Psicologia Positiva e Mindfulness:\n✔️ 100% online, sem encontros presenciais\n✔️ Duração de 12 meses (com acesso garantido por até 24 meses)\n✔️ Carga horária: 360h (média de 6 a 7 horas semanais)\n✔️ Estrutura: 15 disciplinas (20h cada) + 1 avaliação online por disciplina\n✔️ Ao final: Projeto de Aplicação (substitui o TCC tradicional)\n🧑‍🏫 Cada disciplina tem:\n– 3 aulas gravadas\n– 2 aulas ao vivo, das 19h30 às 21h\n(Se não conseguir assistir ao vivo, não tem problema — elas ficam gravadas!)\n🎓 Certificado Lato Sensu +A Code Academy reconhecido pelo MEC, com o mesmo peso do presencial.\n📚 Pós em Neurocomunicação: Estratégias para Narrativas de Impacto:\n✔️ 100% online, sem encontros presenciais\n✔️ Duração de 12 meses (com acesso garantido por até 24 meses)\n✔️ Carga horária: 360h\n✔️ Estrutura: 15 disciplinas + avaliações online por disciplina\n✔️ Projeto de Aplicação ao final (no lugar do TCC tradicional)\n🧑‍🏫 Cada disciplina tem 3 aulas gravadas e 2 ao vivo\n🎓 Certificado Lato Sensu +A Code Academy reconhecido pelo MEC, mesmo peso do presencial\nSobre valores, para garantir a oferta personalizada e com todas as condições disponíveis, preciso agendar a transferência do seu atendimento para um especialista. Posso fazer o agendamento para você agora?\nFez sentido para o que você busca? Se quiser, abrimos a transferência para tirar dúvidas sobre valores e condições."
  ],
  "sessionId": "S_d8f548de"
}
```

Saida completa:

```json
{
  "success": true,
  "data": {
    "session_id": "S_d8f548de",
    "evaluated_at": "2026-04-09T19:20:02Z",
    "score_final": 47.1,
    "classification": "critico",
    "executive_summary": "Atendimento classificado como crítico com score 47.1. O bot identificou corretamente os cursos de interesse do lead, mas falhou gravemente na qualificação inicial, não realizando nenhuma pergunta para compreender o background e objetivo do cliente antes de oferecer agendamento. A conversa apresentou três mensagens duplicadas do bot oferecendo agendamento com especialista, causando perda de contexto, e não respondeu adequadamente à pergunta do lead sobre valores. Pontos positivos incluem conformidade com regras de negócio, envio de material e presença de call-to-action, deixando o atendimento em status pendente. Recomenda-se treinar o bot para qualificar leads antes de oferecer agendamentos e eliminar redundâncias nas mensagens.",
    "scores": {
      "C1": {
        "criterion_id": "C1",
        "criterion_name": "Identificação e compreensão da necessidade",
        "score": 37,
        "justification": "O critério considera a qualidade da qualificação inicial e a aderência aos fatos informados pelo lead. O bot fez 0 perguntas de qualificação, registrou 0 suposições sem confirmação e lead_objective=None. Deduções aplicadas: ausência de qualificação: -45pts; background do lead não identificado: -8pts; objetivo do lead não identificado: -10pts."
      },
      "C2": {
        "criterion_id": "C2",
        "criterion_name": "Assertividade da resposta",
        "score": 60,
        "justification": "O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 1 perguntas sem resposta e 1 perguntas com deflexão. Deduções aplicadas: pergunta sem resposta: -25pts; pergunta desviada: -15pts."
      },
      "C3": {
        "criterion_id": "C3",
        "criterion_name": "Condução e fluxo da conversa",
        "score": 18,
        "justification": "O fluxo foi avaliado pela progressão da conversa e pela preservação de contexto. A conversa passou por 8 etapas e registrou 4 deduções relevantes de fluxo. Deduções aplicadas: mensagem duplicada: -20pts; mensagem duplicada: -20pts; mensagem duplicada: -20pts; perda de contexto: -22pts."
      },
      "C4": {
        "criterion_id": "C4",
        "criterion_name": "Conformidade com regras de negócio",
        "score": 65,
        "justification": "O critério verifica aderência às políticas comerciais e de personalização. Foram observadas 0 informações possivelmente inventadas e name_mismatch=False. Deduções aplicadas: não escalou quando devia: -35pts."
      },
      "C5": {
        "criterion_id": "C5",
        "criterion_name": "Desfecho e encaminhamento",
        "score": 62,
        "justification": "O desfecho foi avaliado pelo encaminhamento final, envio de material e presença de CTA. O status final identificado foi 'pending'. Deduções aplicadas: status pending com material enviado e CTA presente: faixa 60-69."
      }
    },
    "strengths": [
      "C4 com score 65.0: O critério verifica aderência às políticas comerciais e de personalização. Foram observadas 0 informações possivelmente inventadas e name_mismatch=False. Deduções aplicadas: não escalou quando devia: -35pts.",
      "C5 com score 62.0: O desfecho foi avaliado pelo encaminhamento final, envio de material e presença de CTA. O status final identificado foi 'pending'. Deduções aplicadas: status pending com material enviado e CTA presente: faixa 60-69.",
      "C2 com score 60.0: O critério mede se as dúvidas do lead foram respondidas de forma direta e específica. Foram identificadas 1 perguntas sem resposta e 1 perguntas com deflexão. Deduções aplicadas: pergunta sem resposta: -25pts; pergunta desviada: -15pts."
    ],
    "improvement_areas": [
      "C3: corrigir mensagem duplicada: -20pts; mensagem duplicada: -20pts; mensagem duplicada: -20pts; perda de contexto: -22pts",
      "C1: corrigir ausência de qualificação: -45pts; background do lead não identificado: -8pts; objetivo do lead não identificado: -10pts",
      "C2: corrigir pergunta sem resposta: -25pts; pergunta desviada: -15pts"
    ]
  }
}
```

## Testes

```bash
pytest tests/ -v
```

O repositório também inclui workflow do GitHub Actions para rodar testes e cobertura mínima em `push` e `pull_request`.

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
