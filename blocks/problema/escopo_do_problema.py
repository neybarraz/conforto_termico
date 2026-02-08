# blocks/problema/escopo_ambiente.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "problema_escopo_ambiente"


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
    # VÍDEO(S) (curto) — introdução ao recorte do sistema em estudo
    # -------------------------------------------------------------------------
    st.video("https://www.youtube.com/watch?v=ngQWVEnxMQw")

    # -------------------------------------------------------------------------
    # TEXTO (justificado) — por que delimitar escopo antes de investigar
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="text-align: justify;">
        <p style="margin-bottom: 0.6em;">
        Em Física, investigar um fenômeno exige definir com clareza
        <strong>qual sistema</strong> está sendo analisado.
        Nesta etapa, o objetivo é delimitar o escopo do estudo de conforto térmico
        para evitar ambiguidade e garantir que as observações e medições façam sentido
        dentro de um recorte bem definido.
        </p>

        <p style="margin-bottom: 0.6em;">
        Você deve especificar:
        (i) <strong>o ambiente</strong> (o lugar exato),
        (ii) <strong>o período do dia</strong> e
        (iii) <strong>as condições típicas</strong> em que o desconforto ocorre.
        Ao mesmo tempo, é importante registrar o que <strong>não</strong> faz parte
        do escopo: este projeto não trata conforto acústico ou lumínico,
        não projeta sistemas de climatização e não avalia aspectos médicos ou fisiológicos.
        </p>

        <p style="margin-bottom: 0;">
        Do ponto de vista da Física da disciplina, o ar será tratado como um
        <strong>fluido em repouso ou em movimento</strong>, a temperatura será
        interpretada como <strong>estado térmico do sistema</strong>, e as trocas
        de energia serão discutidas qualitativamente a partir dos princípios da
        Termodinâmica (sem necessidade de fórmulas nesta etapa).
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # ATIVIDADE — campos estruturados (evidência)
    # -------------------------------------------------------------------------
    st.write("### Atividade — defina o sistema em estudo")

    ambiente_especifico = st.text_input(
        "Ambiente específico (ex.: Sala B12 – Bloco A)",
        value=data.get("ambiente_especifico", ""),
        key=f"{STAGE_ID}_ambiente_especifico",
    )

    turno_opts = ["Manhã", "Tarde", "Noite"]
    saved_turno = (data.get("turno") or "Manhã").strip()
    idx_turno = turno_opts.index(saved_turno) if saved_turno in turno_opts else 0

    turno = st.radio(
        "Período do dia (turno)",
        options=turno_opts,
        index=idx_turno,
        horizontal=True,
        key=f"{STAGE_ID}_turno",
    )

    condicoes = st.text_area(
        "Condições típicas (descreva em 2–5 linhas: ocupação, janelas, ventilação, etc.)",
        value=data.get("condicoes", ""),
        height=130,
        key=f"{STAGE_ID}_condicoes",
    )

    # 2) Exclusões explícitas do escopo (checklist)
    st.markdown(
        """
        <div style="text-align: justify; margin-bottom: 4px;">
            <strong>Exclusões explícitas do escopo</strong> (marque para confirmar que você entendeu o que NÃO será analisado):
        </div>
        """,
        unsafe_allow_html=True,
    )

    exc_acustico_lum = st.checkbox(
        "Não tratar conforto acústico ou lumínico",
        value=bool(data.get("exc_acustico_lum", False)),
        key=f"{STAGE_ID}_exc_acustico_lum",
    )
    exc_climatizacao = st.checkbox(
        "Não projetar sistemas de climatização (não é projeto de engenharia)",
        value=bool(data.get("exc_climatizacao", False)),
        key=f"{STAGE_ID}_exc_climatizacao",
    )
    exc_medico = st.checkbox(
        "Não avaliar aspectos médicos ou fisiológicos",
        value=bool(data.get("exc_medico", False)),
        key=f"{STAGE_ID}_exc_medico",
    )

    # 3) Critério de conclusão (visível para o aluno)
    st.markdown(
        """
        <div style="text-align: justify;">
            <strong>Critério de conclusão da etapa</strong>
            <ul style="margin-top: 6px;">
                <li>O sistema físico deve estar claramente delimitado (ambiente específico + turno + condições).</li>
                <li>Não pode haver ambiguidade sobre o que será analisado.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # SALVAR + feedback mínimo (sem bloquear)
    # -------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            payload = {
                "stage_id": STAGE_ID,
                "saved_at": _now_iso(),
                "ambiente_especifico": ambiente_especifico.strip(),
                "turno": turno,
                "condicoes": condicoes.strip(),
                "exc_acustico_lum": exc_acustico_lum,
                "exc_climatizacao": exc_climatizacao,
                "exc_medico": exc_medico,
                # metadados
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
            }

            # grava dentro do container do aluno, identificado por stages[STAGE_ID]
            root["stages"][STAGE_ID] = payload
            root["updated_at"] = _now_iso()

            save_json(path, root)

            # feedback leve de completude (não bloqueia)
            avisos = []
            if not ambiente_especifico.strip():
                avisos.append("Preencha o ambiente específico (ex.: Sala B12 – Bloco A).")
            if not condicoes.strip():
                avisos.append("Descreva as condições típicas (2–5 linhas).")
            if not (exc_acustico_lum and exc_climatizacao and exc_medico):
                avisos.append("Marque as exclusões do escopo para confirmar entendimento.")

            if avisos:
                st.success("Salvo em data/problema para o aluno.")
                st.warning("Faltam itens para concluir totalmente esta etapa:")
                for a in avisos:
                    st.write(f"- {a}")
            else:
                st.success("Etapa salva e concluída: escopo claramente delimitado.")

    with col2:
        # Debug opcional (pode comentar depois)
        # st.caption(f"Arquivo do aluno: {path}")
        pass
