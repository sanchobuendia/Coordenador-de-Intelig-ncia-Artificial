# Documento de Solucao

## Visao geral

O objetivo da solucao e apoiar a avaliacao humana da qualidade de atendimentos em canais digitais, produzindo um relatorio estruturado com scores, justificativas e evidencias. O foco do MVP e combinar interpretacao flexivel de linguagem natural com regras claras de negocio e auditoria.

A arquitetura adotada no prototipo separa o problema em duas camadas:

- interpretacao da conversa em fatos estruturados
- avaliacao desses fatos por criterio, com rubricas versionaveis

Essa separacao evita que cada criterio dependa diretamente da conversa bruta, reduz custo, melhora rastreabilidade e facilita evolucao.

## Fluxo fim a fim

```text
Conversa recebida
  -> validacao do payload
  -> normalizacao em texto unico
  -> extrator LLM gera ExtractedFacts
  -> roteamento para 5 criterios paralelos
  -> scoring deterministico por rubrica
  -> sintese final do EvaluationReport
  -> resposta da API
```

Campos relevantes do relatorio:

- score final ponderado
- classificacao final
- score por criterio
- justificativa por criterio
- evidencias por criterio
- fatos extraidos da conversa
- pontos fortes
- areas de melhoria

## Criterios de avaliacao

O MVP usa cinco criterios com pesos explicitos:

- C1 Identificacao e compreensao da necessidade: 25%
- C2 Assertividade da resposta: 25%
- C3 Conducao e fluxo da conversa: 20%
- C4 Conformidade com regras de negocio: 20%
- C5 Desfecho e encaminhamento: 10%

Os criterios foram escolhidos para equilibrar experiencia do cliente, aderencia operacional e capacidade de coaching do operador.

## Estrategia de prompts

O prototipo usa prompt apenas no extrator. A decisao foi deliberada.

Principios:

- extrair fatos observaveis e nao julgamentos
- ser conservador em caso de ambiguidade
- preservar evidencias textuais no output estruturado
- produzir schema fixo para alimentar scoring deterministico

Trade-off:

- vantagem: menos variabilidade nos scores e maior auditabilidade
- desvantagem: parte da inteligencia analitica fica concentrada na cobertura do schema de extracao

Evolucao natural:

- versionar prompts por `prompt_version`
- armazenar prompt, modelo e resposta bruta por execucao
- introduzir prompts por criterio somente onde heuristica ficar insuficiente

## Estrategia de modelos

### MVP adotado

- um unico modelo para extracao estruturada
- scoring e sintese deterministica

Racional:

- menor custo por conversa
- menor latencia que uma arquitetura totalmente LLM
- maior consistencia entre execucoes
- mais facilidade de justificar a nota para auditoria humana

### Criterios para escolha do modelo do extrator

- boa aderencia a structured output
- custo previsivel
- baixa taxa de alucinacao
- boa performance em portugues

No prototipo, o extrator esta preparado para uso via LangChain com provider configuravel e Bedrock como padrao operacional.

## Estrategia de orquestracao

O fluxo foi modelado em LangGraph com fan-out/fan-in:

- um no de extracao
- cinco nos de avaliacao em paralelo
- um no final de sintese

Essa estrutura permite:

- paralelizar criterios
- inserir checkpoints
- isolar falhas por etapa
- evoluir criterios sem reescrever o pipeline inteiro

## Comparacao entre abordagens arquiteturais

### Abordagem A: pipeline hibrido com extracao LLM + scoring deterministico

Descricao:

- a conversa vira fatos estruturados
- os criterios calculam score a partir desses fatos

Vantagens:

- custo baixo e previsivel
- alta auditabilidade
- rubricas mais faceis de revisar com operacao
- menor variacao de output entre execucoes

Limitacoes:

- depende de boa cobertura do schema de extracao
- heuristicas podem ficar rigidas em casos de borda
- exige manutencao quando surgem novos tipos de atendimento

### Abordagem B: avaliadores LLM por criterio + sintetizador LLM

Descricao:

- extracao opcional
- cada criterio avalia a conversa ou os fatos com seu proprio prompt
- sintetizador consolida e produz recomendacoes

Vantagens:

- maior flexibilidade sem criar muitas regras manuais
- adaptacao mais rapida a novos cenarios
- potencial de capturar nuances sem engenharia adicional

Limitacoes:

- custo e latencia maiores
- maior variabilidade entre execucoes
- necessidade de controles mais fortes para auditoria
- maior risco de divergencia entre criterios

### Recomendacao

Para o MVP, eu adotaria a Abordagem A, que e a implementada neste repositorio. Ela atende melhor as premissas de viabilidade economica, auditabilidade, apoio a avaliacao humana e potencial de escala. A Abordagem B faria sentido como evolucao seletiva, principalmente para criterios com baixa cobertura heuristica ou em casos mais ambiguos.

## Auditabilidade e rastreabilidade

A solucao foi desenhada para permitir trilha de decisao:

- fatos extraidos ficam no relatorio final
- cada criterio retorna deducoes e evidencias
- pesos sao explicitos
- checkpoints do LangGraph podem ser persistidos em Postgres

Para producao, eu adicionaria:

- `model_version`, `prompt_version` e `rubric_version`
- armazenamento da resposta bruta do extrator
- IDs de trace por execucao
- painel com distribuicao de scores e drift por criterio
- fila de revisao humana para casos de baixa confianca

## Dados sensiveis

Parte das conversas pode conter dados pessoais. Por isso, a estrategia recomendada de producao inclui:

- mascaramento de PII antes de observabilidade externa
- controle de retencao
- segregacao de logs tecnicos e payloads
- principio de minimo privilegio para acesso aos dados
- anonimizacao para datasets de calibracao

## Visao de operacao

Em producao, eu operaria o sistema com quatro camadas:

- API stateless para recebimento
- fila/processamento assincrono quando volume crescer
- storage de traces e checkpoints
- monitoramento de qualidade e custo

Metricas importantes:

- latencia por etapa
- custo medio por conversa
- taxa de erro do extrator
- distribuicao de scores por criterio
- divergencia entre avaliacao humana e IA
- percentual de casos escalados para revisao

## Exemplo de execucao do prototipo

Para demonstrar o comportamento do MVP, foi executado um caso de atendimento em que o lead:

- informou o nome como `Pessoa_006`
- declarou formacao em Redes de Computadores e graduacao em Defesa Cibernetica
- explicitou interesse em `IA aplicada em Cybersecurity`
 
Observacao: o exemplo mais recente do `README.md` foi atualizado para um caso real de educacao inclusiva, com resposta completa do sistema. Os pontos abaixo permanecem apenas como ilustracao resumida do comportamento do prototipo e nao como copia literal do exemplo operacional documentado.

Resultado observado:

- `score_final`: `99`
- `classification`: `excelente`
- distribuicao dos criterios: `C1=100`, `C2=100`, `C3=100`, `C4=100`, `C5=90`

Leitura do resultado:

- a conversa performou bem em qualificacao, assertividade, fluxo e conformidade
- o criterio `C5` ficou ligeiramente abaixo dos demais porque o caso terminou em `material_sent`, com CTA e proximo passo claro, mas sem fechamento mais forte como escalada ou resolucao final
- o caso ilustra bem a proposta do MVP: separar fatos extraidos da etapa de scoring para permitir justificativa e auditoria por criterio

Evidencias relevantes capturadas nesse teste:

- `lead_area_of_interest: IA aplicada em Cybersecurity`
- `lead_background: Graduação em Redes de Computadores. Graduando em Defesa Cibernética.`
- `course_correctly_identified: True`
- `resolution_status: material_sent`
- `material_sent: True`
- `cta_present: True`

Observacao importante:

- neste teste houve um comportamento inconsistente no campo `extracted_facts.metadata.session_id`, que retornou `Pessoa_006` em vez do `sessionId` de entrada `S_cb815acbtt1`
- esse ponto nao invalida o racional arquitetural, mas deve ser tratado como ajuste de robustez antes de uma versao de producao

Entrada completa e saida completa desse teste estao documentadas no `README.md`, para facilitar reproducao e inspecao do comportamento do prototipo.

## Riscos e limitacoes

- o extrator ainda concentra bastante responsabilidade sem uma camada de confianca explicita
- regras heuristicas podem degradar quando o dominio sair do escopo atual
- nao ha calibracao estatistica com ground truth humano no repositorio
- o prototipo ainda nao processa voz, apenas texto
- nao ha politica implementada de redacao de dados sensiveis
- ha casos em que campos estruturados podem sair inconsistentes com o identificador de entrada e precisam de validacao adicional

## Proximos passos

1. Criar dataset rotulado por avaliadores humanos e medir concordancia.
2. Adicionar versao de prompt, rubrica e modelo no output.
3. Introduzir score de confianca e fila de revisao humana.
4. Expandir cobertura para transcricoes de voz.
5. Testar uma versao avancada com avaliadores LLM apenas nos criterios mais subjetivos.
6. Implementar observabilidade de producao com traces, custo e drift.
