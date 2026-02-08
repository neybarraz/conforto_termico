# blocks/investigacao/01_coleta_de_dados_tabelas.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import math
import re

import streamlit as st

from storage.io_csv import load_json, save_json


# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
STAGE_ID = "investigacao_coleta_de_dados"

PONTOS_TA_DEF: List[Dict[str, str]] = [
    {"id": "NO", "label": "NO"},
    {"id": "NE", "label": "NE"},
    {"id": "C", "label": "C"},
    {"id": "SO", "label": "SO"},
    {"id": "SE", "label": "SE"},
]
PONTOS_TS_DEF: List[Dict[str, str]] = [
    {"id": "N1", "label": "N1"},
    {"id": "N2", "label": "N2"},
    {"id": "L1", "label": "L1"},
    {"id": "L2", "label": "L2"},
    {"id": "O1", "label": "O1"},
    {"id": "O2", "label": "O2"},
    {"id": "S1", "label": "S1"},
    {"id": "S2", "label": "S2"},
]

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


# -----------------------------------------------------------------------------
# DADOS / NORMALIZAÇÃO
# -----------------------------------------------------------------------------
def safe_float(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(",", ".")
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def _is_nan(x: Any) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False


def _index_by_id(rows: List[Dict[str, Any]], id_key: str = "id") -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        pid = str(r.get(id_key, "") or "").strip()
        if pid:
            out[pid] = r
    return out


def _build_fixed_rows_ta(existing_rows: Any) -> List[Dict[str, Any]]:
    src_rows = existing_rows if isinstance(existing_rows, list) else []
    by_id = _index_by_id(src_rows, "id")
    out: List[Dict[str, Any]] = []
    for p in PONTOS_TA_DEF:
        pid = p["id"]
        base = {"id": pid, "Ta_C": None, "UR_pct": None, "v_ms": None}
        if pid in by_id:
            base["Ta_C"] = safe_float(by_id[pid].get("Ta_C"))
            base["UR_pct"] = safe_float(by_id[pid].get("UR_pct"))
            base["v_ms"] = safe_float(by_id[pid].get("v_ms"))
        out.append(base)
    return out


def _build_fixed_rows_ts(existing_rows: Any) -> List[Dict[str, Any]]:
    src_rows = existing_rows if isinstance(existing_rows, list) else []
    by_id = _index_by_id(src_rows, "id")
    out: List[Dict[str, Any]] = []
    for p in PONTOS_TS_DEF:
        pid = p["id"]
        base = {"id": pid, "Ts_C": None}
        if pid in by_id:
            base["Ts_C"] = safe_float(by_id[pid].get("Ts_C"))
        out.append(base)
    return out


def _normalize_existing_coleta(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return {
            "horario": str(raw.get("horario", "") or "").strip(),
            "ta_rows": raw.get("ta_rows", []) if isinstance(raw.get("ta_rows"), list) else [],
            "ts_rows": raw.get("ts_rows", []) if isinstance(raw.get("ts_rows"), list) else [],
        }
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and ("ta_rows" in item or "ts_rows" in item):
                return {
                    "horario": str(item.get("horario", "") or "").strip(),
                    "ta_rows": item.get("ta_rows", []) if isinstance(item.get("ta_rows"), list) else [],
                    "ts_rows": item.get("ts_rows", []) if isinstance(item.get("ts_rows"), list) else [],
                }
    return {"horario": "", "ta_rows": [], "ts_rows": []}


def _find_hora_in_root(root: Dict[str, Any]) -> str:
    stages = root.get("stages")
    if not isinstance(stages, dict):
        return ""
    for _, stg in stages.items():
        if not isinstance(stg, dict):
            continue
        cond = stg.get("condicoes_coleta")
        if isinstance(cond, dict):
            h = str(cond.get("hora", "") or "").strip()
            if h:
                return h
    return ""


def _coleta_ok(coleta: Dict[str, Any]) -> bool:
    h = str(coleta.get("horario", "") or "").strip()
    if not h:
        return False

    for r in (coleta.get("ta_rows", []) or []):
        if not isinstance(r, dict):
            continue
        for k in ("Ta_C", "UR_pct", "v_ms"):
            x = r.get(k)
            if isinstance(x, (int, float)) and not _is_nan(x):
                return True

    for r in (coleta.get("ts_rows", []) or []):
        if not isinstance(r, dict):
            continue
        x = r.get("Ts_C")
        if isinstance(x, (int, float)) and not _is_nan(x):
            return True

    return False


# -----------------------------------------------------------------------------
# CONTEXTO
# -----------------------------------------------------------------------------
def build_context(ctx: Dict[str, Any]) -> StageContext:
    container_path = investigacao_path(ctx)
    root = load_json(container_path) or {}
    root = ensure_root_schema(root, ctx)

    saved_stage = root["stages"].get(STAGE_ID, {}) if isinstance(root.get("stages"), dict) else {}
    state = ctx_get_state()
    hydrate_state_from_saved(state, saved_stage if isinstance(saved_stage, dict) else {})

    state.setdefault("rodadas_medicoes", [])

    return StageContext(
        stage_id=STAGE_ID,
        container_path=container_path,
        root=root,
        saved_stage=saved_stage if isinstance(saved_stage, dict) else {},
        state=state,
    )


# -----------------------------------------------------------------------------
# ENTRYPOINT (sem st.form, sem moldura)
# -----------------------------------------------------------------------------
def render(ctx: Dict[str, Any]) -> None:
    stage = build_context(ctx)

    # Horário: tenta puxar de outra etapa já preenchida
    hora_root = _find_hora_in_root(stage.root)

    # Carrega 1 rodada existente (se houver)
    coleta = _normalize_existing_coleta(stage.state.get("rodadas_medicoes", []))

    # Se já existe hora em outra etapa, usa ela
    if hora_root:
        coleta["horario"] = hora_root

    # Linhas fixas
    ta_init = _build_fixed_rows_ta(coleta.get("ta_rows", []))
    ts_init = _build_fixed_rows_ts(coleta.get("ts_rows", []))

    # Guarda no state (para persistir visualmente após rerun)
    stage.state["rodadas_medicoes"] = [
        {"horario": coleta.get("horario", ""), "ta_rows": ta_init, "ts_rows": ts_init}
    ]

    if coleta.get("horario"):
        st.markdown(f"**Horário da coleta:** {coleta['horario']}")
    else:
        st.warning("Horário da coleta não encontrado. Preencha o horário na etapa de condições da coleta.")

    st.markdown("**Tabela Ta (ar)**")
    ta_rows_edit = st.data_editor(
        ta_init,
        use_container_width=True,
        num_rows="fixed",
        key=f"{STAGE_ID}_ta_editor",
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Ta_C": st.column_config.NumberColumn("Ta (°C)", width="small"),
            "UR_pct": st.column_config.NumberColumn("UR (%)", width="small"),
            "v_ms": st.column_config.NumberColumn("v (m/s)", width="small"),
        },
    )

    st.markdown("**Tabela Ts (superfície)**")
    ts_rows_edit = st.data_editor(
        ts_init,
        use_container_width=True,
        num_rows="fixed",
        key=f"{STAGE_ID}_ts_editor",
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Ts_C": st.column_config.NumberColumn("Ts (°C)", width="small"),
        },
    )

    salvar = st.button("Salvar", type="primary", key=f"{STAGE_ID}_salvar")

    if salvar:
        coleta_final = {
            "horario": str(coleta.get("horario", "") or "").strip(),
            "ta_rows": _build_fixed_rows_ta(ta_rows_edit),
            "ts_rows": _build_fixed_rows_ts(ts_rows_edit),
        }

        # Opcional: se quiser impedir salvar totalmente vazio, descomente:
        # if not _coleta_ok(coleta_final):
        #     st.warning("Nada para salvar (sem horário ou sem valores numéricos).")
        #     return

        stage.state["rodadas_medicoes"] = [coleta_final]
        payload = {"rodadas_medicoes": stage.state.get("rodadas_medicoes", [])}
        save_stage_overwrite(stage.container_path, ctx, stage.stage_id, payload)

        st.success("Salvo no arquivo de investigação.")
