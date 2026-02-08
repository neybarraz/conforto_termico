# blocks/problema/diagnostico_inicial.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "problema_diagnostico_inicial"

LIKERT_OPCOES = [
    "1 — Não sei / nunca estudei",
    "2 — Sei muito pouco",
    "3 — Sei o básico",
    "4 — Sei bem",
    "5 — Sei muito bem / consigo explicar",
]

# Questões conceituais típicas (objetivas)
QUESTOES_OBJETIVAS = [
    {
        "id": "q1_temp_calor",
        "pergunta": "1) Qual alternativa melhor descreve a diferença entre temperatura e calor?",
        "opcoes": [
            "Temperatura é energia em trânsito; calor é o estado térmico do corpo.",
            "Temperatura mede o estado térmico; calor é energia transferida por diferença de temperatura.",
            "Temperatura e calor são a mesma coisa; só mudam as unidades.",
            "Calor é medido em °C; temperatura é medida em joule.",
        ],
        "correta": 1,
    },
    {
        "id": "q2_equilibrio",
        "pergunta": "2) Quando dois corpos atingem equilíbrio térmico, o que necessariamente é verdadeiro?",
        "opcoes": [
            "Eles ficam com a mesma quantidade de calor.",
            "Eles ficam com a mesma temperatura e não há fluxo líquido de calor entre eles.",
            "Eles ficam com a mesma massa.",
            "Eles param de trocar energia com o ambiente.",
        ],
        "correta": 1,
    },
    {
        "id": "q3_conducao",
        "pergunta": "3) Condução de calor ocorre principalmente quando:",
        "opcoes": [
            "Há emissão de ondas eletromagnéticas.",
            "Há contato físico e transferência por colisões microscópicas.",
            "O fluido se movimenta carregando energia térmica.",
            "Ocorre apenas no vácuo.",
        ],
        "correta": 1,
    },
    {
        "id": "q4_conveccao",
        "pergunta": "4) Convecção de calor está mais associada a:",
        "opcoes": [
            "Movimento de um fluido transportando energia térmica.",
            "Contato direto entre sólidos.",
            "Troca por radiação infravermelha sem meio material.",
            "Mudança de fase sem variação de temperatura.",
        ],
        "correta": 0,
    },
    {
        "id": "q5_radiacao",
        "pergunta": "5) Radiação térmica é:",
        "opcoes": [
            "Transferência de calor que depende do movimento do ar.",
            "Transferência de energia por ondas eletromagnéticas, podendo ocorrer no vácuo.",
            "Transferência de energia apenas por contato.",
            "O mesmo que convecção.",
        ],
        "correta": 1,
    },
    {
        "id": "q6_ar_fluido",
        "pergunta": "6) No conforto térmico, por que o ar pode ser tratado como um fluido térmico importante?",
        "opcoes": [
            "Porque o ar é sólido e conduz calor muito bem.",
            "Porque o ar pode se mover (vento/correntes), afetando trocas térmicas por convecção.",
            "Porque o ar elimina toda radiação térmica.",
            "Porque a temperatura do ar nunca muda.",
        ],
        "correta": 1,
    },
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_filename(name: str) -> str:
    """
    Gera um nome de arquivo estável e seguro a partir do nome do aluno.
    - remove espaços extras
    - troca espaços por underscore
    - remove caracteres não seguros
    """
    name = (name or "Aluno").strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_\-]", "", name)
    return name or "Aluno"


def _problema_path(aluno: str) -> Path:
    # salva em data/problema/problema_<aluno>.json
    base = Path("data") / "problema"
    base.mkdir(parents=True, exist_ok=True)
    fname = f"problema_{_safe_filename(aluno)}.json"
    return base / fname


def render(ctx: Dict) -> None:
    # Mostra contexto (não depende de sidebar)
    aluno = (ctx.get("aluno") or "Aluno").strip()
    grupo_id = (ctx.get("grupo_id") or "").strip()
    grupo_nome = (ctx.get("grupo_nome") or "").strip()

    if grupo_id and grupo_nome:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id} ({grupo_nome})")
    elif grupo_id:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id}")

    # Caminho por aluno em data/problema (container único do aluno)
    path = _problema_path(aluno)

    root = load_json(path) or {}
    root.setdefault("aluno", aluno)
    if grupo_id:
        root.setdefault("grupo_id", grupo_id)
    if grupo_nome:
        root.setdefault("grupo_nome", grupo_nome)
    root.setdefault("stages", {})

    # Dados já salvos especificamente deste stage (se existir)
    data = root["stages"].get(STAGE_ID, {})
    if not isinstance(data, dict):
        data = {}

    st.markdown(
        """
        <div style="text-align: justify;">
            <strong>Diagnóstico inicial (pré-teste / autoavaliação)</strong><br><br>
            Objetivo: identificar conhecimentos prévios e possíveis lacunas conceituais.
            Este diagnóstico <strong>não vale nota</strong>. Ele serve para você perceber o que já sabe
            e o que precisa estudar antes de avançar nas próximas fases do PBL.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Parte A — Autoavaliação (Likert)
    # -------------------------------------------------------------------------
    st.write("### Parte A — Autoavaliação (não vale nota)")

    st.markdown(
        """
        <div style="text-align: justify;">
            Marque o seu nível de segurança em cada tópico. Seja honesto: o objetivo é orientar o estudo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    saved_likert = data.get("likert", {}) if isinstance(data.get("likert", {}), dict) else {}

    def _idx_likert(saved_value: str) -> int:
        try:
            return LIKERT_OPCOES.index(saved_value)
        except Exception:
            return 0

    colA, colB = st.columns(2)

    with colA:
        l1 = st.selectbox(
            "Temperatura × calor",
            LIKERT_OPCOES,
            index=_idx_likert(saved_likert.get("l1_temp_calor", "")),
            key=f"{STAGE_ID}_l1",
            help="O quanto você sabe diferenciar temperatura e calor?",
        )
        l2 = st.selectbox(
            "Equilíbrio térmico",
            LIKERT_OPCOES,
            index=_idx_likert(saved_likert.get("l2_equilibrio", "")),
            key=f"{STAGE_ID}_l2",
        )
        l3 = st.selectbox(
            "Condução",
            LIKERT_OPCOES,
            index=_idx_likert(saved_likert.get("l3_conducao", "")),
            key=f"{STAGE_ID}_l3",
        )

    with colB:
        l4 = st.selectbox(
            "Convecção",
            LIKERT_OPCOES,
            index=_idx_likert(saved_likert.get("l4_conveccao", "")),
            key=f"{STAGE_ID}_l4",
        )
        l5 = st.selectbox(
            "Radiação",
            LIKERT_OPCOES,
            index=_idx_likert(saved_likert.get("l5_radiacao", "")),
            key=f"{STAGE_ID}_l5",
        )
        l6 = st.selectbox(
            "Ar como fluido térmico",
            LIKERT_OPCOES,
            index=_idx_likert(saved_likert.get("l6_ar_fluido", "")),
            key=f"{STAGE_ID}_l6",
        )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Parte B — Questões objetivas
    # -------------------------------------------------------------------------
    st.write("### Parte B — Questões objetivas (não vale nota)")

    st.markdown(
        """
        <div style="text-align: justify;">
            Responda as questões abaixo. Você pode errar — o objetivo é mapear o seu ponto de partida.
        </div>
        """,
        unsafe_allow_html=True,
    )

    respostas_salvas_obj = data.get("objetivas", {}) if isinstance(data.get("objetivas", {}), dict) else {}

    respostas_obj = {}
    acertos = 0
    respondidas = 0

    for q in QUESTOES_OBJETIVAS:
        valor_salvo = respostas_salvas_obj.get(q["id"])
        default_index = 0 if valor_salvo is None else int(valor_salvo)

        escolha = st.radio(
            q["pergunta"],
            q["opcoes"],
            index=default_index,
            key=f"{STAGE_ID}_{q['id']}",
        )

        idx = q["opcoes"].index(escolha)
        respostas_obj[q["id"]] = idx
        respondidas += 1
        if idx == q["correta"]:
            acertos += 1

        st.markdown("<div style='margin-top: 0.6rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Parte C — Reflexão curta (metacognição mínima)
    # -------------------------------------------------------------------------
    st.write("### Parte C — Reconheça seu ponto de partida")

    reflexao = st.text_area(
        "Em 2–4 linhas, escreva: (i) o que você já sabe com segurança e (ii) o que você precisa estudar.",
        value=(data.get("reflexao") or "") if isinstance(data, dict) else "",
        height=120,
        key=f"{STAGE_ID}_reflexao",
    )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Salvar + critério de conclusão
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="text-align: justify;">
            <strong>Critério de conclusão:</strong> diagnóstico respondido integralmente e registro do que você sabe e do que precisa estudar.
        </div>
        """,
        unsafe_allow_html=True,
    )

    msg_box = st.empty()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            concluido = True
            avisos = []

            if not reflexao.strip():
                concluido = False
                avisos.append("Escreva a reflexão curta (Parte C).")

            payload = {
                "stage_id": STAGE_ID,
                "saved_at": _now_iso(),
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
                "likert": {
                    "l1_temp_calor": l1,
                    "l2_equilibrio": l2,
                    "l3_conducao": l3,
                    "l4_conveccao": l4,
                    "l5_radiacao": l5,
                    "l6_ar_fluido": l6,
                },
                "objetivas": respostas_obj,
                "resultado": {
                    "respondidas": respondidas,
                    "acertos": acertos,
                    "percentual": round((acertos / respondidas) * 100, 1) if respondidas else 0.0,
                },
                "reflexao": reflexao.strip(),
                "concluido": concluido,
            }

            # grava no container do aluno, identificado por stages[STAGE_ID]
            root["stages"][STAGE_ID] = payload
            root["updated_at"] = _now_iso()
            save_json(path, root)

            if avisos:
                msg_box.success("Diagnóstico salvo (arquivo do aluno).")
                msg_box.warning("Faltam itens para concluir totalmente esta etapa:")
                for a in avisos:
                    msg_box.write(f"- {a}")
            else:
                msg_box.success("Diagnóstico salvo e concluído (arquivo do aluno). Use este resultado para guiar seu estudo.")

    with col2:
        st.markdown(
            f"""
            <div style="text-align: justify;">
                <strong>Resumo (não vale nota):</strong><br>
                Questões objetivas: <strong>{acertos}/{respondidas}</strong> acertos.
            </div>
            """,
            unsafe_allow_html=True,
        )
