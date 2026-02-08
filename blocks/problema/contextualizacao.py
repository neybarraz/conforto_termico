# blocks/problema/contextualizacao.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "problema_definicao"


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
    # Contexto (não depende de sidebar)
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

    # Conteúdo introdutório
    st.video(
        "https://www.youtube.com/watch?v=mmesl7zwpJE&list=PL3ZQ5CpNulQl6jZYRSrpv_ODBAqQW7bw0&index=2"
    )

    st.markdown(
        """<div style='text-align: justify;'>
        Em diferentes ambientes do campus, como salas de aula, laboratórios e bibliotecas, 
        é comum surgirem queixas relacionadas a calor excessivo ou frio desconfortável. 
        Essas situações afetam diretamente a permanência das pessoas no ambiente, a 
        concentração durante as atividades e a necessidade de adaptações improvisadas, 
        como abrir janelas, ligar ventiladores ou ajustar o uso do ar-condicionado.
        <br><br>
        Do ponto de vista da Física, o conforto térmico não é apenas uma opinião subjetiva, 
        mas o resultado de trocas de energia térmica entre o corpo humano, o ar do ambiente, 
        as superfícies ao redor e o movimento do ar. Reconhecer essas interações é o 
        primeiro passo para transformar uma percepção cotidiana em um problema físico 
        investigável.
        <br><br>
        </div>""",
        unsafe_allow_html=True,
    )

    st.video("https://www.youtube.com/watch?v=CKbc7PtbTzU")

    st.markdown(
        """<div style='text-align: justify;'>
        Nesta etapa, o objetivo não é propor soluções, nem realizar cálculos, mas 
        <strong>identificar e descrever claramente uma situação real de desconforto 
        térmico</strong>, delimitando o ambiente em que ela ocorre e justificando por que 
        essa situação pode ser analisada à luz da Física estudada na disciplina.
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.write("### Atividade")

    # Ambiente: menu "aberto" com seleção única
    options = [
        "Biblioteca",
        "Bloco A",
        "Corredor",
        "Ginásio",
        "Laboratório",
        "Sala de aula",
    ]
    saved_amb = (data.get("ambiente") or "").strip()
    idx = options.index(saved_amb) if saved_amb in options else 0

    ambiente = st.radio(
        "Escolha um ambiente do campus (marque apenas 1):",
        options=options,
        index=idx,
        key=f"{STAGE_ID}_ambiente",
    )

    st.markdown(
        """
        <div style="margin-bottom: 4px;">
            <strong>Quais sinais de desconforto térmico você já observou nesse ambiente?</strong>
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
                <li>O que ocorre no ambiente (calor excessivo ou frio desconfortável);</li>
                <li>Ao menos <strong>1 impacto observável</strong> (queda de concentração,
                    fadiga térmica, improdutividade ou adaptações como janelas, ventilador
                    ou ar-condicionado);</li>
                <li>Uma explicação intuitiva de como o ambiente afeta o corpo
                    (sensação térmica, circulação do ar, contato com superfícies).</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    texto = st.text_area(
        "Descreva o problema (5–8 linhas):",
        value=data.get("texto", ""),
        height=160,
        key=f"{STAGE_ID}_texto",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            payload = {
                # identificação do que foi salvo
                "stage_id": STAGE_ID,
                "saved_at": _now_iso(),
                "ambiente": ambiente,
                "texto": texto,
                # metadados úteis
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
            }

            # grava dentro do container do aluno, identificado por stages[STAGE_ID]
            root["stages"][STAGE_ID] = payload
            root["updated_at"] = _now_iso()

            save_json(path, root)
            st.success("Salvo em data/problema para o aluno.")

    # with col2:
    #     st.caption(f"Arquivo do aluno: {path}")
