# blocks/investigacao/02_analise_radiacao_conforto.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import math
import re

import streamlit as st

from storage.io_csv import load_json, save_json


# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
STAGE_ID = "investigacao_analise_radiacao_conforto"

# ID do stage onde estão salvas as medições (o seu arquivo de coleta)
COLETA_STAGE_ID = "investigacao_coleta_de_dados"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVESTIGACAO_DIR = PROJECT_ROOT / "data" / "investigacao"

CANTOS = {
    "NO": {"label": "Canto NO", "ta_id": "NO", "ts_ids": ("O1", "N1"), "ts_labels": ("O1", "N1")},
    "NE": {"label": "Canto NE", "ta_id": "NE", "ts_ids": ("N2", "L1"), "ts_labels": ("N2", "L1")},
    "SO": {"label": "Canto SO", "ta_id": "SO", "ts_ids": ("O2", "S1"), "ts_labels": ("O2", "S1")},
    "SE": {"label": "Canto SE", "ta_id": "SE", "ts_ids": ("L2", "S2"), "ts_labels": ("L2", "S2")},
}


# -----------------------------------------------------------------------------
# CONTEXTO / UTIL (mesmo padrão do seu app de investigação)
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


def save_stage_overwrite(
    container_path: Path, ctx: Dict[str, Any], stage_id: str, stage_data: Dict[str, Any]
) -> Dict[str, Any]:
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

    state.setdefault("root_cache", {})
    state.setdefault("last_loaded_at", "")
    state.setdefault("respostas", {})  # { "NO": {...}, "NE": {...}, ... }

    return StageContext(
        stage_id=STAGE_ID,
        container_path=container_path,
        root=root,
        saved_stage=saved_stage if isinstance(saved_stage, dict) else {},
        state=state,
    )


def _is_nan(x: Any) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)) and not _is_nan(x):
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


def _index_by_id(rows: Any, id_key: str = "id") -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for r in rows:
        if not isinstance(r, dict):
            continue
        pid = str(r.get(id_key, "") or "").strip()
        if pid:
            out[pid] = r
    return out


def _load_latest_coleta(root: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    stages = root.get("stages")
    if not isinstance(stages, dict):
        return "", {}, {}

    coleta = stages.get(COLETA_STAGE_ID, {})
    if not isinstance(coleta, dict):
        return "", {}, {}

    rodadas = coleta.get("rodadas_medicoes", [])
    if not isinstance(rodadas, list) or not rodadas:
        return "", {}, {}

    r0 = rodadas[0] if isinstance(rodadas[0], dict) else {}
    horario = str(r0.get("horario", "") or "").strip()

    ta_rows = r0.get("ta_rows", [])
    ts_rows = r0.get("ts_rows", [])

    ta_by_id = _index_by_id(ta_rows, "id")
    ts_by_id = _index_by_id(ts_rows, "id")

    return horario, ta_by_id, ts_by_id


def _fmt(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{x:.1f}".replace(".", ",")


def _compute_delta(ts: Optional[float], ta: Optional[float]) -> Optional[float]:
    if ts is None or ta is None:
        return None
    return ts - ta


def _interpret_delta(delta: Optional[float]) -> str:
    if delta is None:
        return "Sem dados suficientes"
    if abs(delta) < 1e-9:
        return "Equilíbrio (sem fluxo líquido)"
    if delta < 0:
        return "Ar → Superfície (superfície retira calor)"
    return "Superfície → Ar (superfície aquece o ar)"


def _radiative_bullets(ta: Optional[float], ts_a: Optional[float], ts_b: Optional[float]) -> str:
    if ta is None or ts_a is None or ts_b is None:
        return "• Não foi possível interpretar conforto radiativo porque faltam valores (Ta ou Ts).\n"

    mean_ts = (ts_a + ts_b) / 2.0
    d = mean_ts - ta

    if abs(d) < 1e-9:
        return (
            "• As superfícies estão, em média, na mesma temperatura do ar.\n"
            "• Troca radiativa tende a ficar neutra (sem tendência clara de aquecer/esfriar).\n"
        )
    if d < 0:
        return (
            "• As superfícies estão ligeiramente mais frias que o ar.\n"
            "• Tendem a receber energia do ambiente (ar e ocupantes) e não aumentam a carga térmica radiante.\n"
            "• Interpretação: pequeno “alívio” radiativo, compatível com ΔT negativo.\n"
        )
    return (
        "• As superfícies estão ligeiramente mais quentes que o ar.\n"
        "• Tendem a emitir mais energia para o ambiente e podem aumentar a carga térmica radiante.\n"
        "• Interpretação: tendência de desconforto radiativo, compatível com ΔT positivo.\n"
    )


def _render_regra_pratica_once() -> None:
    st.markdown("**Leitura física simplificada (regra prática)**")
    st.table(
        [
            {
                "Valor de ΔT": "ΔT < 0",
                "Quem está mais quente?": "Ar",
                "Sentido do calor": "Ar → Superfície",
                "Efeito no ambiente": "Superfície retira calor",
            },
            {
                "Valor de ΔT": "ΔT = 0",
                "Quem está mais quente?": "Nenhum",
                "Sentido do calor": "Sem fluxo líquido",
                "Efeito no ambiente": "Equilíbrio térmico",
            },
            {
                "Valor de ΔT": "ΔT > 0",
                "Quem está mais quente?": "Superfície",
                "Sentido do calor": "Superfície → Ar",
                "Efeito no ambiente": "Superfície aquece o ar",
            },
        ]
    )


def _flow_from_delta(delta: Optional[float]) -> Optional[str]:
    """
    Retorna a resposta esperada (para comparação e feedback):
      - "ar_ganhando" (ar recebe calor da superfície)  -> ΔT > 0
      - "ar_perdendo" (ar perde calor p/ superfície)   -> ΔT < 0
      - "equilibrio"                                  -> ΔT = 0
      - None se não der para avaliar
    """
    if delta is None:
        return None
    if abs(delta) < 1e-9:
        return "equilibrio"
    if delta > 0:
        return "ar_ganhando"
    return "ar_perdendo"


def _save_all(stage: StageContext, ctx: Dict[str, Any], horario: str) -> None:
    payload = {
        "horario_ref": horario,
        "respostas": stage.state.get("respostas", {}),
        "last_loaded_at": stage.state.get("last_loaded_at", ""),
    }
    save_stage_overwrite(stage.container_path, ctx, stage.stage_id, payload)


def _render_canto(
    stage: StageContext,
    ctx: Dict[str, Any],
    canto_key: str,
    canto_cfg: Dict[str, Any],
    horario: str,
    ta_by_id: Dict[str, Any],
    ts_by_id: Dict[str, Any],
) -> None:
    st.subheader(f"{canto_cfg['label']}")

    ta_id = canto_cfg["ta_id"]
    ts1_id, ts2_id = canto_cfg["ts_ids"]
    ts1_label, ts2_label = canto_cfg["ts_labels"]

    ta = _safe_float((ta_by_id.get(ta_id, {}) or {}).get("Ta_C"))
    ts1 = _safe_float((ts_by_id.get(ts1_id, {}) or {}).get("Ts_C"))
    ts2 = _safe_float((ts_by_id.get(ts2_id, {}) or {}).get("Ts_C"))

    d1 = _compute_delta(ts1, ta)
    d2 = _compute_delta(ts2, ta)

    # guarda um snapshot numérico
    respostas = stage.state.get("respostas", {})
    if not isinstance(respostas, dict):
        respostas = {}
    respostas.setdefault(canto_key, {})
    respostas[canto_key].setdefault(
        "snapshot",
        {
            "ta_id": ta_id,
            "ts_ids": [ts1_id, ts2_id],
            "ta_C": ta,
            "ts_C": [ts1, ts2],
            "deltas_C": [d1, d2],
        },
    )
    stage.state["respostas"] = respostas

    st.markdown("**1) Tabela de dados + ΔT** (ΔT = Ts − Ta)")
    st.table(
        [
            {"Ponto": "Ta", "ID": ta_id, "Tipo": "Ar", "Temperatura (°C)": _fmt(ta), "ΔT (°C)": "—"},
            {"Ponto": ts1_label, "ID": ts1_id, "Tipo": "Superfície", "Temperatura (°C)": _fmt(ts1), "ΔT (°C)": _fmt(d1)},
            {"Ponto": ts2_label, "ID": ts2_id, "Tipo": "Superfície", "Temperatura (°C)": _fmt(ts2), "ΔT (°C)": _fmt(d2)},
        ]
    )

    st.markdown("**Perguntas (após a tabela): ar ganha ou perde calor?**")

    def _render_q_fluxo(surface_key: str, surface_label: str, delta: Optional[float]) -> None:
        expected = _flow_from_delta(delta)

        cur = stage.state["respostas"].get(canto_key, {}).get("fluxo", {}).get(surface_key, {})
        if not isinstance(cur, dict):
            cur = {}

        # opções visíveis (estilo da imagem: múltipla escolha com rádio)
        option_keys = ["ar_ganhando", "ar_perdendo", "equilibrio", "nao_sei"]
        option_labels = {
            "ar_ganhando": "O ar está GANHANDO calor desta superfície (superfície → ar)",
            "ar_perdendo": "O ar está PERDENDO calor para esta superfície (ar → superfície)",
            "equilibrio": "Equilíbrio (sem fluxo líquido)",
            "nao_sei": "Não sei / sem dados suficientes",
        }

        current_val = str(cur.get("escolha", "") or "")
        if current_val not in option_keys:
            current_val = "nao_sei"

        idx = option_keys.index(current_val)

        escolha = st.radio(
            f"Para {surface_label}, o que acontece com o ar?",
            options=option_keys,
            index=idx,
            format_func=lambda k: option_labels.get(k, str(k)),
            key=f"{STAGE_ID}_{canto_key}_{surface_key}_radio",
            horizontal=False,  # se quiser em linha (como no topo da sua imagem), mude para True
        )

        justificativa = st.text_area(
            f"Justifique usando o sinal do ΔT ({surface_label}) e a leitura física:",
            value=str(cur.get("justificativa", "") or ""),
            height=90,
            key=f"{STAGE_ID}_{canto_key}_{surface_key}_just",
        )

        stage.state["respostas"][canto_key].setdefault("fluxo", {})
        stage.state["respostas"][canto_key]["fluxo"][surface_key] = {
            "delta_C": delta,
            "escolha": escolha,
            "justificativa": justificativa,
            "gabarito_esperado": expected,
        }

        # feedback leve só quando o aluno escolhe uma opção "de conteúdo"
        # if escolha in ("ar_ganhando", "ar_perdendo", "equilibrio") and expected and escolha != expected:
        #     st.info("Reveja: compare o sinal do ΔT com a regra prática acima.")

    _render_q_fluxo("ts1", ts1_label, d1)
    _render_q_fluxo("ts2", ts2_label, d2)



    cur_cr = stage.state["respostas"].get(canto_key, {}).get("conforto_radiativo", {})
    if not isinstance(cur_cr, dict):
        cur_cr = {}

    st.markdown("**Pergunta (conforto radiativo):**")
    cr_txt = st.text_area(
        "Com base em Ta, Ts e no sinal médio (Ts−Ta), descreva se este canto tende a causar alívio radiativo, neutralidade ou desconforto radiativo. Explique em 2–5 linhas.",
        value=str(cur_cr.get("texto", "") or ""),
        height=110,
        key=f"{STAGE_ID}_{canto_key}_cr_texto",
    )
    stage.state["respostas"][canto_key]["conforto_radiativo"] = {
        "texto": cr_txt,
        "referencia": {
            "ta_C": ta,
            "ts_media_C": ((ts1 + ts2) / 2.0) if (ts1 is not None and ts2 is not None) else None,
            "ts_media_minus_ta_C": (((ts1 + ts2) / 2.0) - ta)
            if (ta is not None and ts1 is not None and ts2 is not None)
            else None,
        },
    }


    if st.button(
        "Salvar",
        type="primary",
        key=f"{STAGE_ID}_{canto_key}_salvar_tudo",
    ):
        _save_all(stage, ctx, horario)
        st.success("Salvo os dados informados.")


def render(ctx: Dict[str, Any]) -> None:
    stage = build_context(ctx)

    st.markdown("### Análise numérica: radiação térmica, influência de superfícies e conforto radiativo")
    st.markdown(
        "Clique no botão abaixo para ler o arquivo de investigação e atualizar as tabelas. "
        "A leitura não é automática para evitar custo/peso no app."
    )

    col1, _ = st.columns([1, 2])
    with col1:
        atualizar = st.button("Coletar/Atualizar", type="primary", key=f"{STAGE_ID}_atualizar")

    if atualizar:
        root = load_json(stage.container_path) or {}
        stage.state["root_cache"] = root
        stage.state["last_loaded_at"] = now_iso()

    root_cache = stage.state.get("root_cache")
    if not isinstance(root_cache, dict) or not root_cache:
        st.info("Nenhum dado carregado ainda. Clique em “Coletar/Atualizar”.")
        return

    _render_regra_pratica_once()

    horario, ta_by_id, ts_by_id = _load_latest_coleta(root_cache)

    if not horario:
        st.warning("Horário não encontrado na rodada salva (ok para análise, mas recomendado preencher).")
    if not ta_by_id and not ts_by_id:
        st.error("Não encontrei Ta/Ts na rodada salva. Verifique se a etapa de coleta foi salva corretamente.")
        return

    for canto_key in ("NO", "NE", "SO", "SE"):
        st.divider()
        _render_canto(stage, ctx, canto_key, CANTOS[canto_key], horario, ta_by_id, ts_by_id)

    loaded_at = stage.state.get("last_loaded_at", "")

