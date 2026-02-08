# blocks/problema/objetivos.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "problema_objetivos"

OBJETIVOS_PROJETO = [
    "Analisar as condições térmicas de um ambiente real do campus.",
    "Identificar os principais mecanismos de transferência de calor envolvidos.",
    "Relacionar temperatura, movimento do ar e conforto térmico.",
    "Aplicar conceitos da Termodinâmica para interpretar dados experimentais.",
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

    # -------------------------------------------------------------------------
    # Texto fixo (objetivos)
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="text-align: justify;">
            <strong>Objetivos do projeto</strong><br><br>
            Os objetivos abaixo definem o que este projeto busca alcançar. Eles serão usados mais adiante
            como referência para autoavaliação e para a rubrica de avaliação. Nesta etapa, o objetivo é
            apenas <strong>ler e compreender</strong> o que será investigado.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top: 1.0rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<div style='text-align: justify;'>"
        "<ul>"
        + "".join([f"<li>{o}</li>" for o in OBJETIVOS_PROJETO])
        + "</ul>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Confirmação de leitura e compreensão (critério de conclusão)
    # -------------------------------------------------------------------------
    st.write("### Confirmação")

    st.markdown(
        """
        <div style="text-align: justify;">
            Para concluir esta etapa, confirme que você leu e compreendeu os objetivos do projeto.
        </div>
        """,
        unsafe_allow_html=True,
    )

    confirmo = st.checkbox(
        "Li e compreendi os objetivos do projeto.",
        value=bool(data.get("confirmo", False)),
        key=f"{STAGE_ID}_confirmo",
    )

    msg_box = st.empty()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            payload = {
                "stage_id": STAGE_ID,
                "saved_at": _now_iso(),
                "objetivos": OBJETIVOS_PROJETO,
                "confirmo": bool(confirmo),
                "concluido": bool(confirmo),
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
            }

            # grava dentro do container do aluno, identificado por stages[STAGE_ID]
            root["stages"][STAGE_ID] = payload
            root["updated_at"] = _now_iso()

            save_json(path, root)

            if confirmo:
                msg_box.success("Objetivos confirmados. Etapa concluída.")
            else:
                msg_box.success("Salvo.")
                msg_box.warning("Para concluir, marque a confirmação de leitura e compreensão.")

    # with col2:
    #     st.caption(f"Arquivo do aluno: {path}")
