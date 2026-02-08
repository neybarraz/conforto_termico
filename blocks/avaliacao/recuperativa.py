# blocks/avaliacao/recuperativa.py
# =============================================================================
# AVALIAÇÃO RECUPERATIVA
# Regras:
# - Só habilita se a Prova estiver enviada e a nota for < NOTA_MINIMA
# - Além disso, só habilita se o aluno estiver AUTORIZADO no alunos.csv
#   (flag: habilitado_recuperativa = 1)
# - Formato implementado: Prova equivalente (10 múltipla escolha)
# - Após enviar: bloqueia respostas, mostra acertos/erros e nota
# - Nota final: regra padrão = max(nota_prova, nota_recuperativa) (configurável)
# Persistência:
# - JSON: stage_path(ctx, STAGE_ID)
# Dependência de leitura:
# - Lê o JSON da prova (stage_path(ctx, "avaliacao_prova"))
# =============================================================================

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime

import streamlit as st

from storage.paths import stage_path
from storage.io_csv import load_json, save_json

# >>> NOVO: gate por stage (autorização administrativa)
from ui.auth import is_enabled_for_stage, StudentRecord


STAGE_ID = "avaliacao_recuperativa"
STAGE_PROVA_ID = "avaliacao_prova"

NOTA_MINIMA = 6.0  # critério mínimo (ajuste conforme sua regra)


def _ctx_get_state(ctx: Dict) -> Dict[str, Any]:
    if isinstance(ctx, dict) and isinstance(ctx.get("state"), dict):
        return ctx["state"]
    key = "__pbl_state__avaliacao_recuperativa"
    if key not in st.session_state:
        st.session_state[key] = {}
    return st.session_state[key]


def _get(state: Dict[str, Any], k: str, default: Any) -> Any:
    return state.get(k, default)


def _set(state: Dict[str, Any], k: str, v: Any) -> None:
    state[k] = v


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _get_student_from_session_or_ctx(ctx: Dict) -> Optional[StudentRecord]:
    """
    Tenta obter o aluno autenticado.
    Prioridade:
      1) st.session_state["student"]  (padrão do login único)
      2) ctx["student"]               (se você optar por colocar no ctx)
    """
    student = st.session_state.get("student", None)
    if isinstance(student, StudentRecord):
        return student

    student2 = ctx.get("student", None) if isinstance(ctx, dict) else None
    if isinstance(student2, StudentRecord):
        return student2

    return None


def _build_questions() -> List[Dict[str, Any]]:
    # Questões novas (mesma matriz conceitual, novos enunciados)
    return [
        {
            "id": "rq01_escalas",
            "tag": "Temperatura e escalas térmicas",
            "stem": "Qual afirmação é mais adequada sobre o uso de sensores na medição de Ta em uma sala?",
            "options": [
                "A posição do sensor não importa; Ta é sempre igual em todo o ambiente.",
                "A leitura depende do ponto/altura e do tempo; por isso pontos e horários devem ser registrados.",
                "Sensores medem diretamente “calor” em Joules.",
                "A umidade relativa substitui a necessidade de medir temperatura.",
            ],
            "correct": 1,
        },
        {
            "id": "rq02_tc_interpretacao",
            "tag": "Teoria cinética dos gases",
            "stem": "Se Ta aumenta em um ponto do ambiente, uma explicação compatível com teoria cinética é:",
            "options": [
                "A energia cinética média das moléculas do ar aumentou naquele ponto.",
                "A densidade do ar necessariamente aumentou.",
                "A radiação desapareceu naquele ponto.",
                "A condução no ar tornou-se impossível.",
            ],
            "correct": 0,
        },
        {
            "id": "rq03_transferencia_mix",
            "tag": "Calor e formas de transferência",
            "stem": "Uma parede aquecida pelo sol pode influenciar o ar do ambiente por:",
            "options": [
                "Radiação para objetos/pessoas e convecção do ar adjacente.",
                "Apenas condução direta com o corpo humano.",
                "Somente evaporação do suor.",
                "Apenas aumento da umidade relativa.",
            ],
            "correct": 0,
        },
        {
            "id": "rq04_equilibrio_sentido",
            "tag": "Conceito de equilíbrio térmico",
            "stem": "Dizer que a sala “tende ao equilíbrio térmico” significa, de forma física, que:",
            "options": [
                "As temperaturas ficam exatamente iguais em todos os pontos instantaneamente.",
                "As diferenças de temperatura e fluxos de energia tendem a diminuir com o tempo, dadas condições estáveis.",
                "Sempre existe corrente de ar forte.",
                "A radiação é sempre nula.",
            ],
            "correct": 1,
        },
        {
            "id": "rq05_conveccao_forcada",
            "tag": "Noções de convecção natural e forçada",
            "stem": "O uso de ventilador altera o conforto térmico principalmente por:",
            "options": [
                "Aumentar o movimento do ar e intensificar trocas convectivas com o corpo.",
                "Reduzir a energia interna do ar sem troca de energia.",
                "Eliminar condução em superfícies.",
                "Transformar radiação em condução automaticamente.",
            ],
            "correct": 0,
        },
        {
            "id": "rq06_primeira_lei_qualitativa",
            "tag": "Primeira Lei da Termodinâmica",
            "stem": "Uma aplicação qualitativa coerente da Primeira Lei em uma sala é:",
            "options": [
                "A energia interna muda apenas por ‘vontade’ do sistema.",
                "Mudanças térmicas decorrem de balanço entre entradas/saídas de energia (trocas com paredes, janelas e ventilação).",
                "Temperatura não tem relação com energia interna.",
                "Energia interna é sempre constante em sistemas reais.",
            ],
            "correct": 1,
        },
        {
            "id": "rq07_grafico_gradiente",
            "tag": "Interpretação física de dados",
            "stem": "Se Ts (superfície) perto da janela é maior do que Ts no centro, isso sugere:",
            "options": [
                "Gradiente térmico associado a fontes/transferências locais (ex.: insolação), devendo ser sustentado por condições e repetição.",
                "Equilíbrio perfeito, pois Ts é diferente.",
                "Que a UR é inválida.",
                "Que convecção não existe.",
            ],
            "correct": 0,
        },
        {
            "id": "rq08_incerteza",
            "tag": "Interpretação física de dados",
            "stem": "Qual é um exemplo de incerteza experimental relevante nesse PBL?",
            "options": [
                "Trocar ‘calor’ por ‘temperatura’ por estilo.",
                "Diferença de leitura por posicionamento/tempo de estabilização do sensor.",
                "Aumentar o número de pessoas na sala sem registrar.",
                "Escolher um mecanismo dominante por preferência pessoal.",
            ],
            "correct": 1,
        },
        {
            "id": "rq09_mecanismo_dominante",
            "tag": "Calor e formas de transferência",
            "stem": "Para sustentar “mecanismo dominante”, a melhor prática é:",
            "options": [
                "Escolher o mecanismo mais comum em livros.",
                "Relacionar evidências (dados + condições) a uma lógica física de transferência e comparar alternativas.",
                "Usar uma fórmula pronta sem explicar.",
                "Evitar qualquer referência a dados.",
            ],
            "correct": 1,
        },
        {
            "id": "rq10_umidade",
            "tag": "Variáveis ambientais (UR)",
            "stem": "Mesmo com Ta semelhante em dois pontos, o desconforto pode diferir se:",
            "options": [
                "A UR e o movimento do ar diferirem, alterando trocas de energia do corpo (ex.: evaporação e convecção).",
                "A cor do caderno mudar.",
                "O relógio estiver adiantado.",
                "Não houver paredes no ambiente.",
            ],
            "correct": 0,
        },
    ]


def _score(questions: List[Dict[str, Any]], answers: Dict[str, int]) -> Dict[str, Any]:
    total = len(questions)
    correct_ids: List[str] = []
    wrong_ids: List[str] = []
    missing_ids: List[str] = []

    for q in questions:
        qid = q["id"]
        if qid not in answers or answers[qid] is None:
            missing_ids.append(qid)
            continue
        if int(answers[qid]) == int(q["correct"]):
            correct_ids.append(qid)
        else:
            wrong_ids.append(qid)

    acertos = len(correct_ids)
    erros = len(wrong_ids)
    faltantes = len(missing_ids)
    nota_0_10 = round((acertos / total) * 10, 2) if total > 0 else 0.0

    return {
        "total": total,
        "acertos": acertos,
        "erros": erros,
        "faltantes": faltantes,
        "nota_0_10": nota_0_10,
        "correct_ids": correct_ids,
        "wrong_ids": wrong_ids,
        "missing_ids": missing_ids,
    }


def render(ctx: Dict) -> None:
    path = stage_path(ctx, STAGE_ID)
    state = _ctx_get_state(ctx)

    # Carrega 1x
    if not _get(state, "__loaded__", False):
        saved = load_json(path) or {}
        if isinstance(saved, dict):
            for k, v in saved.items():
                if k not in state:
                    state[k] = v
        _set(state, "__loaded__", True)

    aluno = ctx.get("aluno", "Aluno")
    st.title("Avaliação Recuperativa")
    st.caption("Disponível apenas se a nota da prova for inferior ao critério mínimo e houver autorização.")
    st.markdown("---")

    # Lê prova
    prova_path = stage_path(ctx, STAGE_PROVA_ID)
    prova_data = load_json(prova_path) or {}
    prova_submitted = bool(isinstance(prova_data, dict) and prova_data.get("submitted", False))
    prova_nota = None
    if isinstance(prova_data, dict):
        prova_res = prova_data.get("result", {}) or {}
        if isinstance(prova_res, dict):
            prova_nota = prova_res.get("nota_0_10", None)

    if not prova_submitted:
        st.info("A prova ainda não foi enviada. A recuperativa só aparece após a prova registrada.")
        return

    if prova_nota is None:
        st.warning("Não foi possível ler a nota da prova. Verifique o JSON da prova.")
        return

    st.write(f"Nota da prova: **{prova_nota}** (mínimo: {NOTA_MINIMA})")

    # Se passou, não existe recuperativa
    if float(prova_nota) >= float(NOTA_MINIMA):
        st.success("Recuperativa não necessária: nota já atende ao critério mínimo.")
        return

    # >>> NOVO: autorização administrativa (alunos.csv)
    student = _get_student_from_session_or_ctx(ctx)
    if student is None:
        st.warning("Sessão de aluno não encontrada. Faça login novamente.")
        return

    if not is_enabled_for_stage(student, STAGE_ID):
        st.error("Você não está autorizado a realizar a avaliação recuperativa.")
        st.caption("Se houver dúvida, procure o professor para liberação.")
        return

    st.warning("Recuperativa habilitada: sua nota na prova ficou abaixo do mínimo e você está autorizado.")
    st.markdown("---")

    questions = _build_questions()

    submitted = bool(_get(state, "submitted", False))
    saved_answers = _get(state, "answers", {})
    if not isinstance(saved_answers, dict):
        saved_answers = {}

    st.markdown("### Prova equivalente (10 questões)")
    st.write("Após enviar, suas respostas ficam bloqueadas.")

    answers: Dict[str, Optional[int]] = {}

    for i, q in enumerate(questions, start=1):
        qid = q["id"]
        opts = q["options"]

        if submitted and qid in saved_answers and saved_answers[qid] is not None:
            idx_default = int(saved_answers[qid])
        else:
            idx_default = saved_answers.get(qid, None)
            if idx_default is None:
                idx_default = -1

        st.markdown(f"**{i}.** {q['stem']}")
        options_with_placeholder = ["— selecione —"] + opts
        if idx_default is None or int(idx_default) < 0:
            radio_index = 0
        else:
            radio_index = int(idx_default) + 1

        choice = st.radio(
            label=f"Resposta {i}",
            options=options_with_placeholder,
            index=radio_index,
            key=f"{STAGE_ID}_{qid}",
            disabled=submitted,
            label_visibility="collapsed",
        )

        if choice == "— selecione —":
            answers[qid] = None
        else:
            answers[qid] = options_with_placeholder.index(choice) - 1

        st.markdown("<div style='margin-bottom:0.6rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    if submitted:
        result = _get(state, "result", {}) or {}
        if not isinstance(result, dict):
            result = _score(questions, {k: int(v) for k, v in saved_answers.items() if v is not None})

        st.success("Recuperativa já enviada. Respostas bloqueadas.")
        st.write(f"Acertos: **{result.get('acertos', 0)}** / {result.get('total', 10)}")
        st.write(f"Erros: **{result.get('erros', 0)}**")
        st.write(f"Nota recuperativa (0–10): **{result.get('nota_0_10', 0.0)}**")

        # Regra padrão de nota final
        nota_final = max(float(prova_nota), float(result.get("nota_0_10", 0.0)))
        st.markdown("---")
        st.write(f"Nota final (regra padrão = max(prova, recuperativa)): **{nota_final}**")
        when = _get(state, "submitted_at", "")
        if when:
            st.caption(f"Enviado em: {when}")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Enviar recuperativa (bloqueia respostas)", key=f"{STAGE_ID}_submit"):
            if any(v is None for v in answers.values()):
                st.error("Responda todas as 10 questões antes de enviar.")
                _set(state, "answers", answers)
                return

            answers_int = {k: int(v) for k, v in answers.items()}  # type: ignore[arg-type]
            result = _score(questions, answers_int)

            payload = {
                "stage_id": STAGE_ID,
                "submitted": True,
                "submitted_at": _now_iso(),
                "answers": answers_int,
                "result": result,
                "concluido": True,
                "aluno": aluno,
                "prova_nota": float(prova_nota),
                "nota_final_regra": "max(prova, recuperativa)",
                "nota_final": max(float(prova_nota), float(result["nota_0_10"])),
            }

            save_json(path, payload)

            _set(state, "submitted", True)
            _set(state, "submitted_at", payload["submitted_at"])
            _set(state, "answers", answers_int)
            _set(state, "result", result)
            _set(state, "concluido", True)

            st.success("Recuperativa enviada e registrada. Respostas agora estão bloqueadas.")
            st.write(f"Acertos: **{result['acertos']}** / {result['total']}")
            st.write(f"Erros: **{result['erros']}**")
            st.write(f"Nota recuperativa (0–10): **{result['nota_0_10']}**")
            st.write(f"Nota final (max): **{payload['nota_final']}**")

    with col2:
        if st.button("Salvar rascunho", key=f"{STAGE_ID}_draft"):
            payload = {
                "stage_id": STAGE_ID,
                "submitted": False,
                "answers": {k: (int(v) if v is not None else None) for k, v in answers.items()},
                "concluido": False,
                "saved_at": _now_iso(),
                "aluno": aluno,
                "prova_nota": float(prova_nota),
            }
            save_json(path, payload)
            _set(state, "answers", payload["answers"])
            st.success("Rascunho salvo (ainda não enviado).")
