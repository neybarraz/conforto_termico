# blocks/avaliacao/prova.py
# =============================================================================
# PROVA (AVALIAÇÃO) — 10 questões de múltipla escolha
# Regras:
# - 10 questões
# - Ao finalizar: mostra acertos e erros
# - Se já respondeu (submitted=True): não permite alterar, só visualizar resultado
# Persistência:
# - JSON: stage_path(ctx, STAGE_ID)
# =============================================================================

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime

import streamlit as st

from storage.paths import stage_path
from storage.io_csv import load_json, save_json

STAGE_ID = "avaliacao_prova"

# Conteúdos essenciais (coerente com blocks/problema/conteudos_essenciais.py)
CONTEUDOS_ESSENCIAIS = [
    "Temperatura e escalas térmicas",
    "Teoria cinética dos gases",
    "Calor e formas de transferência",
    "Primeira Lei da Termodinâmica",
    "Noções de convecção natural e forçada",
    "Conceito de equilíbrio térmico",
]


def _ctx_get_state(ctx: Dict) -> Dict[str, Any]:
    if isinstance(ctx, dict) and isinstance(ctx.get("state"), dict):
        return ctx["state"]
    key = "__pbl_state__avaliacao_prova"
    if key not in st.session_state:
        st.session_state[key] = {}
    return st.session_state[key]


def _get(state: Dict[str, Any], k: str, default: Any) -> Any:
    return state.get(k, default)


def _set(state: Dict[str, Any], k: str, v: Any) -> None:
    state[k] = v


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _build_questions() -> List[Dict[str, Any]]:
    """
    Cada questão:
      - id: str
      - stem: enunciado
      - options: lista de alternativas
      - correct: índice correto em options
      - tag: conteúdo principal (para rastreabilidade)
    """
    return [
        {
            "id": "q01_temp_calor",
            "tag": "Temperatura e escalas térmicas",
            "stem": "Em termos físicos, qual afirmação diferencia corretamente temperatura e calor?",
            "options": [
                "Temperatura é energia transferida; calor é estado térmico do sistema.",
                "Temperatura caracteriza o estado térmico; calor é energia transferida por diferença de temperatura.",
                "Temperatura e calor são sinônimos, apenas com unidades diferentes.",
                "Calor é a energia interna total; temperatura é a energia total do sistema.",
            ],
            "correct": 1,
        },
        {
            "id": "q02_tc_gases",
            "tag": "Teoria cinética dos gases",
            "stem": "Na teoria cinética, aumento de temperatura do ar (Ta) está mais diretamente associado a:",
            "options": [
                "Diminuição da energia cinética média das moléculas.",
                "Aumento da energia cinética média das moléculas.",
                "Aumento obrigatório da massa do ar.",
                "Transformação do ar em líquido.",
            ],
            "correct": 1,
        },
        {
            "id": "q03_equilibrio",
            "tag": "Conceito de equilíbrio térmico",
            "stem": "Dois corpos em contato estão em equilíbrio térmico quando:",
            "options": [
                "Têm a mesma massa.",
                "Têm a mesma temperatura e não há fluxo líquido de energia térmica entre eles.",
                "Ambos estão em movimento.",
                "Ambos recebem radiação solar igualmente.",
            ],
            "correct": 1,
        },
        {
            "id": "q04_conducao",
            "tag": "Calor e formas de transferência",
            "stem": "Qual situação representa predominantemente condução de calor?",
            "options": [
                "Ar quente subindo perto do teto.",
                "Corrente de ar gerada por um ventilador.",
                "Mão encostada em uma mesa fria sentindo resfriamento local.",
                "Aquecimento por luz solar atravessando uma janela.",
            ],
            "correct": 2,
        },
        {
            "id": "q05_conveccao_natural",
            "tag": "Noções de convecção natural e forçada",
            "stem": "Convecção natural em uma sala ocorre principalmente porque:",
            "options": [
                "O ar mais quente fica menos denso e tende a subir, criando circulação.",
                "A radiação térmica cria vento constante.",
                "A condução no ar é maior que nos sólidos.",
                "A umidade relativa impede o ar de se mover.",
            ],
            "correct": 0,
        },
        {
            "id": "q06_conveccao_forcada",
            "tag": "Noções de convecção natural e forçada",
            "stem": "Convecção forçada é mais bem caracterizada por:",
            "options": [
                "Transferência de energia por ondas eletromagnéticas.",
                "Movimento do fluido imposto por um agente externo (ventilador/AC).",
                "Contato direto entre sólido e sólido.",
                "Ausência de movimento do ar.",
            ],
            "correct": 1,
        },
        {
            "id": "q07_radiacao",
            "tag": "Calor e formas de transferência",
            "stem": "Qual evidência sugere papel importante de radiação térmica no desconforto?",
            "options": [
                "Mesa fria ao toque.",
                "Corrente de ar constante no corredor.",
                "Sensação de calor perto de uma janela ensolarada mesmo sem tocar em nada.",
                "Ar subindo lentamente perto de uma parede interna.",
            ],
            "correct": 2,
        },
        {
            "id": "q08_primeira_lei",
            "tag": "Primeira Lei da Termodinâmica",
            "stem": "No contexto da Primeira Lei aplicada a uma sala, uma interpretação qualitativa coerente é:",
            "options": [
                "A energia interna do ar só depende da cor das paredes.",
                "Variações de energia interna podem estar ligadas a trocas de calor com paredes/janelas e a efeitos de ventilação.",
                "Não há troca de energia em ambientes reais.",
                "Temperatura aumenta sem qualquer troca de energia.",
            ],
            "correct": 1,
        },
        {
            "id": "q09_leitura_grafico",
            "tag": "Interpretação física de dados",
            "stem": "Um gráfico mostra Ta maior perto da janela do que no centro durante a tarde. A inferência física mais adequada (sem “caixa-preta”) é:",
            "options": [
                "O sensor está sempre errado; não é possível concluir nada.",
                "Existe um gradiente térmico; pode haver ganho de energia associado à radiação solar/transferência pela janela, devendo ser sustentado por condições e repetição.",
                "O equilíbrio térmico é garantido, pois há diferença de Ta.",
                "Condução no ar é o mecanismo dominante, necessariamente.",
            ],
            "correct": 1,
        },
        {
            "id": "q10_umidade",
            "tag": "Variáveis ambientais (UR)",
            "stem": "Em conforto térmico, a umidade relativa (UR) é relevante porque:",
            "options": [
                "Determina diretamente a massa do corpo humano.",
                "Pode influenciar a percepção térmica ao afetar a evaporação do suor (trocas de energia com o corpo).",
                "Impede completamente a convecção.",
                "Elimina a radiação térmica.",
            ],
            "correct": 1,
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

    # Nota em 0–10
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
    grupo_id = ctx.get("grupo_id", "")
    grupo_nome = ctx.get("grupo_nome", "")
    if grupo_id and grupo_nome:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id} ({grupo_nome})")
    else:
        st.caption(f"Aluno: {aluno}")

    st.title("Prova — Avaliação Individual (10 questões)")
    st.caption(
        "Foco: raciocínio físico e interpretação. Após enviar, suas respostas ficam bloqueadas."
    )
    st.markdown("---")

    questions = _build_questions()

    submitted = bool(_get(state, "submitted", False))
    saved_answers = _get(state, "answers", {})
    if not isinstance(saved_answers, dict):
        saved_answers = {}

    # Painel lateral/apoio: conteúdos essenciais (fixo)
    with st.expander("Conteúdos avaliados (referência)", expanded=False):
        st.write("Derivados do percurso do PBL (conteúdos essenciais):")
        for c in CONTEUDOS_ESSENCIAIS:
            st.write(f"- {c}")

    st.markdown("### Questões")
    st.write("Selecione uma alternativa por questão.")

    answers: Dict[str, Optional[int]] = {}
    for i, q in enumerate(questions, start=1):
        qid = q["id"]
        opts = q["options"]

        # Se já submetido: trava no valor salvo
        if submitted and qid in saved_answers and saved_answers[qid] is not None:
            idx_default = int(saved_answers[qid])
        else:
            # durante preenchimento: tenta usar o que já está no state
            idx_default = saved_answers.get(qid, None)
            if idx_default is None:
                idx_default = -1  # sem seleção

        st.markdown(f"**{i}.** {q['stem']}")
        # Radio com placeholder: adiciona uma opção "— selecione —" na frente
        options_with_placeholder = ["— selecione —"] + opts
        if idx_default is None or int(idx_default) < 0:
            radio_index = 0
        else:
            radio_index = int(idx_default) + 1  # shift por causa do placeholder

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
            answers[qid] = options_with_placeholder.index(choice) - 1  # volta ao índice real

        st.markdown("<div style='margin-bottom:0.6rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # Se já submetido, só mostra resultado do que foi salvo
    if submitted:
        result = _get(state, "result", {}) or {}
        if not isinstance(result, dict):
            result = _score(questions, {k: int(v) for k, v in saved_answers.items() if v is not None})

        st.success("Prova já enviada. Respostas bloqueadas.")
        st.write(f"Acertos: **{result.get('acertos', 0)}** / {result.get('total', 10)}")
        st.write(f"Erros: **{result.get('erros', 0)}**")
        st.write(f"Nota (0–10): **{result.get('nota_0_10', 0.0)}**")
        when = _get(state, "submitted_at", "")
        if when:
            st.caption(f"Enviado em: {when}")
        return

    # Caso não submetido: botão enviar + validação
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Enviar prova (bloqueia respostas)", key=f"{STAGE_ID}_submit"):
            # valida
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
                "concluido": True,  # critério de conclusão: prova realizada + registrada
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
            }

            save_json(path, payload)

            # Atualiza estado em memória para refletir travamento imediato
            _set(state, "submitted", True)
            _set(state, "submitted_at", payload["submitted_at"])
            _set(state, "answers", answers_int)
            _set(state, "result", result)
            _set(state, "concluido", True)

            st.success("Prova enviada e registrada. Respostas agora estão bloqueadas.")
            st.write(f"Acertos: **{result['acertos']}** / {result['total']}")
            st.write(f"Erros: **{result['erros']}**")
            st.write(f"Nota (0–10): **{result['nota_0_10']}**")

    with col2:
        # rascunho: salvar progresso sem bloquear
        if st.button("Salvar rascunho", key=f"{STAGE_ID}_draft"):
            # salva mesmo incompleto, mas sem concluir
            payload = {
                "stage_id": STAGE_ID,
                "submitted": False,
                "answers": {k: (int(v) if v is not None else None) for k, v in answers.items()},
                "concluido": False,
                "saved_at": _now_iso(),
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
            }
            save_json(path, payload)
            _set(state, "answers", payload["answers"])
            st.success("Rascunho salvo (ainda não enviado).")
