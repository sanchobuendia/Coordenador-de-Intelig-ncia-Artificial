import json
from pathlib import Path

from evaluator.graph import graph


def load_examples():
    path = Path(__file__).resolve().parents[1] / "data" / "examples" / "conversations.json"
    return {item["session_id"]: item for item in json.loads(path.read_text())}


def invoke_example(session_id: str):
    example = load_examples()[session_id]
    return graph.invoke(
        {
            "session_id": session_id,
            "conversation": "\n".join(f'{m["role"]}: {m["content"]}' for m in example["messages"]),
        }
    )["report"]


def test_pipeline_name_mismatch_hits_c4():
    report = invoke_example("S_84b564f9")
    assert "nome errado do lead: -25pts" in report.scores["C4"].deductions


def test_pipeline_wrong_course_assumed_hits_c3():
    report = invoke_example("S_22492061")
    assert report.extracted_facts.flow.wrong_course_assumed is True


def test_pipeline_deflected_question_hits_c2():
    report = invoke_example("S_f72ec490")
    assert report.extracted_facts.assertiveness.deflected_questions


def test_pipeline_honest_when_uninformed_hits_c4():
    report = invoke_example("S_68c0d237")
    assert report.extracted_facts.compliance.honest_when_uninformed is True


def test_pipeline_clean_flow_scores_high():
    report = invoke_example("S_14252299")
    assert report.score_final > 75


def test_pipeline_real_case_does_not_mark_false_escalation():
    conversation = "\n".join(
        [
            "human: Eu sou Pessoa_002",
            "ai: Olá, Pessoa_002! Eu sou a Beatriz, consultora de carreira da +A Code Academy. Vi que você tem interesse em uma pós-graduação. Você já tem algum curso em mente ou gostaria de ajuda para escolher?",
            "human: Dentro de Ed inclusiva",
            'ai: Entendi seu interesse em abordar temas de educação inclusiva. Temos uma pós em "TEA, TDAH e Inclusão: Saúde, Família e Sociedade", que pode ser relevante para esse campo.\nPosso te perguntar qual sua área de formação ou atuação para entender como essa especialização pode ajudar nos seus objetivos?',
            "human: Reposta da mensagem:  Entendi seu interesse em abordar temas de educação inclusiva. Temos uma pós em \"TEA, TDAH e Inclusão: Saúde, Família e Sociedade\", que pode ser relevante para esse campo. Resposta:  Sim",
            "human: Sou diretora escolar",
            "ai: Só para confirmar, quando você respondeu 'sim', está dizendo que já atua ou tem formação na área de educação inclusiva? Assim consigo te direcionar melhor.",
            "human: Pedagogia \nPós em educação brasileira \nMBA em gestão escolar",
            "ai: Ótimo saber que você é diretora escolar! Muitos profissionais de gestão na educação buscam essa especialização para promover práticas mais inclusivas nas escolas.\nTem algum desafio específico ou objetivo que te motivou a buscar o curso de TEA, TDAH e Inclusão?",
            "human: Reposta da mensagem:  Só para confirmar, quando você respondeu 'sim', está dizendo que já atua ou tem formação na área de educação inclusiva? Assim consigo te direcionar melhor. Resposta:  Não . Sim para o interesse nesse curso",
            "ai: Sua formação é uma base sólida para liderar ações de inclusão escolar. A pós em TEA, TDAH e Inclusão: Saúde, Família e Sociedade aprofunda o olhar sobre políticas inclusivas, a integração de talentos neurodiversos, e prepara gestores para construir estratégias efetivas junto a equipes e famílias.\nVeja o vídeo de apresentação e acesse o material completo do curso nos links abaixo:\nSe quiser, posso te orientar para os próximos passos e os detalhes da matrícula. Posso prosseguir com seu cadastro ou prefere tirar alguma dúvida pontual sobre o programa?",
            "ai: Ótimo, já entendi que seu interesse é direcionado ao curso TEA, TDAH e Inclusão: Saúde, Família e Sociedade. Essa pós-graduação trabalha temas como neurodesenvolvimento, políticas públicas de inclusão, estratégias para integração de alunos neurodivergentes e o papel da família e da escola, sempre priorizando a construção de uma cultura inclusiva na gestão escolar.\nVocê pode conhecer detalhes da estrutura e forma de aplicação do curso neste vídeo de apresentação.\nE conferir a grade curricular e informações em PDF.\nSe quiser seguir para inscrição ou tirar dúvidas pontuais sobre valor, prazo ou formas de ingresso, me avise que já te passo as próximas orientações.",
            "human: Estou no trânsito agora . Chegando no trabalho vejo o vídeo e te chamo aqui",
            "ai: Perfeito, fique à vontade para assistir ao vídeo quando conseguir! Assim que estiver pronta, é só me chamar aqui para conversarmos sobre dúvidas ou sobre o processo de matrícula. Deixo aberto para avançarmos juntos quando for o melhor momento para você.",
        ]
    )
    report = graph.invoke({"session_id": "S_cb815acb", "conversation": conversation})["report"]
    assert report.extracted_facts.resolution.resolution_status == "pending"
    assert report.extracted_facts.compliance.escalation_triggered is False
    assert report.extracted_facts.resolution.material_sent is True
    assert report.extracted_facts.resolution.cta_present is True
    assert report.scores["C5"].score == 72.0
