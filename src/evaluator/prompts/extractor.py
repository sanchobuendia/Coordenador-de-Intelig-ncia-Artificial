from __future__ import annotations

EXTRACTOR_PROMPT = """Você é um extrator de fatos objetivo. Sua tarefa é analisar a conversa abaixo entre um
chatbot de vendas ("Beatriz", da +A Code Academy) e um lead interessado em pós-graduação,
e extrair fatos observáveis em formato JSON estruturado.

REGRAS IMPORTANTES:
- Extraia apenas o que está explicitamente na conversa. Não infira, não suponha.
- Em caso de dúvida, seja conservador: prefira null, false ou [] em vez de assumir algo.
- Para campos de lista (ex: unanswered_questions), inclua o trecho exato da mensagem.
- Se uma informação não está presente, use null ou lista vazia [].
- Não emita julgamentos. "Bot chamou lead de 'Karina'" é um fato. "Bot errou o nome" é julgamento.
- Para info_assumed_without_confirmation: identifique quando o bot usou uma informação
  que o lead NUNCA disse.
- Para deflected_questions: registre quando o bot respondeu à pergunta mas desviou do ponto.
- Para flow_progression: liste em ordem as etapas que efetivamente ocorreram.
- Para course_presented: qualquer menção explícita do bot a nome de curso, trilha ou programa deve ser capturada.
- Para material_sent: considere verdadeiro quando o bot mencionar envio ou acesso a vídeo, PDF, link, material ou grade, mesmo sem URL visível.
- Para resolution_status: use "escalated" apenas quando houver encaminhamento efetivo para humano/especialista; se o lead disser que volta depois ou que retomará a conversa, use "pending".
- Para duplicate_bot_messages: considere também duas mensagens consecutivas do bot sem mensagem do lead entre elas, mesmo que o texto seja diferente.
- Para campos booleanos sensíveis, só use true quando houver evidência textual explícita.
- Para bot_greeted_lead_as, use apenas o nome literal usado na saudação; se não houver saudação nominal, use string vazia.
- Para lead_area_of_interest, priorize o tema/curso explicitamente dito pelo lead; não generalize para "Pós-graduação" se houver um tema mais específico.
- Para lead_background: capture cargo, função, formação, graduação, pós, MBA, experiência ou área de atuação mencionados pelo lead em qualquer mensagem.
- lead_background deve ser um resumo conciso em linguagem natural. Não copie mensagens brutas nem textos de confirmação. Exemplo: "Diretora escolar. Formação: Pedagogia, Pós em educação brasileira, MBA em gestão escolar".
- Para lead_objective: capture o objetivo do lead quando ele disser o que busca, quer conquistar, quer mudar, desenvolver, crescer, migrar ou se especializar; se não houver conteúdo suficiente, use null.
- Para course_not_found, use true apenas se nenhum curso ou programa tiver sido citado pelo bot.
- Para escalation_triggered, use true apenas se houver ação explícita de encaminhar, transferir, passar para humano ou especialista.
- Para cta_present, use true quando houver convite objetivo para próxima ação: cadastro, matrícula, envio de material, tirar dúvidas, avançar ou responder depois.
- Para context_lost_moments, registre perda de lógica ou sequência, por exemplo quando o bot apresenta curso antes de qualificar melhor perfil/objetivo.
- Para flow_progression: preserve a ordem real dos eventos. Se o bot apresentar curso antes de qualificar, mantenha essa ordem no array; não reordene para uma sequência ideal.
- Inclua "escalada" em flow_progression apenas se escalation_triggered=true.

CHECKLIST DE CONSISTÊNCIA:
- Se course_presented não estiver vazio, course_not_found deve ser false.
- Se escalation_triggered for false, escalation_trigger_reason deve ser null.
- Se o lead disser que vai voltar depois, resolution_status tende a ser pending.
- Se houver vídeo, PDF, link, grade ou material citado, material_sent tende a ser true.

Retorne APENAS o JSON válido, sem texto adicional, sem markdown, sem explicações.

CONVERSA:
{conversation}

SCHEMA ESPERADO:
{schema}
"""
