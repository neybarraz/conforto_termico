# blocks/problema/criterios_rubrica.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "problema_criterios_rubrica"


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
    # ---------------------------------------------------------------------
    # Contexto
    # ---------------------------------------------------------------------
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
    # Como será a avaliação (MARKDOWN PURO)
    # ---------------------------------------------------------------------
    st.write("### Como será a avaliação")

    st.markdown(
        """
Nesta disciplina, o preenchimento do aplicativo funciona como **evidência do seu raciocínio individual**.  
Mesmo que a coleta de dados possa ser feita em grupo, cada aluno deve registrar sua própria visão e
justificativas nas etapas do app (**Problema → Investigação → Solução**).

A progressão por etapa será acompanhada pelo professor usando três níveis:

- **Auxiliar**: abaixo do mínimo esperado (precisa melhorar antes de avançar).
- **Técnico**: nível mínimo aceitável para avançar (nota entre **6,0** e **7,5**).
- **Engenheiro**: acima do mínimo, com domínio claro (acima de **7,5**, podendo chegar a **10**).

**Recuperação / Repetição**

- **Prova**: possui regra de recuperação (avaliação recuperativa).
- **Entregas parciais**: podem ser refeitas quantas vezes for necessário até atingir, no mínimo, o nível **Técnico**.
- **Memorial técnico** e **Seminário**: não podem ser repetidos, pois envolvem apresentação em grupo e o memorial
  consolida as conclusões das etapas.

**Composição da nota no SIGAA (UFFS)**

- **Nota 1 (0–10)**: Prova (individual).
- **Nota 2 (0–10)**: média das outras notas  
  (entregas parciais + memorial técnico + seminário).
"""
    )

    st.markdown("---")

    # ---------------------------------------------------------------------
    # Níveis de desempenho (quadro de referência visual)
    # ---------------------------------------------------------------------
    st.write("### Níveis de desempenho (referência rápida)")

    st.markdown(
        """
<div style="
    background-color: #1f2937;
    border-left: 4px solid #3b82f6;
    padding: 10px 12px;
    margin-top: 4px;
    margin-bottom: 10px;
    font-size: 0.95rem;
    color: #e5e7eb;
">
<strong>O que diferencia os níveis</strong>

- **Auxiliar**: respostas vagas ou incompletas; pouco vínculo com evidências; justificativas fracas.
- **Técnico**: respostas claras; escopo bem definido; justificativas coerentes; evidências mínimas suficientes.
- **Engenheiro**: precisão e consistência; interpretações bem sustentadas; limites bem reconhecidos; bom encadeamento lógico.
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---------------------------------------------------------------------
    # Ciência do aluno
    # ---------------------------------------------------------------------
    st.write("### Ciência do aluno")

    st.markdown(
        """
Para avançar, registre que você está **ciente das regras de avaliação**, incluindo:

- os níveis **Auxiliar / Técnico / Engenheiro**;
- a possibilidade de **refazer entregas parciais** até atingir o nível Técnico;
- a existência de **recuperação na prova**;
- a impossibilidade de repetição do **memorial técnico** e do **seminário**.
"""
    )

    ciente = st.checkbox(
        "Li e estou ciente de como serei avaliado(a).",
        value=bool(data.get("ciente", False)),
        key=f"{STAGE_ID}_ciente",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            payload = {
                "stage_id": STAGE_ID,
                "saved_at": _now_iso(),
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
                "ciente": bool(ciente),
                "concluido": bool(ciente),
            }

            # grava dentro do container do aluno, identificado por stages[STAGE_ID]
            root["stages"][STAGE_ID] = payload
            root["updated_at"] = _now_iso()

            save_json(path, root)

            if ciente:
                st.success("Ciência registrada. Etapa concluída.")
            else:
                st.success("Salvo para o aluno.")
                st.warning("Para concluir esta etapa, marque o OK de ciência.")

    with col2:
        # espaço reservado (debug ou futuras ações)
        pass
