# blocks/problema/pergunta_norteadora.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "problema_pergunta_norteadora"


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


# Pergunta fixa (não editável pelo aluno)
PERGUNTA_NORTEADORA = (
    "As condições térmicas do ambiente escolhido favorecem o equilíbrio térmico "
    "entre o corpo humano e o meio, segundo os princípios da Termodinâmica?"
)

# Sugestões (apenas referência)
OUTRAS_POSSIBILIDADES = [
    "Quais mecanismos de transferência de calor dominam neste ambiente?",
    "Como o movimento do ar influencia o conforto térmico percebido?",
]


def render(ctx: Dict) -> None:
    # Contexto
    aluno = (ctx.get("aluno") or "Aluno").strip()
    grupo_id = (ctx.get("grupo_id") or "").strip()
    grupo_nome = (ctx.get("grupo_nome") or "").strip()

    if grupo_id and grupo_nome:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id} ({grupo_nome})")
    elif grupo_id:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id}")

    # Arquivo por aluno em data/problema
    path = _problema_path(aluno)

    # Carrega o "arquivo-container" do aluno
    root = load_json(path) or {}

    # Garante estrutura e metadados mínimos no container
    root.setdefault("aluno", aluno)
    if grupo_id:
        root.setdefault("grupo_id", grupo_id)
    if grupo_nome:
        root.setdefault("grupo_nome", grupo_nome)
    root.setdefault("stages", {})  # cada etapa fica identificada por stage_id

    # Dados já salvos especificamente deste stage
    data = root["stages"].get(STAGE_ID, {})

    # ---------------------------------------------------------------------
    # Introdução
    # ---------------------------------------------------------------------
    st.markdown(
        """
        <div style="text-align: justify;">
            A <strong>pergunta norteadora</strong> define o foco do projeto.
            Ela deve ser respondível com observações, dados e conceitos da disciplina,
            sem antecipar soluções.
            <br><br>
            Nesta etapa, a pergunta principal já está definida. Ainda assim,
            você deverá <strong>formular sua própria versão</strong> para refletir
            sobre o que exatamente será investigado.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---------------------------------------------------------------------
    # Pergunta norteadora fixa
    # ---------------------------------------------------------------------
    st.write("### Pergunta norteadora (referência fixa)")

    st.markdown(
        f"""
        <div style="
            text-align: justify;
            font-size: 1.2rem;
            line-height: 1.6;
            padding: 1rem;
            border-left: 4px solid #22c55e;
            background-color: rgba(34, 197, 94, 0.12);
            border-radius: 6px;
        ">
            <strong>{PERGUNTA_NORTEADORA}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------------------
    # Outras possibilidades (referência)
    # ---------------------------------------------------------------------
    with st.expander("Outras possibilidades (apenas referência)", expanded=False):
        st.markdown(
            "<div style='text-align: justify;'>"
            "Estas variações são exemplos alinhados à disciplina. "
            "<strong>Elas não substituem</strong> a pergunta norteadora oficial."
            "</div>",
            unsafe_allow_html=True,
        )
        for p in OUTRAS_POSSIBILIDADES:
            st.write(f"- {p}")

    st.markdown("---")

    # ---------------------------------------------------------------------
    # Reflexão do aluno
    # ---------------------------------------------------------------------
    st.write("### Sua formulação da pergunta central")

    st.markdown(
        """
        <div style="text-align: justify; margin-bottom: 4px;">
            <strong>Como você reformularia a pergunta acima com suas próprias palavras?</strong>
        </div>

        <div style="
            background-color: #1f2937;
            border-left: 4px solid #3b82f6;
            padding: 10px 12px;
            margin-top: 4px;
            margin-bottom: 10px;
            font-size: 0.95rem;
            color: #e5e7eb;
        ">
            <strong>Orientações:</strong>
            <ul style="margin-top: 6px;">
                <li>Mantenha o foco no ambiente escolhido.</li>
                <li>Não proponha soluções.</li>
                <li>Escreva uma pergunta que possa ser respondida com observações e dados.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pergunta_aluno = st.text_area(
        "Escreva sua versão da pergunta central (1–2 frases):",
        value=data.get("pergunta_aluno", ""),
        height=120,
        key=f"{STAGE_ID}_pergunta_aluno",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            payload = {
                "stage_id": STAGE_ID,
                "saved_at": _now_iso(),
                "pergunta_norteadora": PERGUNTA_NORTEADORA,
                "pergunta_aluno": pergunta_aluno.strip(),
                "confirmado": True,
                # metadados úteis
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
            }

            root["stages"][STAGE_ID] = payload
            root["updated_at"] = _now_iso()

            save_json(path, root)
            st.success("Pergunta norteadora registrada em data/problema para o aluno.")
