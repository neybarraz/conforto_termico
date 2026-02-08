# blocks/investigacao/Grandezas_Fisicas_Medidas.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
import re

import streamlit as st

from storage.io_csv import load_json, save_json


# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
STAGE_ID = "investigacao_grandezas_fisicas_medidas"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVESTIGACAO_DIR = PROJECT_ROOT / "data" / "investigacao"


# -----------------------------------------------------------------------------
# CONTEXTO / UTIL
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class StageContext:
    stage_id: str
    container_path: Path
    root: Dict[str, Any]
    saved_stage: Dict[str, Any]
    state: Dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_filename(name: str) -> str:
    if not isinstance(name, str):
        name = str(name)
    name = name.strip()
    if not name:
        return "anon"
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return name.lower()


def get_aluno_from_ctx(ctx: Dict[str, Any]) -> str:
    if not isinstance(ctx, dict):
        return "anon"
    return (
        ctx.get("aluno")
        or ctx.get("aluno_nome")
        or ctx.get("nome")
        or ctx.get("student")
        or "anon"
    )


def investigacao_path(ctx: Dict[str, Any]) -> Path:
    aluno = safe_filename(get_aluno_from_ctx(ctx))
    INVESTIGACAO_DIR.mkdir(parents=True, exist_ok=True)
    return INVESTIGACAO_DIR / f"{aluno}_investigacao.json"


def ensure_root_schema(root: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(root, dict):
        root = {}

    root.setdefault("aluno", get_aluno_from_ctx(ctx))

    if isinstance(ctx, dict):
        if "grupo_id" in ctx:
            root.setdefault("grupo_id", ctx.get("grupo_id"))
        if "grupo_nome" in ctx:
            root.setdefault("grupo_nome", ctx.get("grupo_nome"))

    if not isinstance(root.get("stages"), dict):
        root["stages"] = {}

    root.setdefault("created_at", now_iso())
    root["updated_at"] = now_iso()
    return root


def ctx_get_state() -> Dict[str, Any]:
    """
    Usa um namespace exclusivo no session_state para esta etapa.
    """
    key = f"__pbl_state__{STAGE_ID}"
    if key not in st.session_state:
        st.session_state[key] = {}
    return st.session_state[key]


def hydrate_state_from_saved(state: Dict[str, Any], saved: Dict[str, Any]) -> None:
    if not isinstance(saved, dict):
        return
    for k, v in saved.items():
        if k not in state:
            state[k] = v


def save_stage_overwrite(container_path: Path, ctx: Dict[str, Any], stage_id: str, stage_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Salva no mesmo padrão:
      root["stages"][stage_id] = stage_data + metadados
    """
    root_latest = load_json(container_path) or {}
    root_latest = ensure_root_schema(root_latest, ctx)

    if not isinstance(root_latest.get("stages"), dict):
        root_latest["stages"] = {}

    stage_clean = dict(stage_data)
    stage_clean["stage_id"] = stage_id
    stage_clean["saved_at"] = now_iso()

    root_latest["stages"][stage_id] = stage_clean
    root_latest["updated_at"] = now_iso()

    save_json(container_path, root_latest)
    return stage_clean


def build_context(ctx: Dict[str, Any]) -> StageContext:
    container_path = investigacao_path(ctx)
    root = load_json(container_path) or {}
    root = ensure_root_schema(root, ctx)

    saved_stage = root["stages"].get(STAGE_ID, {}) if isinstance(root.get("stages"), dict) else {}
    state = ctx_get_state()
    hydrate_state_from_saved(state, saved_stage if isinstance(saved_stage, dict) else {})

    # defaults mínimos desta etapa
    state.setdefault("grandezas_detalhes", {})

    return StageContext(
        stage_id=STAGE_ID,
        container_path=container_path,
        root=root,
        saved_stage=saved_stage if isinstance(saved_stage, dict) else {},
        state=state,
    )


# -----------------------------------------------------------------------------
# UI: GRANDEZAS
# -----------------------------------------------------------------------------
def render_grandezas(stage: StageContext) -> None:
    st.write(
        "Para investigar o problema do conforto térmico, devem ser medidas algumas "
        "grandezas físicas listadas abaixo. Para cada uma, indique o instrumento "
        "utilizado e o tempo de espera necessário para obter uma medida confiável."
    )


    detalhes = stage.state.get("grandezas_detalhes", {})
    if not isinstance(detalhes, dict):
        detalhes = {}

    grandezas = [
        "Temperatura do ar (Ta)",
        "Temperatura das superfícies (Ts)",
        "Umidade relativa do ar (UR)",
        "Ventilação do ambiente",
    ]
    tempos_opcoes = ["Instantâneo", "90 s"]

    for titulo in grandezas:
        key_base = safe_filename(titulo)
        if titulo not in detalhes or not isinstance(detalhes.get(titulo), dict):
            detalhes[titulo] = {}

        st.markdown(f"**{titulo}**")

        c1, c2 = st.columns([1, 5], vertical_alignment="center")
        with c1:
            st.write("Instrumento:")
        with c2:
            instrumento = st.text_input(
                "Instrumento",
                value=str(detalhes[titulo].get("instrumento", "") or ""),
                label_visibility="collapsed",
                key=f"{STAGE_ID}_inst_{key_base}",
            )

        c1, c2 = st.columns([2, 3], vertical_alignment="center")
        with c1:
            st.write("Tempo de espera:")
        with c2:
            atual = str(detalhes[titulo].get("tempo_espera", tempos_opcoes[0]) or tempos_opcoes[0])
            idx = tempos_opcoes.index(atual) if atual in tempos_opcoes else 0
            tempo = st.radio(
                "Tempo de espera",
                options=tempos_opcoes,
                index=idx,
                horizontal=True,
                label_visibility="collapsed",
                key=f"{STAGE_ID}_tempo_{key_base}",
            )

        detalhes[titulo] = {"instrumento": instrumento, "tempo_espera": tempo}
        st.write("")

    stage.state["grandezas_detalhes"] = detalhes


def save(stage: StageContext, ctx: Dict[str, Any]) -> None:
    payload = {"grandezas_detalhes": stage.state.get("grandezas_detalhes", {})}
    save_stage_overwrite(stage.container_path, ctx, stage.stage_id, payload)


# -----------------------------------------------------------------------------
# ENTRYPOINT
# -----------------------------------------------------------------------------
def render(ctx: Dict[str, Any]) -> None:
    stage = build_context(ctx)
    render_grandezas(stage)
    if st.button("Salvar", type="primary", key=f"{STAGE_ID}_salvar"):
        save(stage, ctx)
        st.success("Salvo no arquivo de investigação (somente esta etapa).")
