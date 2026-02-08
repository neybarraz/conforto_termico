# blocks/investigacao/Contexto_da_Medicao.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import re

import streamlit as st

from storage.io_csv import load_json, save_json


# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
STAGE_ID = "investigacao_contexto_medicao"

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


def save_stage_overwrite(
    container_path: Path, ctx: Dict[str, Any], stage_id: str, stage_data: Dict[str, Any]
) -> Dict[str, Any]:
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

    saved_stage = (
        root["stages"].get(STAGE_ID, {}) if isinstance(root.get("stages"), dict) else {}
    )
    state = ctx_get_state()
    hydrate_state_from_saved(state, saved_stage if isinstance(saved_stage, dict) else {})

    # defaults mínimos desta etapa
    state.setdefault("ambiente_medicao", {"ambiente_id": ""})
    state.setdefault(
        "condicoes_coleta",
        {"hora": "", "ocupacao": "", "incidencia_solar": "", "condicao_externa": ""},
    )

    # NOVO: ventilação natural/mecânica e percepção térmica
    state.setdefault(
        "ventilacao_aberturas",
        {
            "janelas": "fechadas",
            "portas": "fechadas",
        },
    )
    state.setdefault(
        "ventilacao_mecanica",
        {
            "tipo": "ar condicionado",
            "estado": "desligado",
        },
    )
    state.setdefault(
        "percepcao_termica",
        {
            "sensacao": "confortável",
            "intensidade": 3,
            "descricao": "",
            "diferencas_regioes": "",
        },
    )

    return StageContext(
        stage_id=STAGE_ID,
        container_path=container_path,
        root=root,
        saved_stage=saved_stage if isinstance(saved_stage, dict) else {},
        state=state,
    )


# -----------------------------------------------------------------------------
# UI: CONTEXTO DA MEDIÇÃO (ambiente + condições + ventilação + percepção)
# -----------------------------------------------------------------------------
def _idx(options: List[str], current: str) -> int:
    try:
        return options.index(current)
    except Exception:
        return 0


def render_ambiente_medicao(stage: StageContext) -> None:
    st.markdown("**Em qual ambiente as medições estão sendo realizadas?**")

    ambiente = stage.state.get("ambiente_medicao", {})
    if not isinstance(ambiente, dict):
        ambiente = {}

    ambientes = [
        "Sala 405A",
        "Sala 302A",
        "Sala 212 Lab. 3",
        "Saguão da cantina",
        "Biblioteca",
        "Saguão do Bloco A",
    ]

    atual = str(ambiente.get("ambiente_id", ambientes[0]) or ambientes[0])
    idx = ambientes.index(atual) if atual in ambientes else 0

    ambiente_id = st.radio(
        "Ambiente",
        options=ambientes,
        index=idx,
        horizontal=True,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_ambiente_id",
    )

    stage.state["ambiente_medicao"] = {"ambiente_id": ambiente_id}


def render_condicoes_coleta(stage: StageContext) -> None:
    cond = stage.state.get("condicoes_coleta", {})
    if not isinstance(cond, dict):
        cond = {}

    horas = [f"{h:02d}:{m:02d}" for h in range(7, 23) for m in (0, 30)]
    ocupacoes = ["1 - 5 pessoas", "6 - 15 pessoas", "16 - 30 pessoas", "mais de 31 pessoas"]
    incidencias = ["Não observado", "Sem sol direto", "Sol direto na parte do ambiente", "Sol direto forte"]
    externas = ["Não observado", "Quente", "Ameno", "Frio", "Nublado", "Chuvoso"]

    st.markdown("**Em que horário as medições estão sendo realizadas?**")
    hora = st.radio(
        label="horario",
        options=horas,
        index=_idx(horas, str(cond.get("hora", "14:00") or "14:00")),
        horizontal=True,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_cond_hora",
    )

    st.markdown("**Quantas pessoas estão presentes no ambiente no momento da medição?**")
    ocupacao = st.radio(
        "Ocupação do ambiente",
        options=ocupacoes,
        index=_idx(ocupacoes, str(cond.get("ocupacao", ocupacoes[0]) or ocupacoes[0])),
        label_visibility="collapsed",
        key=f"{STAGE_ID}_cond_ocupacao",
    )

    st.markdown("**Há incidência de radiação solar direta no ambiente?**")
    incidencia = st.radio(
        "Incidência solar",
        options=incidencias,
        index=_idx(incidencias, str(cond.get("incidencia_solar", incidencias[0]) or incidencias[0])),
        label_visibility="collapsed",
        key=f"{STAGE_ID}_cond_sol",
    )

    st.markdown("**Como se apresentam as condições climáticas externas no momento da medição?**")
    externa = st.radio(
        "Condições externas",
        options=externas,
        index=_idx(externas, str(cond.get("condicao_externa", externas[0]) or externas[0])),
        horizontal=True,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_cond_clima",
    )

    stage.state["condicoes_coleta"] = {
        "hora": hora,
        "ocupacao": ocupacao,
        "incidencia_solar": incidencia,
        "condicao_externa": externa,
    }


def render_ventilacao(stage: StageContext) -> None:
    aberturas = stage.state.get("ventilacao_aberturas", {})
    if not isinstance(aberturas, dict):
        aberturas = {}

    mecanica = stage.state.get("ventilacao_mecanica", {})
    if not isinstance(mecanica, dict):
        mecanica = {}

    op_aberturas = ["fechadas", "abertas", "parcialmente abertas", "mistos"]
    op_tipo_mec = ["ar condicionado", "ventilador", "ventilador + ar-condicionado"]
    op_estado_mec = ["desligado", "ligado", "intermitente/variando"]

    st.markdown("**As janelas estão abertas?**")
    janelas = st.radio(
        "Janelas",
        options=op_aberturas,
        index=_idx(op_aberturas, str(aberturas.get("janelas", op_aberturas[0]) or op_aberturas[0])),
        horizontal=True,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_janelas",
    )

    st.markdown("**As portas estão fechadas?**")
    portas = st.radio(
        "Portas",
        options=op_aberturas,
        index=_idx(op_aberturas, str(aberturas.get("portas", op_aberturas[0]) or op_aberturas[0])),
        horizontal=True,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_portas",
    )

    st.markdown("**Qual é a ventilação mecânica?**")
    tipo = st.radio(
        "Tipo de ventilação mecânica",
        options=op_tipo_mec,
        index=_idx(op_tipo_mec, str(mecanica.get("tipo", op_tipo_mec[0]) or op_tipo_mec[0])),
        label_visibility="collapsed",
        key=f"{STAGE_ID}_mec_tipo",
    )

    st.markdown("**A ventilação mecânica está ligada?**")
    estado = st.radio(
        "Estado da ventilação mecânica",
        options=op_estado_mec,
        index=_idx(op_estado_mec, str(mecanica.get("estado", op_estado_mec[0]) or op_estado_mec[0])),
        horizontal=True,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_mec_estado",
    )

    stage.state["ventilacao_aberturas"] = {"janelas": janelas, "portas": portas}
    stage.state["ventilacao_mecanica"] = {"tipo": tipo, "estado": estado}


def render_percepcao_termica(stage: StageContext) -> None:
    perc = stage.state.get("percepcao_termica", {})
    if not isinstance(perc, dict):
        perc = {}

    sensacoes = ["frio", "confortável", "calor"]

    st.markdown("**Qual é a sensação térmica percebida?**")
    sensacao = st.radio(
        "Sensação térmica",
        options=sensacoes,
        index=_idx(sensacoes, str(perc.get("sensacao", sensacoes[1]) or sensacoes[1])),
        horizontal=True,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_sensacao",
    )

    st.markdown("**Qual a intensidade percebida?**")
    intensidade = st.slider(
        "Intensidade",
        min_value=1,
        max_value=5,
        value=int(perc.get("intensidade", 3) or 3),
        step=1,
        key=f"{STAGE_ID}_intensidade",
    )

    st.markdown("**Faça uma breve descrição da sensação térmica:**")
    descricao = st.text_area(
        "Descrição da sensação térmica",
        value=str(perc.get("descricao", "") or ""),
        height=100,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_descricao",
    )

    st.markdown("**Percebeu alguma diferença entre as regiões no interior do ambiente?**")
    diferencas = st.text_area(
        "Diferenças entre regiões",
        value=str(perc.get("diferencas_regioes", "") or ""),
        height=100,
        label_visibility="collapsed",
        key=f"{STAGE_ID}_diferencas",
    )

    stage.state["percepcao_termica"] = {
        "sensacao": sensacao,
        "intensidade": int(intensidade),
        "descricao": descricao,
        "diferencas_regioes": diferencas,
    }


def render_contexto(stage: StageContext) -> None:
    st.write(
        "Para caracterizar o contexto da medição, selecione o ambiente onde "
        "as medidas serão realizadas, o momento da coleta e as condições em que "
        "o local se encontra."
    )
    render_ambiente_medicao(stage)
    render_condicoes_coleta(stage)

    st.markdown("---")
    render_ventilacao(stage)

    st.markdown("---")
    render_percepcao_termica(stage)


def save(stage: StageContext, ctx: Dict[str, Any]) -> None:
    payload = {
        "ambiente_medicao": stage.state.get("ambiente_medicao", {}),
        "condicoes_coleta": stage.state.get("condicoes_coleta", {}),
        "ventilacao_aberturas": stage.state.get("ventilacao_aberturas", {}),
        "ventilacao_mecanica": stage.state.get("ventilacao_mecanica", {}),
        "percepcao_termica": stage.state.get("percepcao_termica", {}),
    }
    save_stage_overwrite(stage.container_path, ctx, stage.stage_id, payload)


# -----------------------------------------------------------------------------
# ENTRYPOINT
# -----------------------------------------------------------------------------
def render(ctx: Dict[str, Any]) -> None:
    stage = build_context(ctx)
    render_contexto(stage)

    if st.button("Salvar", type="primary", key=f"{STAGE_ID}_salvar"):
        save(stage, ctx)
        st.success("Salvo no arquivo de investigação (somente esta etapa).")
