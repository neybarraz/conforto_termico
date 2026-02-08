# blocks/investigacao/04_grafico_gradiente_termico.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
import math
import re

import streamlit as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from storage.io_csv import load_json, save_json


# =============================================================================
# CONFIG
# =============================================================================
STAGE_ID = "investigacao_grafico_gradiente_termico"
KEY_NS = f"{STAGE_ID}__v2"  # namespace único para evitar colisões de key

COLETA_STAGE_ID = "investigacao_coleta_de_dados"
DIM_STAGE_ID = "investigacao_estrutura_do_ambiente"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVESTIGACAO_DIR = PROJECT_ROOT / "data" / "investigacao"
FIGURAS_DIR = PROJECT_ROOT / "data" / "figuras"

# Parâmetros fixos
_GRID_N = 181
_IDW_POWER = 3.4
_WALL_WEIGHT = 2.8
_WALL_SAMPLES = 70
_AIR_N_SIDE = 50
_AIR_SIGMA_FRAC = 0.20
_BLUR_K = 7

_TA_POINTS: Dict[str, Tuple[float, float]] = {
    "NO": (0.30, 0.30),
    "NE": (0.70, 0.30),
    "C":  (0.50, 0.50),
    "SO": (0.30, 0.70),
    "SE": (0.70, 0.70),
}

_TC_WALL_POINTS: Dict[str, Tuple[float, float]] = {
    "N1": (0.25, 0.00),
    "N2": (0.75, 0.00),
    "O1": (0.00, 0.25),
    "O2": (0.00, 0.75),
    "L1": (1.00, 0.25),
    "L2": (1.00, 0.75),
    "S1": (0.25, 1.00),
    "S2": (0.75, 1.00),
}

# =============================================================================
# QUESTÕES GUIADAS (Termodinâmica + Conforto) — para este gráfico
# =============================================================================
GUIDED_QUESTIONS = [
    {
        "sec": "1) Leitura da imagem (observação)",
        "items": [
            {"id": "obs_01", "tipo": "texto", "prompt": "O que as cores diferentes representam fisicamente neste mapa?"},
            {"id": "obs_02", "tipo": "texto", "prompt": "Se a imagem é vista de cima e os quatro lados são paredes, por que a temperatura não é uniforme no interior?"},
            {"id": "obs_03", "tipo": "texto", "prompt": "Onde estão os maiores gradientes de temperatura? O que isso sugere sobre o papel das paredes?"},
        ],
    },
    {
        "sec": "2) Temperatura e energia interna (U ~ T)",
        "items": [
            {"id": "ut_01", "tipo": "texto", "prompt": "Em um gás como o ar, o que a temperatura mede (interpretação microscópica)?"},
            {"id": "ut_02", "tipo": "texto", "prompt": "Se a temperatura varia no espaço, o que isso indica sobre a distribuição de energia interna?"},
        ],
    },
    {
        "sec": "3) Primeira Lei (ΔU = Q − W)",
        "items": [
            {"id": "pl_01", "tipo": "texto", "prompt": "Escreva a Primeira Lei e indique qual termo você considera desprezível neste caso (W≈0 ou não). Justifique."},
            {"id": "pl_02", "tipo": "texto", "prompt": "Com W≈0, explique por que o mapa de T pode ser interpretado como consequência de Q (trocas de calor)."},
        ],
    },
    {
        "sec": "4) Modos de transferência (condução, convecção e radiação)",
        "items": [
            {"id": "modes_01", "tipo": "texto", "prompt": "Condução: como o calor chega à superfície interna das paredes? O que a condução determina (Ts)?"},
            {"id": "modes_02", "tipo": "texto", "prompt": "Convecção: como a parede troca calor com o ar próximo? Por que existe gradiente perto da parede (camada limite)?"},
            {"id": "modes_03", "tipo": "texto", "prompt": "Radiação: mesmo sem tocar nas paredes, um ocupante sentiria diferença? Explique usando temperatura radiante média."},
        ],
    },
    {
        "sec": "5) Regime permanente e conservação de energia",
        "items": [
            {"id": "reg_01", "tipo": "texto", "prompt": "Este mapa parece representar regime permanente ou transitório? Qual evidência sustenta sua resposta?"},
            {"id": "reg_02", "tipo": "texto", "prompt": "Em regime permanente, o que a Primeira Lei implica para o balanço de energia (Q_entra = Q_sai)?"},
        ],
    },
    {
        "sec": "6) Conforto térmico",
        "items": [
            {"id": "conf_01", "tipo": "texto", "prompt": "Um único valor de temperatura média descreve o conforto neste ambiente? Por quê?"},
            {"id": "conf_02", "tipo": "texto", "prompt": "Como a posição do ocupante em relação às paredes afeta o conforto (radiação + convecção)?"},
            {"id": "conf_03", "tipo": "texto", "prompt": "Cite 2 estratégias de projeto para reduzir os gradientes observados (envoltória/isolamento/ventilação/sombreamento)."},
        ],
    },
]


# =============================================================================
# CONTEXTO / UTIL
# =============================================================================
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


def figura_path(ctx: Dict[str, Any]) -> Path:
    aluno = safe_filename(get_aluno_from_ctx(ctx))
    FIGURAS_DIR.mkdir(parents=True, exist_ok=True)
    return FIGURAS_DIR / f"{aluno}_gradiente_termico.png"


def figura_relpath(ctx: Dict[str, Any]) -> str:
    aluno = safe_filename(get_aluno_from_ctx(ctx))
    rel = Path("data") / "figuras" / f"{aluno}_gradiente_termico.png"
    return rel.as_posix()


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
    state.setdefault("last_generated_at", "")
    state.setdefault("figura_png", "")
    state.setdefault("horario_ref", "")
    state.setdefault("meta", {})
    state.setdefault("respostas", {})  # respostas do aluno

    return StageContext(
        stage_id=STAGE_ID,
        container_path=container_path,
        root=root,
        saved_stage=saved_stage if isinstance(saved_stage, dict) else {},
        state=state,
    )


# =============================================================================
# LEITURA DE DADOS
# =============================================================================
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


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        if isinstance(x, str):
            x = x.strip().replace(",", ".")
        return float(x)
    except Exception:
        return None


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

    ta_by_id = _index_by_id(r0.get("ta_rows", []), "id")
    ts_by_id = _index_by_id(r0.get("ts_rows", []), "id")

    return horario, ta_by_id, ts_by_id


def _load_layout_dims(root: Dict[str, Any]) -> Tuple[float, float]:
    stages = root.get("stages")
    if not isinstance(stages, dict):
        return (1.0, 1.0)

    dim_stage = stages.get(DIM_STAGE_ID, {})
    if not isinstance(dim_stage, dict):
        return (1.0, 1.0)

    estrutura = dim_stage.get("estrutura_ambiente", {})
    dims = None

    if isinstance(estrutura, dict) and isinstance(estrutura.get("dimensoes"), dict):
        dims = estrutura.get("dimensoes")

    if dims is None:
        od = dim_stage.get("orientacao_dimensoes", {})
        if isinstance(od, dict) and isinstance(od.get("dimensoes"), dict):
            dims = od.get("dimensoes")

    if not isinstance(dims, dict):
        return (1.0, 1.0)

    try:
        w = float(dims.get("largura_m", 1.0))
    except Exception:
        w = 1.0
    try:
        h = float(dims.get("profundidade_m", 1.0))
    except Exception:
        h = 1.0

    return (max(0.1, w), max(0.1, h))


# =============================================================================
# INTERPOLAÇÃO / DENSIFICAÇÃO
# =============================================================================
def _idw_interpolate(
    xy: np.ndarray,
    values: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    *,
    power: float = 2.0,
    eps: float = 1e-12,
    weights: Optional[np.ndarray] = None,
) -> np.ndarray:
    if weights is None:
        w_pts = np.ones((xy.shape[0],), dtype=float)
    else:
        w_pts = np.asarray(weights, dtype=float)
        if w_pts.shape[0] != xy.shape[0]:
            w_pts = np.ones((xy.shape[0],), dtype=float)

    dx = grid_x[None, :, :] - xy[:, 0][:, None, None]
    dy = grid_y[None, :, :] - xy[:, 1][:, None, None]
    d2 = dx * dx + dy * dy

    near = d2 < eps
    out = np.full_like(grid_x, np.nan, dtype=float)

    if np.any(near):
        idx_pt, idx_r, idx_c = np.where(near)
        for k in range(len(idx_pt)):
            out[idx_r[k], idx_c[k]] = float(values[idx_pt[k]])

    mask = np.isnan(out)
    if np.any(mask):
        d = np.sqrt(d2) + eps
        w = (w_pts[:, None, None]) / (d ** power)
        num = np.sum(w * values[:, None, None], axis=0)
        den = np.sum(w, axis=0)
        zz = num / (den + eps)
        out[mask] = zz[mask]

    return out


def _blur_separable_edge(arr: np.ndarray, k: int = 7) -> np.ndarray:
    k = int(max(3, k))
    if k % 2 == 0:
        k += 1
    pad = k // 2
    w = np.ones(k, dtype=float) / float(k)

    a = np.pad(arr, ((0, 0), (pad, pad)), mode="edge")
    tmp = np.apply_along_axis(lambda m: np.convolve(m, w, mode="valid"), axis=1, arr=a)

    b = np.pad(tmp, ((pad, pad), (0, 0)), mode="edge")
    out = np.apply_along_axis(lambda m: np.convolve(m, w, mode="valid"), axis=0, arr=b)

    return out


def _linear_interp_extrap(s: float, s1: float, t1: float, s2: float, t2: float) -> float:
    if abs(s2 - s1) < 1e-12:
        return float(t1)
    m = (t2 - t1) / (s2 - s1)
    return float(t1 + m * (s - s1))


def _densify_wall_points(tc_by_id: Dict[str, float], *, n_samples: int = 70) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def add_wall(wall_name: str, pid_a: str, pid_b: str, *, axis: str, fixed: float, s_a: float, s_b: float):
        if pid_a not in tc_by_id or pid_b not in tc_by_id:
            return
        t_a = float(tc_by_id[pid_a])
        t_b = float(tc_by_id[pid_b])

        ss = np.linspace(0.0, 1.0, int(max(10, n_samples)))
        for s in ss:
            t = _linear_interp_extrap(float(s), s_a, t_a, s_b, t_b)
            if axis == "x":
                x, y = float(s), float(fixed)
            else:
                x, y = float(fixed), float(s)
            out.append({"id": f"WALL_{wall_name}_{s:.3f}", "x": x, "y": y, "T_C": float(t), "fonte": "Tc_dense"})

    add_wall("N", "N1", "N2", axis="x", fixed=0.0, s_a=0.25, s_b=0.75)
    add_wall("S", "S1", "S2", axis="x", fixed=1.0, s_a=0.25, s_b=0.75)
    add_wall("O", "O1", "O2", axis="y", fixed=0.0, s_a=0.25, s_b=0.75)
    add_wall("L", "L1", "L2", axis="y", fixed=1.0, s_a=0.25, s_b=0.75)
    return out


def _bilinear_T(
    x: float,
    y: float,
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    t00: float,
    t10: float,
    t01: float,
    t11: float,
) -> float:
    if abs(x1 - x0) < 1e-12 or abs(y1 - y0) < 1e-12:
        return float(t00)
    u = (x - x0) / (x1 - x0)
    v = (y - y0) / (y1 - y0)
    u = max(0.0, min(1.0, float(u)))
    v = max(0.0, min(1.0, float(v)))
    return float((1 - u) * (1 - v) * t00 + u * (1 - v) * t10 + (1 - u) * v * t01 + u * v * t11)


def _densify_air_square_bilinear(ta_by_id: Dict[str, float], *, n_side: int = 50, sigma_frac: float = 0.20) -> List[Dict[str, Any]]:
    required = ("NO", "NE", "SO", "SE")
    if not all(k in ta_by_id for k in required):
        return []

    x0, y0 = _TA_POINTS["NO"]
    x1, y1 = _TA_POINTS["SE"]
    tNO = float(ta_by_id["NO"])
    tNE = float(ta_by_id["NE"])
    tSO = float(ta_by_id["SO"])
    tSE = float(ta_by_id["SE"])

    xc, yc = _TA_POINTS["C"]
    tC = float(ta_by_id["C"]) if "C" in ta_by_id else None

    delta = 0.0
    if tC is not None:
        tC_bi = _bilinear_T(float(xc), float(yc), x0=x0, x1=x1, y0=y0, y1=y1, t00=tNO, t10=tNE, t01=tSO, t11=tSE)
        delta = float(tC - tC_bi)

    Lx = (x1 - x0)
    Ly = (y1 - y0)
    sigma = float(sigma_frac) * float(min(Lx, Ly))
    sigma2 = max(1e-12, sigma * sigma)

    xs = np.linspace(x0, x1, int(max(15, n_side)))
    ys = np.linspace(y0, y1, int(max(15, n_side)))

    out: List[Dict[str, Any]] = []
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            tb = _bilinear_T(float(x), float(y), x0=x0, x1=x1, y0=y0, y1=y1, t00=tNO, t10=tNE, t01=tSO, t11=tSE)
            if tC is not None and abs(delta) > 1e-12:
                dx = float(x) - float(xc)
                dy = float(y) - float(yc)
                w = math.exp(-(dx * dx + dy * dy) / (2.0 * sigma2))
                t = float(tb + delta * w)
            else:
                t = float(tb)
            out.append({"id": f"AIR2D_{iy:03d}_{ix:03d}", "x": float(x), "y": float(y), "T_C": float(t), "fonte": "Ta_dense2D"})

    if tC is not None:
        out.append({"id": "C_DENSE_LOCK", "x": float(xc), "y": float(yc), "T_C": float(tC), "fonte": "Ta_dense2D"})

    return out


def _collect_from_coleta_tables(
    ta_by_id: Dict[str, Any],
    ts_by_id: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, float], Dict[str, float]]:
    pts: List[Dict[str, Any]] = []
    ta_vals: Dict[str, float] = {}
    tc_vals: Dict[str, float] = {}

    for pid in _TA_POINTS.keys():
        row = ta_by_id.get(pid, {}) if isinstance(ta_by_id, dict) else {}
        Ta = _safe_float((row or {}).get("Ta_C"))
        if Ta is None:
            continue
        x, y = _TA_POINTS[pid]
        ta_vals[pid] = float(Ta)
        pts.append({"id": pid, "x": float(x), "y": float(y), "T_C": float(Ta), "fonte": "Ta_medida"})

    for pid in _TC_WALL_POINTS.keys():
        row = ts_by_id.get(pid, {}) if isinstance(ts_by_id, dict) else {}
        Ts = _safe_float((row or {}).get("Ts_C"))
        if Ts is None:
            continue
        x, y = _TC_WALL_POINTS[pid]
        tc_vals[pid] = float(Ts)
        pts.append({"id": pid, "x": float(x), "y": float(y), "T_C": float(Ts), "fonte": "Ts_medida"})

    return pts, ta_vals, tc_vals


def _build_gradient_figure(
    *,
    largura_m: float,
    profundidade_m: float,
    ta_by_id: Dict[str, Any],
    ts_by_id: Dict[str, Any],
) -> Tuple[plt.Figure, Dict[str, Any]]:
    pts_measured, ta_vals, tc_vals = _collect_from_coleta_tables(ta_by_id, ts_by_id)

    dense_wall_pts = _densify_wall_points(tc_vals, n_samples=_WALL_SAMPLES)
    dense_air_pts = _densify_air_square_bilinear(ta_vals, n_side=_AIR_N_SIDE, sigma_frac=_AIR_SIGMA_FRAC)

    all_pts: List[Dict[str, Any]] = []
    all_pts.extend(pts_measured)
    all_pts.extend(dense_wall_pts)
    all_pts.extend(dense_air_pts)

    if len(all_pts) < 3:
        raise RuntimeError("Poucos pontos para gerar o gradiente. Verifique Ta/Ts na coleta.")

    xs_m: List[float] = []
    ys_m: List[float] = []
    vs: List[float] = []
    ws: List[float] = []

    for p in all_pts:
        x = float(p["x"]) * float(largura_m)
        y = float(p["y"]) * float(profundidade_m)
        v = float(p["T_C"])
        fonte = str(p.get("fonte", ""))

        xs_m.append(x)
        ys_m.append(y)
        vs.append(v)

        if fonte == "Tc_dense" or fonte == "Ts_medida":
            ws.append(float(_WALL_WEIGHT))
        else:
            ws.append(1.0)

    xy = np.array(list(zip(xs_m, ys_m)), dtype=float)
    values = np.array(vs, dtype=float)
    weights = np.array(ws, dtype=float)

    gx = np.linspace(0.0, float(largura_m), int(_GRID_N))
    gy = np.linspace(0.0, float(profundidade_m), int(_GRID_N))
    grid_x, grid_y = np.meshgrid(gx, gy)

    z = _idw_interpolate(xy, values, grid_x, grid_y, power=float(_IDW_POWER), weights=weights)

    vmin_data = float(np.nanmin(values))
    vmax_data = float(np.nanmax(values))

    z = _blur_separable_edge(z, k=_BLUR_K)
    z = np.clip(z, vmin_data, vmax_data)

    ratio = float(largura_m) / float(profundidade_m)
    base_h = 4.4
    base_w = max(6.5, base_h * ratio)

    fig = plt.figure(figsize=(base_w, base_h), dpi=160)
    ax = fig.add_subplot(111)

    im = ax.imshow(
        z,
        origin="upper",
        extent=[0.0, float(largura_m), float(profundidade_m), 0.0],
        interpolation="bicubic",
        aspect="equal",
        cmap="turbo",
        vmin=vmin_data,
        vmax=vmax_data,
    )

    ax.plot([0, largura_m, largura_m, 0, 0], [0, 0, profundidade_m, profundidade_m, 0], linewidth=1.2)

    ax.set_xlim(0.0, float(largura_m))
    ax.set_ylim(float(profundidade_m), 0.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Gradiente térmico (Ta no interior + Ts nas paredes)", fontsize=12)

    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.06)
    cb.ax.set_title("T (°C)", fontsize=10)
    ticks = np.linspace(vmin_data, vmax_data, 5)
    cb.set_ticks(ticks)
    cb.ax.set_yticklabels([f"{t:.2f}" for t in ticks])

    meta = {
        "n_pts_measured": len(pts_measured),
        "n_pts_wall_dense": len(dense_wall_pts),
        "n_pts_air_dense": len(dense_air_pts),
        "grid_n": int(_GRID_N),
        "idw_power": float(_IDW_POWER),
        "wall_weight": float(_WALL_WEIGHT),
        "blur_k": int(_BLUR_K),
    }
    return fig, meta


def _save_gradient_png(
    *,
    largura_m: float,
    profundidade_m: float,
    ta_by_id: Dict[str, Any],
    ts_by_id: Dict[str, Any],
    out_path: Path,
) -> Tuple[bool, str, Dict[str, Any]]:
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    try:
        fig, meta = _build_gradient_figure(
            largura_m=largura_m,
            profundidade_m=profundidade_m,
            ta_by_id=ta_by_id,
            ts_by_id=ts_by_id,
        )
        fig.savefig(out_path, format="png", bbox_inches="tight", pad_inches=0.05)
        plt.close(fig)
        return True, f"Imagem salva", meta
    except Exception as e:
        try:
            plt.close("all")
        except Exception:
            pass
        return False, f"Falha ao gerar PNG. Motivo: {e}", {}


def _save(stage: StageContext, ctx: Dict[str, Any]) -> None:
    payload = {
        "horario_ref": stage.state.get("horario_ref", ""),
        "last_loaded_at": stage.state.get("last_loaded_at", ""),
        "last_generated_at": stage.state.get("last_generated_at", ""),
        "figura_png": stage.state.get("figura_png", ""),
        "params_fixos": {
            "grid_n": int(_GRID_N),
            "idw_power": float(_IDW_POWER),
            "wall_weight": float(_WALL_WEIGHT),
            "wall_samples": int(_WALL_SAMPLES),
            "air_n_side": int(_AIR_N_SIDE),
            "air_sigma_frac": float(_AIR_SIGMA_FRAC),
            "blur_k": int(_BLUR_K),
        },
        "meta": stage.state.get("meta", {}),
        "respostas": stage.state.get("respostas", {}),
    }
    save_stage_overwrite(stage.container_path, ctx, stage.stage_id, payload)


# =============================================================================
# UI HELPERS
# =============================================================================
def _render_questions(stage: StageContext, ctx: Dict[str, Any]) -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stMarkdown"] { margin-bottom: 0.25rem; }
        div[data-testid="stTextArea"] { margin-top: -0.6rem; margin-bottom: 0.4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    respostas = stage.state.get("respostas", {})
    if not isinstance(respostas, dict):
        respostas = {}

    for sec in GUIDED_QUESTIONS:
        sec_title = str(sec.get("sec", "secao"))
        sec_key = re.sub(r"[^a-zA-Z0-9]+", "_", sec_title).strip("_").lower()

        with st.container(border=True):
            st.markdown(f"#### {sec_title}")

            for q in sec["items"]:
                qid = str(q["id"])
                cur = str(respostas.get(qid, "") or "")

                st.markdown(f"**{q['prompt']}**")
                val = st.text_area(
                    label="",
                    value=cur,
                    height=90,
                    key=f"{KEY_NS}__q__{qid}",
                )
                respostas[qid] = val

            col_a, _ = st.columns([1, 3])
            with col_a:
                if st.button(
                    "Salvar",
                    type="primary",
                    key=f"{KEY_NS}__save_sec__{sec_key}",
                ):
                    stage.state["respostas"] = respostas
                    _save(stage, ctx)
                    st.success("Respostas salvas.")

    stage.state["respostas"] = respostas


# =============================================================================
# UI
# =============================================================================
def render(ctx: Dict[str, Any]) -> None:
    stage = build_context(ctx)

    st.markdown("### Gráfico de gradiente térmico (interpolação)")
    st.write("Este gráfico é pesado. Ele **não é gerado automaticamente**.")

    # -------------------------------------------------------------------------
    # Ações principais (mesma linha)
    # -------------------------------------------------------------------------
    root_cache = stage.state.get("root_cache")
    has_cache = isinstance(root_cache, dict) and bool(root_cache)

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Carregar dados do arquivo", type="secondary", key=f"{KEY_NS}__load"):
            root = load_json(stage.container_path) or {}
            stage.state["root_cache"] = root
            stage.state["last_loaded_at"] = now_iso()
            st.success("Dados carregados.")
            has_cache = True

    with col2:
        gerar_clicked = st.button(
            "Gerar gráfico",
            type="primary",
            key=f"{KEY_NS}__export_png",
            disabled=not has_cache,
        )

    # Se ainda não carregou, mostra instrução e para aqui
    root_cache = stage.state.get("root_cache")
    if not isinstance(root_cache, dict) or not root_cache:
        st.info("Nenhum dado carregado ainda. Clique em “Carregar dados do arquivo”.")
        return

    # -------------------------------------------------------------------------
    # Leitura de dados e metadados
    # -------------------------------------------------------------------------
    horario, ta_by_id, ts_by_id = _load_latest_coleta(root_cache)
    largura_m, profundidade_m = _load_layout_dims(root_cache)
    stage.state["horario_ref"] = horario

    if not isinstance(ta_by_id, dict) or not isinstance(ts_by_id, dict):
        st.error("Estrutura de Ta/Ts inválida na coleta.")
        return

    st.caption(f"Dimensões: {largura_m:.2f} m × {profundidade_m:.2f} m.")
    if horario:
        st.caption(f"Horário da coleta: {horario}")

    # -------------------------------------------------------------------------
    # Geração do PNG (1 único caminho)
    # -------------------------------------------------------------------------
    if gerar_clicked:
        out_path = figura_path(ctx)
        ok, msg, meta = _save_gradient_png(
            largura_m=largura_m,
            profundidade_m=profundidade_m,
            ta_by_id=ta_by_id,
            ts_by_id=ts_by_id,
            out_path=out_path,
        )
        if ok:
            stage.state["figura_png"] = figura_relpath(ctx)
            stage.state["last_generated_at"] = now_iso()
            if isinstance(meta, dict) and meta:
                stage.state["meta"] = meta
            _save(stage, ctx)
            st.success(msg)
            st.image(str(out_path), caption=f"Arquivo: {out_path.name}", use_container_width=True)
        else:
            st.error(msg)

    # Mostra o último salvo (se existir)
    out_path = figura_path(ctx)
    if out_path.exists():
        st.markdown("#### Último gráfico salvo")
        st.image(str(out_path), caption=f"Arquivo: {out_path.name}", use_container_width=True)

    st.divider()
    _render_questions(stage, ctx)

    # cols = st.columns([1, 2])
    # with cols[0]:
    #     if st.button("Salvar (metadados/estado)", key=f"{KEY_NS}__salvar_manual"):
    #         _save(stage, ctx)
    #         st.success("Stage salvo.")
    # with cols[1]:
        # st.caption("Dica: gere o gráfico antes de responder.")
