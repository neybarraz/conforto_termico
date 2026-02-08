# blocks/investigacao/Estrutura_do_Ambiente.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
import re

import streamlit as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from storage.io_csv import load_json, save_json


# =============================================================================
# 0) CONFIG
# =============================================================================
STAGE_ID = "investigacao_estrutura_do_ambiente"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVESTIGACAO_DIR = PROJECT_ROOT / "data" / "investigacao"
FIGURAS_DIR = PROJECT_ROOT / "data" / "figuras"

# Porta com largura fixa (fração do comprimento da parede)
DOOR_WIDTH_FRAC = 0.22

# Cores (preview / PNG)
COLOR_WALL = "#000000"
COLOR_WINDOW = "#2b6cb0"
COLOR_DOOR_GAP = "#ffffff"
COLOR_DOOR_EDGE = "#111111"
COLOR_VM_EDGE = "#444444"
COLOR_VM_FILL = "#f2f2f2"
COLOR_GRID = "#9aa0a6"
COLOR_TA = "#111111"
COLOR_TS = "#b91c1c"


# =============================================================================
# 1) CONTEXTO / UTIL
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
    return FIGURAS_DIR / f"{aluno}_estrutura_do_ambiente.png"


def figura_relpath(ctx: Dict[str, Any]) -> str:
    """
    Caminho RELATIVO ao PROJECT_ROOT (onde está o app/projeto).
    Isso evita salvar path absoluto do Windows (ex.: G:\\...).
    """
    aluno = safe_filename(get_aluno_from_ctx(ctx))
    rel = Path("data") / "figuras" / f"{aluno}_estrutura_do_ambiente.png"
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
    """
    Mesmo padrão: namespace exclusivo por STAGE_ID no session_state.
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

    # defaults mínimos (equivalente ao fluxo do anexo)
    state.setdefault(
        "orientacao_dimensoes",
        {"orientacao_topo": "Norte", "dimensoes": {"largura_m": 8.0, "profundidade_m": 6.0}},
    )
    state.setdefault("paredes_aberturas", {})   # init abaixo
    state.setdefault("estrutura_ambiente", {})  # payload consolidado

    return StageContext(
        stage_id=STAGE_ID,
        container_path=container_path,
        root=root,
        saved_stage=saved_stage if isinstance(saved_stage, dict) else {},
        state=state,
    )


# =============================================================================
# 2) LAYOUT BUILDER (mesma lógica do anexo)
# =============================================================================
def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _door_segment_from_center(center_frac: float, width_frac: float) -> Tuple[float, float]:
    c = _clamp01(center_frac)
    w = max(0.02, _clamp01(width_frac))
    half = w / 2.0
    a = c - half
    b = c + half
    if a < 0.0:
        b = min(1.0, b - a)
        a = 0.0
    if b > 1.0:
        a = max(0.0, a - (b - 1.0))
        b = 1.0
    a = _clamp01(a)
    b = _clamp01(b)
    if b < a:
        a, b = b, a
    return (a, b)


def _wall_defaults() -> Dict[str, Any]:
    return {
        "porta": {"existe": False, "center_frac": 0.5},
        "janela": {"existe": False, "inicio_frac": 0.0, "fim_frac": 1.0},
        "vm": {"existe": False, "pos_frac": 0.5},
    }


def _init_walls_if_needed(stage: StageContext) -> None:
    paredes = stage.state.get("paredes_aberturas", {})
    if not isinstance(paredes, dict) or not paredes:
        paredes = {}
    for w in ("Norte", "Sul", "Leste", "Oeste"):
        if w not in paredes or not isinstance(paredes.get(w), dict):
            paredes[w] = _wall_defaults()
    stage.state["paredes_aberturas"] = paredes


def _measurement_points_def() -> List[Dict[str, Any]]:
    xs = [1.0 / 6.0, 3.0 / 6.0, 5.0 / 6.0]
    ys = [1.0 / 6.0, 3.0 / 6.0, 5.0 / 6.0]

    out: List[Dict[str, Any]] = []
    ta_pts = [
        ("NO", "Ta — Canto Noroeste", xs[0], ys[0]),
        ("NE", "Ta — Canto Nordeste", xs[2], ys[0]),
        ("C",  "Ta — Centro",        xs[1], ys[1]),
        ("SO", "Ta — Canto Sudoeste", xs[0], ys[2]),
        ("SE", "Ta — Canto Sudeste",  xs[2], ys[2]),
    ]
    for pid, label, xf, yf in ta_pts:
        out.append({"id": pid, "label": label, "tipo": "Ta", "x_frac": xf, "y_frac": yf})

    a = 0.25
    b = 0.75
    inset = 0.04
    ts_pts = [
        ("N1", "Ts — Parede Norte (25%)", a, inset),
        ("N2", "Ts — Parede Norte (75%)", b, inset),
        ("S1", "Ts — Parede Sul (25%)", a, 1.0 - inset),
        ("S2", "Ts — Parede Sul (75%)", b, 1.0 - inset),
        ("O1", "Ts — Parede Oeste (25%)", inset, a),
        ("O2", "Ts — Parede Oeste (75%)", inset, b),
        ("L1", "Ts — Parede Leste (25%)", 1.0 - inset, a),
        ("L2", "Ts — Parede Leste (75%)", 1.0 - inset, b),
    ]
    for pid, label, xf, yf in ts_pts:
        out.append({"id": pid, "label": label, "tipo": "Ts", "x_frac": xf, "y_frac": yf})
    return out


def _build_layout_payload(stage: StageContext) -> Dict[str, Any]:
    od = stage.state.get("orientacao_dimensoes", {})
    if not isinstance(od, dict):
        od = {}
    dims = od.get("dimensoes", {"largura_m": 8.0, "profundidade_m": 6.0})
    if not isinstance(dims, dict):
        dims = {"largura_m": 8.0, "profundidade_m": 6.0}

    paredes_state = stage.state.get("paredes_aberturas", {})
    if not isinstance(paredes_state, dict):
        paredes_state = {}

    paredes: Dict[str, Any] = {}

    for w in ("Norte", "Sul", "Leste", "Oeste"):
        cfg = paredes_state.get(w, _wall_defaults())
        if not isinstance(cfg, dict):
            cfg = _wall_defaults()

        porta_st = cfg.get("porta", {}) if isinstance(cfg.get("porta"), dict) else {}
        janela_st = cfg.get("janela", {}) if isinstance(cfg.get("janela"), dict) else {}
        vm_st = cfg.get("vm", {}) if isinstance(cfg.get("vm"), dict) else {}

        porta_existe = bool(porta_st.get("existe", False))
        if porta_existe:
            center = float(porta_st.get("center_frac", 0.5))
            a, b = _door_segment_from_center(center, DOOR_WIDTH_FRAC)
            porta = {"existe": True, "inicio_frac": a, "fim_frac": b}
        else:
            porta = {"existe": False, "inicio_frac": None, "fim_frac": None}

        janela_existe = bool(janela_st.get("existe", False))
        if janela_existe:
            try:
                a = _clamp01(float(janela_st.get("inicio_frac", 0.0)))
                b = _clamp01(float(janela_st.get("fim_frac", 1.0)))
                if b < a:
                    a, b = b, a
                if abs(b - a) < 1e-6:
                    janela = {"existe": False, "inicio_frac": None, "fim_frac": None}
                else:
                    janela = {"existe": True, "inicio_frac": a, "fim_frac": b}
            except Exception:
                janela = {"existe": False, "inicio_frac": None, "fim_frac": None}
        else:
            janela = {"existe": False, "inicio_frac": None, "fim_frac": None}

        vm_existe = bool(vm_st.get("existe", False))
        if vm_existe:
            try:
                pf = _clamp01(float(vm_st.get("pos_frac", 0.5)))
            except Exception:
                pf = 0.5
            vm = {"existe": True, "pos_frac": pf}
        else:
            vm = {"existe": False, "pos_frac": 0.5}

        paredes[w] = {"porta": porta, "janela": janela, "vm": vm}

    return {
        "orientacao_topo": "Norte",
        "dimensoes": {
            "largura_m": float(dims.get("largura_m", 8.0)),
            "profundidade_m": float(dims.get("profundidade_m", 6.0)),
        },
        "paredes": paredes,
        "pontos_medicao": _measurement_points_def(),
    }


# =============================================================================
# 3) PREVIEW (SVG/HTML) + EXPORT PNG (matplotlib)
# =============================================================================
def _render_layout_preview(payload: Dict[str, Any]) -> None:
    W, H, pad = 520, 360, 90

    dims = payload.get("dimensoes", {}) if isinstance(payload.get("dimensoes"), dict) else {}
    largura_m = max(0.1, float(dims.get("largura_m", 8.0) or 8.0))
    profundidade_m = max(0.1, float(dims.get("profundidade_m", 6.0) or 6.0))

    drawable_w = W - 2 * pad
    drawable_h = H - 2 * pad
    target_ratio = profundidade_m / largura_m
    drawable_ratio = drawable_h / drawable_w

    if drawable_ratio >= target_ratio:
        room_w = drawable_w
        room_h = room_w * target_ratio
    else:
        room_h = drawable_h
        room_w = room_h / target_ratio

    cx, cy = W / 2, H / 2
    x0, x1 = cx - room_w / 2, cx + room_w / 2
    y0, y1 = cy - room_h / 2, cy + room_h / 2

    def line(xa, ya, xb, yb, stroke="#000", sw=2, opacity=1.0):
        return f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'

    def rect(x, y, w, h, stroke="#000", fill="none", sw=2):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" stroke="{stroke}" fill="{fill}" stroke-width="{sw}"/>'

    def text(x, y, t, size=12, anchor="middle", fill="#000"):
        t = str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{fill}">{t}</text>'

    def sqrect(cx_, cy_, size=8, fill="#000"):
        s = size
        return f'<rect x="{cx_ - s/2}" y="{cy_ - s/2}" width="{s}" height="{s}" fill="{fill}" stroke="{fill}" stroke-width="0"/>'

    def seg_from_fracs(total_len: float, a: float, b: float) -> Tuple[float, float]:
        a = _clamp01(a); b = _clamp01(b)
        if b < a:
            a, b = b, a
        return (total_len * a, total_len * b)

    def xy_from_fracs(xf: float, yf: float) -> Tuple[float, float]:
        x = x0 + (x1 - x0) * _clamp01(xf)
        y = y0 + (y1 - y0) * _clamp01(yf)
        return x, y

    parts: List[str] = []
    parts.append(rect(x0, y0, x1 - x0, y1 - y0, stroke=COLOR_WALL, sw=3))
    parts.append(text((x0 + x1) / 2, y0 - 24, "Norte", size=12))
    parts.append(text(x1 + 42, (y0 + y1) / 2, "Leste", size=12, anchor="start"))
    parts.append(text((x0 + x1) / 2, y1 + 34, "Sul", size=12))
    parts.append(text(x0 - 42, (y0 + y1) / 2, "Oeste", size=12, anchor="end"))

    for frac in (1 / 3, 2 / 3):
        xv = x0 + (x1 - x0) * frac
        yh = y0 + (y1 - y0) * frac
        parts.append(line(xv, y0, xv, y1, stroke=COLOR_GRID, sw=1, opacity=0.8))
        parts.append(line(x0, yh, x1, yh, stroke=COLOR_GRID, sw=1, opacity=0.8))

    paredes = payload.get("paredes", {}) if isinstance(payload.get("paredes"), dict) else {}
    inv = {"Norte": "top", "Sul": "bottom", "Leste": "right", "Oeste": "left"}

    wall_len_h = (x1 - x0)
    wall_len_v = (y1 - y0)

    for wall_label in ("Norte", "Sul", "Leste", "Oeste"):
        side = inv.get(wall_label)
        cfg = paredes.get(wall_label, {})
        if not side or not isinstance(cfg, dict):
            continue

        porta = cfg.get("porta", {}) if isinstance(cfg.get("porta"), dict) else {}
        janela = cfg.get("janela", {}) if isinstance(cfg.get("janela"), dict) else {}
        vm = cfg.get("vm", {}) if isinstance(cfg.get("vm"), dict) else {}

        if janela.get("existe") is True and janela.get("inicio_frac") is not None and janela.get("fim_frac") is not None:
            a = float(janela["inicio_frac"]); b = float(janela["fim_frac"])
            if side in ("top", "bottom"):
                sa, sb = seg_from_fracs(wall_len_h, a, b)
                xa, xb = x0 + sa, x0 + sb
                y = y0 if side == "top" else y1
                parts.append(line(xa, y, xb, y, stroke=COLOR_WINDOW, sw=6))
            else:
                sa, sb = seg_from_fracs(wall_len_v, a, b)
                ya, yb = y0 + sa, y0 + sb
                x = x1 if side == "right" else x0
                parts.append(line(x, ya, x, yb, stroke=COLOR_WINDOW, sw=6))

        if porta.get("existe") is True and porta.get("inicio_frac") is not None and porta.get("fim_frac") is not None:
            a = float(porta["inicio_frac"]); b = float(porta["fim_frac"])
            if side in ("top", "bottom"):
                sa, sb = seg_from_fracs(wall_len_h, a, b)
                xa, xb = x0 + sa, x0 + sb
                y = y0 if side == "top" else y1
                parts.append(line(xa, y, xb, y, stroke=COLOR_DOOR_GAP, sw=8))
                parts.append(line(xa, y, xb, y, stroke=COLOR_DOOR_EDGE, sw=1))
            else:
                sa, sb = seg_from_fracs(wall_len_v, a, b)
                ya, yb = y0 + sa, y0 + sb
                x = x1 if side == "right" else x0
                parts.append(line(x, ya, x, yb, stroke=COLOR_DOOR_GAP, sw=8))
                parts.append(line(x, ya, x, yb, stroke=COLOR_DOOR_EDGE, sw=1))

        if vm.get("existe") is True:
            pf = _clamp01(float(vm.get("pos_frac", 0.5)))
            if side == "top":
                x = x0 + wall_len_h * pf
                parts.append(rect(x - 15, y0 + 6, 36, 12, stroke=COLOR_VM_EDGE, fill=COLOR_VM_FILL, sw=2))
                parts.append(text(x, y0 + 32, "VM", size=9))
            elif side == "bottom":
                x = x0 + wall_len_h * pf
                parts.append(rect(x - 18, y1 - 18, 36, 12, stroke=COLOR_VM_EDGE, fill=COLOR_VM_FILL, sw=2))
                parts.append(text(x, y1 - 24, "VM", size=9))
            elif side == "right":
                y = y0 + wall_len_v * pf
                parts.append(rect(x1 - 18, y - 18, 12, 36, stroke=COLOR_VM_EDGE, fill=COLOR_VM_FILL, sw=2))
                parts.append(text(x1 + 24, y + 4, "VM", size=9, anchor="start"))
            else:
                y = y0 + wall_len_v * pf
                parts.append(rect(x0 + 6, y - 18, 12, 36, stroke=COLOR_VM_EDGE, fill=COLOR_VM_FILL, sw=2))
                parts.append(text(x0 - 24, y + 4, "VM", size=9, anchor="end"))

    pts = payload.get("pontos_medicao")
    if not isinstance(pts, list) or not pts:
        pts = _measurement_points_def()

    for p in pts:
        try:
            pid = str(p.get("id", "")).strip()
            xf = float(p.get("x_frac"))
            yf = float(p.get("y_frac"))
            tipo = str(p.get("tipo", "")).strip()
        except Exception:
            continue
        x, y = xy_from_fracs(xf, yf)
        col = COLOR_TA if tipo == "Ta" else COLOR_TS
        parts.append(sqrect(x, y, size=9, fill=col))
        parts.append(text(x, y - 12, pid, size=9, fill=col))

    svg_html = f"""
    <div style="border:1px solid #ddd; padding:10px; border-radius:8px; background:#fff;">
      <div style="font-size:14px; margin-bottom:8px;"><b>Estrutura do ambiente (preview)</b></div>
      <svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">
        {''.join(parts)}
      </svg>
      <div style="font-size:12px; color:#555; margin-top:6px;">
        Legenda:
        <span style="color:{COLOR_WINDOW};"><b>Janela</b></span> •
        <b>Porta</b> •
        <b>VM</b> •
        <span style="color:{COLOR_TA};"><b>Ta</b></span> •
        <span style="color:{COLOR_TS};"><b>Ts</b></span>
      </div>
    </div>
    """
    st.markdown(svg_html, unsafe_allow_html=True)


def _save_preview_png(payload: Dict[str, Any], out_path: Path) -> Tuple[bool, str]:
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    W, H, pad = 520, 360, 90

    dims = payload.get("dimensoes", {}) if isinstance(payload.get("dimensoes"), dict) else {}
    largura_m = max(0.1, float(dims.get("largura_m", 8.0) or 8.0))
    profundidade_m = max(0.1, float(dims.get("profundidade_m", 6.0) or 6.0))

    drawable_w = W - 2 * pad
    drawable_h = H - 2 * pad
    target_ratio = profundidade_m / largura_m
    drawable_ratio = drawable_h / drawable_w

    if drawable_ratio >= target_ratio:
        room_w = drawable_w
        room_h = room_w * target_ratio
    else:
        room_h = drawable_h
        room_w = room_h / target_ratio

    cx, cy = W / 2, H / 2
    x0, x1 = cx - room_w / 2, cx + room_w / 2
    y0, y1 = cy - room_h / 2, cy + room_h / 2

    def seg_from_fracs(total_len: float, a: float, b: float) -> Tuple[float, float]:
        a = _clamp01(a)
        b = _clamp01(b)
        if b < a:
            a, b = b, a
        return (total_len * a, total_len * b)

    def xy_from_fracs(xf: float, yf: float) -> Tuple[float, float]:
        x = x0 + (x1 - x0) * _clamp01(xf)
        y = y0 + (y1 - y0) * _clamp01(yf)
        return x, y

    paredes = payload.get("paredes", {}) if isinstance(payload.get("paredes"), dict) else {}

    try:
        fig = plt.figure(figsize=(W / 100, H / 100), dpi=200)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, W)
        ax.set_ylim(H, 0)
        ax.axis("off")

        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, linewidth=3, edgecolor=COLOR_WALL))
        ax.text((x0 + x1) / 2, y0 - 28, "Norte", ha="center", va="center", fontsize=12)
        ax.text(x1 + 35, (y0 + y1) / 2, "Leste", ha="left", va="center", fontsize=12)
        ax.text((x0 + x1) / 2, y1 + 30, "Sul", ha="center", va="center", fontsize=12)
        ax.text(x0 - 35, (y0 + y1) / 2, "Oeste", ha="right", va="center", fontsize=12)

        for frac in (1.0 / 3.0, 2.0 / 3.0):
            xv = x0 + (x1 - x0) * frac
            ax.plot([xv, xv], [y0, y1], color=COLOR_GRID, linewidth=0.8, alpha=0.8)
            yh = y0 + (y1 - y0) * frac
            ax.plot([x0, x1], [yh, yh], color=COLOR_GRID, linewidth=0.8, alpha=0.8)

        inv = {"Norte": "top", "Sul": "bottom", "Leste": "right", "Oeste": "left"}
        wall_len_h = (x1 - x0)
        wall_len_v = (y1 - y0)

        for wall_label in ("Norte", "Sul", "Leste", "Oeste"):
            side = inv.get(wall_label)
            cfg = paredes.get(wall_label, {})
            if not side or not isinstance(cfg, dict):
                continue

            porta = cfg.get("porta", {}) if isinstance(cfg.get("porta"), dict) else {}
            janela = cfg.get("janela", {}) if isinstance(cfg.get("janela"), dict) else {}
            vm = cfg.get("vm", {}) if isinstance(cfg.get("vm"), dict) else {}

            if janela.get("existe") is True and janela.get("inicio_frac") is not None and janela.get("fim_frac") is not None:
                a = float(janela["inicio_frac"]); b = float(janela["fim_frac"])
                if side in ("top", "bottom"):
                    sa, sb = seg_from_fracs(wall_len_h, a, b)
                    xa, xb = x0 + sa, x0 + sb
                    y = y0 if side == "top" else y1
                    ax.plot([xa, xb], [y, y], color=COLOR_WINDOW, linewidth=6, solid_capstyle="butt")
                else:
                    sa, sb = seg_from_fracs(wall_len_v, a, b)
                    ya, yb = y0 + sa, y0 + sb
                    x = x1 if side == "right" else x0
                    ax.plot([x, x], [ya, yb], color=COLOR_WINDOW, linewidth=6, solid_capstyle="butt")

            if porta.get("existe") is True and porta.get("inicio_frac") is not None and porta.get("fim_frac") is not None:
                a = float(porta["inicio_frac"]); b = float(porta["fim_frac"])
                if side in ("top", "bottom"):
                    sa, sb = seg_from_fracs(wall_len_h, a, b)
                    xa, xb = x0 + sa, x0 + sb
                    y = y0 if side == "top" else y1
                    ax.plot([xa, xb], [y, y], color=COLOR_DOOR_GAP, linewidth=8, solid_capstyle="butt")
                    ax.plot([xa, xb], [y, y], color=COLOR_DOOR_EDGE, linewidth=1, solid_capstyle="butt")
                else:
                    sa, sb = seg_from_fracs(wall_len_v, a, b)
                    ya, yb = y0 + sa, y0 + sb
                    x = x1 if side == "right" else x0
                    ax.plot([x, x], [ya, yb], color=COLOR_DOOR_GAP, linewidth=8, solid_capstyle="butt")
                    ax.plot([x, x], [ya, yb], color=COLOR_DOOR_EDGE, linewidth=1, solid_capstyle="butt")

            if vm.get("existe") is True:
                pf = _clamp01(float(vm.get("pos_frac", 0.5)))
                if side == "top":
                    x = x0 + wall_len_h * pf
                    ax.add_patch(Rectangle((x - 18, y0 + 6), 36, 12, linewidth=2, edgecolor=COLOR_VM_EDGE, facecolor=COLOR_VM_FILL))
                elif side == "bottom":
                    x = x0 + wall_len_h * pf
                    ax.add_patch(Rectangle((x - 18, y1 - 18), 36, 12, linewidth=2, edgecolor=COLOR_VM_EDGE, facecolor=COLOR_VM_FILL))
                elif side == "right":
                    y = y0 + wall_len_v * pf
                    ax.add_patch(Rectangle((x1 - 18, y - 18), 12, 36, linewidth=2, edgecolor=COLOR_VM_EDGE, facecolor=COLOR_VM_FILL))
                else:
                    y = y0 + wall_len_v * pf
                    ax.add_patch(Rectangle((x0 + 6, y - 18), 12, 36, linewidth=2, edgecolor=COLOR_VM_EDGE, facecolor=COLOR_VM_FILL))

        pts = payload.get("pontos_medicao")
        if not isinstance(pts, list) or not pts:
            pts = _measurement_points_def()

        sq = 7.0
        for p in pts:
            try:
                pid = str(p.get("id", "")).strip()
                xf = float(p.get("x_frac"))
                yf = float(p.get("y_frac"))
                tipo = str(p.get("tipo", "")).strip()
            except Exception:
                continue
            x, y = xy_from_fracs(xf, yf)
            col = COLOR_TA if tipo == "Ta" else COLOR_TS
            ax.add_patch(Rectangle((x - sq / 2, y - sq / 2), sq, sq, facecolor=col, edgecolor=col, linewidth=0))
            ax.text(x, y - 12, pid, ha="center", va="bottom", fontsize=8, color=col)

        fig.savefig(out_path, format="png", bbox_inches="tight", pad_inches=0.05)
        plt.close(fig)
        return True, f"Imagem salva em: {out_path.name}"
    except Exception as e:
        try:
            plt.close("all")
        except Exception:
            pass
        return False, f"Falha ao gerar PNG. Motivo: {e}"


# =============================================================================
# 4) EDITOR DE PAREDES (porta/janela/vm) - mesmo padrão do anexo
# =============================================================================
def _yes_no_inline(label: str, state_key: str, default: str = "Não") -> bool:
    current = st.session_state.get(state_key, default)
    if current not in ("Sim", "Não"):
        current = default
        st.session_state[state_key] = current

    cols = st.columns([3, 1, 1], vertical_alignment="center")
    with cols[0]:
        st.markdown(f"**{label}**")
    with cols[1]:
        if st.button("✅ Sim" if current == "Sim" else "Sim", key=f"{state_key}__sim", use_container_width=True):
            st.session_state[state_key] = "Sim"
    with cols[2]:
        if st.button("❌ Não" if current == "Não" else "Não", key=f"{state_key}__nao", use_container_width=True):
            st.session_state[state_key] = "Não"

    return st.session_state.get(state_key, default) == "Sim"


def _render_wall_editor(stage: StageContext, wall_name: str) -> None:
    paredes = stage.state.get("paredes_aberturas", {})
    cfg = paredes.get(wall_name, _wall_defaults())
    if not isinstance(cfg, dict):
        cfg = _wall_defaults()

    st.subheader(f"Parede {wall_name}")

    porta_cfg = cfg.get("porta", {}) if isinstance(cfg.get("porta"), dict) else {}
    janela_cfg = cfg.get("janela", {}) if isinstance(cfg.get("janela"), dict) else {}
    vm_cfg = cfg.get("vm", {}) if isinstance(cfg.get("vm"), dict) else {}

    porta_key = f"{STAGE_ID}_porta_{wall_name}"
    porta_existe = _yes_no_inline("Porta existe?", porta_key, default="Sim" if porta_cfg.get("existe") else "Não")
    porta_cfg["existe"] = porta_existe
    if porta_existe:
        porta_cfg["center_frac"] = float(
            st.slider(
                "Posição da porta (0 = início da parede, 1 = fim da parede)",
                min_value=0.0,
                max_value=1.0,
                value=float(porta_cfg.get("center_frac", 0.5)),
                step=0.01,
                key=f"{STAGE_ID}_porta_center_{wall_name}",
            )
        )

    janela_key = f"{STAGE_ID}_janela_{wall_name}"
    janela_existe = _yes_no_inline("Janela existe?", janela_key, default="Sim" if janela_cfg.get("existe") else "Não")
    janela_cfg["existe"] = janela_existe
    if janela_existe:
        a, b = float(janela_cfg.get("inicio_frac", 0.0)), float(janela_cfg.get("fim_frac", 1.0))
        if b < a:
            a, b = b, a
        inicio_fim = st.slider(
            "Trecho da janela (início e fim ao longo da parede)",
            min_value=0.0,
            max_value=1.0,
            value=(float(a), float(b)),
            step=0.01,
            key=f"{STAGE_ID}_janela_range_{wall_name}",
        )
        janela_cfg["inicio_frac"] = float(inicio_fim[0])
        janela_cfg["fim_frac"] = float(inicio_fim[1])

    vm_key = f"{STAGE_ID}_vm_{wall_name}"
    vm_existe = _yes_no_inline("Ventilação mecânica (VM) existe?", vm_key, default="Sim" if vm_cfg.get("existe") else "Não")
    vm_cfg["existe"] = vm_existe
    if vm_existe:
        vm_cfg["pos_frac"] = float(
            st.slider(
                "Posição da VM (0 = início da parede, 1 = fim da parede)",
                min_value=0.0,
                max_value=1.0,
                value=float(vm_cfg.get("pos_frac", 0.5)),
                step=0.01,
                key=f"{STAGE_ID}_vm_pos_{wall_name}",
            )
        )

    cfg["porta"] = porta_cfg
    cfg["janela"] = janela_cfg
    cfg["vm"] = vm_cfg

    paredes[wall_name] = cfg
    stage.state["paredes_aberturas"] = paredes


# =============================================================================
# 5) UI (ORIENTAÇÃO/DIMENSÕES + PAREDES + PREVIEW + EXPORT PNG)
# =============================================================================
def render_estrutura(stage: StageContext, ctx: Dict[str, Any]) -> None:
    _init_walls_if_needed(stage)

    st.write(
        "Posicione-se voltado para o Norte e identifique quais paredes estão ao "
        "Norte, Sul, Leste e Oeste do ambiente. "
        "Neste desenho, o Norte é sempre o topo (padrão fixo)."
    )

    od = stage.state.get("orientacao_dimensoes", {})
    if not isinstance(od, dict):
        od = {}
    od["orientacao_topo"] = "Norte"

    dims = od.get("dimensoes", {"largura_m": 8.0, "profundidade_m": 6.0})
    if not isinstance(dims, dict):
        dims = {"largura_m": 8.0, "profundidade_m": 6.0}

    c1, c2 = st.columns(2)
    with c1:
        dims["largura_m"] = float(
            st.number_input(
                "Largura (m) — eixo Leste–Oeste",
                min_value=2.0,
                max_value=50.0,
                value=float(dims.get("largura_m", 8.0)),
                key=f"{STAGE_ID}_largura_m",
            )
        )
    with c2:
        dims["profundidade_m"] = float(
            st.number_input(
                "Profundidade (m) — eixo Norte–Sul",
                min_value=2.0,
                max_value=50.0,
                value=float(dims.get("profundidade_m", 6.0)),
                key=f"{STAGE_ID}_profundidade_m",
            )
        )

    od["dimensoes"] = dims
    stage.state["orientacao_dimensoes"] = od

    st.markdown("## Paredes e aberturas")
    _render_wall_editor(stage, "Norte")
    _render_wall_editor(stage, "Sul")
    _render_wall_editor(stage, "Leste")
    _render_wall_editor(stage, "Oeste")

    if st.button("Salvar", type="primary", key=f"{STAGE_ID}_salvar"):
        save(stage, ctx)
        st.success("Dados salvos.")

    st.markdown("## Estrutura do ambiente")
    layout_payload = _build_layout_payload(stage)
    stage.state["estrutura_ambiente"] = layout_payload
    _render_layout_preview(layout_payload)

    st.markdown(" ")

    if st.button("Gerar figura (PNG)", key=f"{STAGE_ID}_export_png"):
        out_path = figura_path(ctx)  # caminho absoluto para escrever o arquivo
        ok, msg = _save_preview_png(layout_payload, out_path)
        if ok:
            st.success(msg)
        else:
            st.error(msg)


def save(stage: StageContext, ctx: Dict[str, Any]) -> None:
    payload = {
        "orientacao_dimensoes": stage.state.get("orientacao_dimensoes", {}),
        "paredes_aberturas": stage.state.get("paredes_aberturas", {}),
        "estrutura_ambiente": stage.state.get("estrutura_ambiente", {}),
        # SALVA RELATIVO (não vaza G:\..., e funciona no GitHub)
        "figura_png": figura_relpath(ctx),
    }
    save_stage_overwrite(stage.container_path, ctx, stage.stage_id, payload)


# =============================================================================
# 6) ENTRYPOINT
# =============================================================================
def render(ctx: Dict[str, Any]) -> None:
    stage = build_context(ctx)
    render_estrutura(stage, ctx)
