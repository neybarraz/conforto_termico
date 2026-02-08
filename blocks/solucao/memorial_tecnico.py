# blocks/solucao/memorial_tecnico.py
# =============================================================================
# 2) MEMORIAL TÉCNICO (TEMPLATE ORIENTADOR) — SOLUÇÃO
#
# Persistência:
# - JSON do bloco: data/solucao/memorial_tecnico_<nome_do_aluno>.json
# - PDF (opcional): data/pdf/memorial_tecnico_<nome_do_aluno>.pdf
# - FIGURA: data/figuras/<aluno>_heatmap.png
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import re
import streamlit as st

from storage.paths import stage_path
from storage.io_csv import load_json, save_json

STAGE_ID = "solucao_memorial_tecnico"

# =============================================================================
# (Opcional) PDF — ReportLab
# =============================================================================
try:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image as RLImage,
    )

    REPORTLAB_OK = True
    REPORTLAB_ERR = None
except Exception as err:
    REPORTLAB_OK = False
    REPORTLAB_ERR = err


# =============================================================================
# 0) CONFIG — PONTO ÚNICO PARA AJUSTES RÁPIDOS
# =============================================================================
@dataclass(frozen=True)
class MemorialConfig:
    titulo_base: str = "Memorial Técnico — Conforto Térmico"
    referencias_obrigatorias: bool = False
    orientacao_topo: str = (
        "Escreva com linguagem técnica e impessoal. Separe dado de interpretação. "
        "Evite julgamentos subjetivos sem evidência. Use causalidade física (\"isso ocorre porque...\")."
    )
    conceitos_opcoes: List[str] = (
        "Temperatura (interpretação microscópica)",
        "Equilíbrio térmico (corpo-ambiente)",
        "Condução",
        "Convecção natural",
        "Convecção forçada",
        "Radiação térmica",
        "Ar como fluido térmico (mistura/renovação)",
        "Primeira Lei da Termodinâmica (balanço de energia)",
    )
    implicacoes_opcoes: List[str] = (
        "Abertura/fechamento de janelas altera o balanço energético percebido",
        "Ventilação forçada muda a taxa de troca de energia por convecção",
        "Sombreamento/insolação impacta Ts e as trocas radiativas",
        "Distribuição de pessoas influencia o estado térmico do ar",
        "Outra implicação (descrever abaixo)",
    )
    mecanismo_opcoes: List[str] = (
        "",
        "Condução",
        "Convecção natural",
        "Convecção forçada",
        "Radiação térmica",
        "Combinação de mecanismos",
    )

    # --- política do PDF ---
    pdf_incluir_mini_tabela_stats: bool = True
    pdf_mini_tabela_stats_max_linhas: int = 12
    pdf_incluir_dados_brutos: bool = False
    pdf_incluir_comp_por_ponto: bool = False

    # --- figura (padronização) ---
    fig_square_size_px: int = 1024
    fig_square_pad_ratio: float = 0.06  # 6% padding em todos os lados
    pdf_fig_width_frac: float = 0.50    # 50% da largura útil do PDF

    # --- mapa (para ficar igual ao da INVESTIGAÇÃO) ---
    mapa_n: int = 80
    mapa_power: float = 2.0


CFG = MemorialConfig()


# =============================================================================
# helpers: state, persistência, leitura de outros blocos
# =============================================================================
def _ctx_get_state(ctx: Dict) -> Dict[str, Any]:
    if isinstance(ctx, dict) and isinstance(ctx.get("state"), dict):
        return ctx["state"]
    key = "__pbl_state__solucao_memorial_tecnico"
    if key not in st.session_state:
        st.session_state[key] = {}
    return st.session_state[key]


def _get(state: Dict[str, Any], k: str, default: Any) -> Any:
    return state.get(k, default)


def _set(state: Dict[str, Any], k: str, v: Any) -> None:
    state[k] = v


def _nonempty(x: Any) -> bool:
    return isinstance(x, str) and len(x.strip()) > 0


def _hydrate_state_from_saved(state: Dict[str, Any], saved: Dict[str, Any]) -> None:
    if not isinstance(saved, dict):
        return
    for k, v in saved.items():
        if k not in state:
            state[k] = v


def _safe_stage_data(ctx: Dict, stage_id: str) -> Dict[str, Any]:
    try:
        p = stage_path(ctx, stage_id)
        d = load_json(p) or {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _as_list_str(x: Any) -> List[str]:
    if isinstance(x, list):
        return [str(i) for i in x if str(i).strip()]
    return []


def _nl_to_br(s: str) -> str:
    return (s or "").replace("\n", "<br/>").strip()


# =============================================================================
# Persistência universal (padrão por aluno)
# =============================================================================
def _sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "anon"
    s = s.lower().replace(" ", "_")
    s = re.sub(r"[^a-z0-9_\-]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "anon"


def _get_aluno_name(ctx: Dict) -> str:
    if not isinstance(ctx, dict):
        return "anon"
    for k in ("aluno", "student", "nome", "nome_aluno", "user", "usuario"):
        v = ctx.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    stt = ctx.get("state")
    if isinstance(stt, dict):
        for k in ("aluno", "student", "nome", "nome_aluno", "user", "usuario"):
            v = stt.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return "anon"


def _memorial_path(ctx: Dict) -> Path:
    aluno = _sanitize_filename(_get_aluno_name(ctx))
    p = Path("data") / "solucao" / f"memorial_tecnico_{aluno}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _pdf_path(ctx: Dict) -> Path:
    aluno = _sanitize_filename(_get_aluno_name(ctx))
    p = Path("data") / "pdf" / f"{aluno}_04_memorial_tecnico.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _fig_heatmap_path(ctx: Dict) -> Path:
    aluno = _sanitize_filename(_get_aluno_name(ctx))
    p = Path("data") / "figuras" / f"{aluno}_heatmap.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# =============================================================================
# Payload
# =============================================================================
def _build_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "capa_titulo": _get(state, "capa_titulo", ""),
        "capa_ambiente": _get(state, "capa_ambiente", ""),
        "capa_disciplina": _get(state, "capa_disciplina", ""),
        "capa_instituicao": _get(state, "capa_instituicao", ""),
        "capa_periodo": _get(state, "capa_periodo", ""),
        "capa_integrantes": _get(state, "capa_integrantes", ""),
        "capa_professor": _get(state, "capa_professor", ""),
        "capa_data": _get(state, "capa_data", ""),
        "intro_contextualizacao": _get(state, "intro_contextualizacao", ""),
        "intro_desconforto": _get(state, "intro_desconforto", ""),
        "intro_justificativa_fisica": _get(state, "intro_justificativa_fisica", ""),
        "intro_pergunta_norteadora": _get(state, "intro_pergunta_norteadora", ""),
        "fund_conceitos_sel": _as_list_str(_get(state, "fund_conceitos_sel", [])),
        "fund_modelo_mental": _get(state, "fund_modelo_mental", ""),
        "fund_mecanismos": _get(state, "fund_mecanismos", ""),
        "fund_primeira_lei": _get(state, "fund_primeira_lei", ""),
        "met_sistema_fisico": _get(state, "met_sistema_fisico", ""),
        "met_grandezas": _get(state, "met_grandezas", ""),
        "met_instrumentos": _get(state, "met_instrumentos", ""),
        "met_procedimentos": _get(state, "met_procedimentos", ""),
        "met_condicoes": _get(state, "met_condicoes", ""),
        "resumo_dados": _get(state, "resumo_dados", ""),
        "analise_gradientes": _get(state, "analise_gradientes", ""),
        "analise_equilibrio": _get(state, "analise_equilibrio", ""),
        "analise_mecanismo_dom": _get(state, "analise_mecanismo_dom", ""),
        "analise_mecanismo_just": _get(state, "analise_mecanismo_just", ""),
        "analise_conforto": _get(state, "analise_conforto", ""),
        "conc_resposta": _get(state, "conc_resposta", ""),
        "conc_sintese": _get(state, "conc_sintese", ""),
        "conc_implic_sel": _as_list_str(_get(state, "conc_implic_sel", [])),
        "conc_implic_outra": _get(state, "conc_implic_outra", ""),
        "lim_texto": _get(state, "lim_texto", ""),
        "lim_incertezas": _get(state, "lim_incertezas", ""),
        "lim_variaveis_nao_controladas": _get(state, "lim_variaveis_nao_controladas", ""),
        "lim_melhorias": _get(state, "lim_melhorias", ""),
        "lim_futuros": _get(state, "lim_futuros", ""),
        "refs_texto": _get(state, "refs_texto", ""),
        "concluido": bool(_get(state, "concluido", False)),
    }


def _compute_faltas(state: Dict[str, Any]) -> List[str]:
    faltas: List[str] = []
    if not _nonempty(_get(state, "capa_titulo", "")):
        faltas.append("- Preencha: título técnico na capa (0.1).")
    if not _nonempty(_get(state, "capa_ambiente", "")):
        faltas.append("- Preencha: identificação do ambiente na capa (0.2).")
    if not _nonempty(_get(state, "capa_integrantes", "")):
        faltas.append("- Preencha: integrantes do grupo na capa (0.3).")

    if not _nonempty(_get(state, "intro_contextualizacao", "")):
        faltas.append("- Preencha: contextualização objetiva do ambiente (1.1).")
    if not _nonempty(_get(state, "intro_desconforto", "")):
        faltas.append("- Preencha: descrição clara do desconforto observado (1.2).")
    if not _nonempty(_get(state, "intro_justificativa_fisica", "")):
        faltas.append("- Preencha: justificativa física do problema (1.3).")
    if not _nonempty(_get(state, "intro_pergunta_norteadora", "")):
        faltas.append("- Preencha: pergunta norteadora explícita (1.4).")

    if len(_as_list_str(_get(state, "fund_conceitos_sel", []))) == 0:
        faltas.append("- Marque ao menos 1 conceito na fundamentação (2.1).")
    if not _nonempty(_get(state, "fund_modelo_mental", "")):
        faltas.append("- Preencha: modelo físico mental do sistema (2.2).")
    if not _nonempty(_get(state, "fund_mecanismos", "")):
        faltas.append("- Preencha: mecanismos de transferência e papel do ar (2.3).")
    if not _nonempty(_get(state, "fund_primeira_lei", "")):
        faltas.append("- Preencha: leitura pela Primeira Lei (2.4).")

    if not _nonempty(_get(state, "met_sistema_fisico", "")):
        faltas.append("- Preencha: definição do sistema físico estudado (3.1).")
    if not _nonempty(_get(state, "met_grandezas", "")):
        faltas.append("- Preencha: grandezas medidas e justificativa física (3.2).")
    if not _nonempty(_get(state, "met_instrumentos", "")):
        faltas.append("- Preencha: instrumentos e limitações (3.3).")
    if not _nonempty(_get(state, "met_procedimentos", "")):
        faltas.append("- Preencha: procedimentos de medição (3.4).")
    if not _nonempty(_get(state, "met_condicoes", "")):
        faltas.append("- Preencha: condições ambientais registradas (3.5).")

    if not _nonempty(_get(state, "resumo_dados", "")):
        faltas.append("- Preencha: organização/descrição dos resultados (4.1).")
    if not _nonempty(_get(state, "analise_gradientes", "")):
        faltas.append("- Preencha: análise de gradientes/padrões (4.2).")
    if not _nonempty(_get(state, "analise_equilibrio", "")):
        faltas.append("- Preencha: discussão de equilíbrio (ou não) (4.3).")
    if _get(state, "analise_mecanismo_dom", "") == "":
        faltas.append("- Selecione: mecanismo dominante (4.4).")
    if not _nonempty(_get(state, "analise_mecanismo_just", "")):
        faltas.append("- Preencha: justificativa do mecanismo dominante (4.4.1).")
    if not _nonempty(_get(state, "analise_conforto", "")):
        faltas.append("- Preencha: relação dados → conforto percebido (4.5).")

    if not _nonempty(_get(state, "conc_resposta", "")):
        faltas.append("- Preencha: resposta direta à pergunta norteadora (5.1).")

    if not _nonempty(_get(state, "lim_texto", "")):
        faltas.append("- Preencha: limitações (6.1).")
    if not _nonempty(_get(state, "lim_melhorias", "")):
        faltas.append("- Preencha: melhorias possíveis (6.2).")
    if not _nonempty(_get(state, "lim_futuros", "")):
        faltas.append("- Preencha: aprofundamentos futuros (6.3).")

    if (
        "Outra implicação (descrever abaixo)" in _as_list_str(_get(state, "conc_implic_sel", []))
        and not _nonempty(_get(state, "conc_implic_outra", ""))
    ):
        faltas.append("- Preencha: implicação 'Outra' (5.3.1).")

    if CFG.referencias_obrigatorias and not _nonempty(_get(state, "refs_texto", "")):
        faltas.append("- Preencha: referências (7.1).")

    return faltas


def _save_all(path_json: Path, state: Dict[str, Any]) -> None:
    faltas = _compute_faltas(state)
    concluido = len(faltas) == 0
    _set(state, "concluido", bool(concluido))

    payload = _build_payload(state)
    payload["concluido"] = bool(concluido)

    save_json(path_json, payload)

    if concluido:
        st.success("Salvo e marcado como concluído.")
    else:
        st.success("Salvo. Ainda há pendências para concluir.")


def _render_save_button(path_json: Path, state: Dict[str, Any], key_suffix: str) -> None:
    if st.button("Salvar", key=f"{STAGE_ID}_salvar_{key_suffix}"):
        _save_all(path_json, state)


# =============================================================================
# PDF helpers (ÚNICO E CORRETO)
# =============================================================================
def _build_pdf_bytes(titulo: str, sections: List[Dict[str, Any]]) -> bytes:
    if not REPORTLAB_OK:
        raise RuntimeError(f"ReportLab indisponível: {REPORTLAB_ERR}")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=48,
        bottomMargin=48,
        title=titulo,
        allowSplitting=1,
    )

    styles = getSampleStyleSheet()
    h1 = styles["Title"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    body_compact = ParagraphStyle(
        "BodyCompact",
        parent=body,
        leading=12,
        spaceAfter=6,
    )

    story: List[Any] = []
    story.append(Paragraph(titulo, h1))
    story.append(Spacer(1, 10))

    for sec in sections:
        story.append(Paragraph(str(sec.get("h", "")).strip(), h2))

        txt = sec.get("body", "")
        story.append(Paragraph(_nl_to_br(txt) if _nonempty(txt) else "(não preenchido)", body_compact))
        story.append(Spacer(1, 8))

        tbls = sec.get("tables")
        if isinstance(tbls, list) and tbls:
            for tinfo in tbls:
                if not (isinstance(tinfo, dict) and isinstance(tinfo.get("data"), list) and tinfo["data"]):
                    continue

                title_tbl = str(tinfo.get("title", "")).strip()
                if title_tbl:
                    story.append(Paragraph(title_tbl, body_compact))
                    story.append(Spacer(1, 4))

                t = Table(
                    tinfo["data"],
                    repeatRows=1,
                    splitByRow=1,
                )
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                            ("LEFTPADDING", (0, 0), (-1, -1), 4),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ]
                    )
                )
                story.append(t)
                story.append(Spacer(1, 10))

        img_bytes = sec.get("image_bytes")
        if isinstance(img_bytes, (bytes, bytearray)) and len(img_bytes) > 0:
            frac = sec.get("image_w_frac", CFG.pdf_fig_width_frac)
            try:
                frac = float(frac)
            except Exception:
                frac = CFG.pdf_fig_width_frac
            frac = max(0.10, min(1.00, frac))

            w_pt = doc.width * frac
            h_pt = w_pt  # quadrado (o PNG será padronizado 1:1)

            story.append(RLImage(BytesIO(bytes(img_bytes)), width=w_pt, height=h_pt))

            cap = str(sec.get("image_caption", "")).strip()
            if cap:
                story.append(Spacer(1, 4))
                story.append(Paragraph(cap, body_compact))
            story.append(Spacer(1, 10))

    doc.build(story)
    return buf.getvalue()


def _records_to_table(records: List[Dict[str, Any]], max_rows: int = 40) -> List[List[str]]:
    if not isinstance(records, list) or len(records) == 0:
        return [["(sem dados)"]]

    cols: List[str] = []
    for r in records:
        if isinstance(r, dict):
            for k in r.keys():
                if k not in cols:
                    cols.append(k)

    if not cols:
        return [["(sem dados)"]]

    rows: List[List[str]] = [cols]
    for r in records[:max_rows]:
        if not isinstance(r, dict):
            continue
        line: List[str] = []
        for c in cols:
            v = r.get(c, "")
            if v is None:
                v = ""
            s = str(v).replace("\n", " ").strip()
            if len(s) > 120:
                s = s[:117] + "..."
            line.append(s)
        rows.append(line)

    if len(records) > max_rows:
        rows.append([f"(mostrando {max_rows} de {len(records)} linhas)"] + [""] * (len(cols) - 1))
    return rows


# =============================================================================
# Seção 4 — helpers
# =============================================================================
def _altair_to_png_bytes(chart) -> Tuple[bytes, str]:
    try:
        from io import BytesIO as _BIO

        buf = _BIO()
        chart.save(buf, format="png", engine="vl-convert")
        return buf.getvalue(), ""
    except Exception as e:
        return b"", f"{type(e).__name__}: {e}"


def _pad_png_to_square(png_bytes: bytes, out_size: int, pad_ratio: float) -> bytes:
    try:
        from io import BytesIO
        from PIL import Image
    except Exception:
        return png_bytes

    im = Image.open(BytesIO(png_bytes)).convert("RGBA")
    canvas = Image.new("RGBA", (out_size, out_size), (255, 255, 255, 255))

    pad = int(out_size * float(pad_ratio))
    avail = max(1, out_size - 2 * pad)

    w, h = im.size
    if w <= 0 or h <= 0:
        return png_bytes

    scale = min(avail / w, avail / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    im2 = im.resize((nw, nh), Image.LANCZOS)

    x0 = (out_size - nw) // 2
    y0 = (out_size - nh) // 2
    canvas.alpha_composite(im2, (x0, y0))

    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def _to_df(rows: Any):
    import pandas as pd

    if not isinstance(rows, list) or len(rows) == 0:
        return pd.DataFrame()
    try:
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def _round_numeric_2(df):
    import pandas as pd

    if df is None or df.empty:
        return df

    out = df.copy()
    num_cols = out.select_dtypes(include=["number"]).columns.tolist()
    if num_cols:
        out[num_cols] = out[num_cols].round(2)

    for c in out.columns:
        if c in num_cols:
            continue
        if out[c].dtype == object:
            s = out[c].astype(str).str.replace(",", ".", regex=False)
            s_num = pd.to_numeric(s, errors="coerce")
            if s_num.notna().any() and (s_num.notna().mean() > 0.75):
                out[c] = s_num.round(2)
    return out


def _styler_2dec(df):
    df2 = _round_numeric_2(df)
    num_cols = df2.select_dtypes(include=["number"]).columns.tolist()
    styler = df2.style
    if num_cols:
        styler = styler.format({c: "{:.2f}" for c in num_cols})
    return styler


def _df_show_2dec(records: Any) -> None:
    df = _to_df(records)
    if df.empty:
        st.dataframe(df, use_container_width=True)
        return
    st.dataframe(_styler_2dec(df), use_container_width=True)


def _investigacao_path(ctx2: Dict) -> Path:
    aluno = _sanitize_filename(_get_aluno_name(ctx2))
    p = Path("data") / "investigacao" / f"investigacao_{aluno}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_investigacao(ctx2: Dict) -> Dict[str, Any]:
    try:
        p = _investigacao_path(ctx2)
        d = load_json(p) or {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _pick_stages(inv_all: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(inv_all.get("stages"), dict):
        return inv_all["stages"]
    if isinstance(inv_all.get("data"), dict) and isinstance(inv_all["data"].get("stages"), dict):
        return inv_all["data"]["stages"]
    return inv_all if isinstance(inv_all, dict) else {}


def _ponto_to_xy(ponto: str) -> Tuple[float, float]:
    p = (ponto or "").lower()
    if "janela" in p or "parede externa" in p:
        x, y = 0.10, 0.75
    elif "entre janela" in p:
        x, y = 0.30, 0.60
    elif "centro" in p and "entre" not in p:
        x, y = 0.50, 0.55
    elif "entre centro" in p:
        x, y = 0.70, 0.50
    elif "fundo" in p or "canto" in p:
        x, y = 0.90, 0.60
    elif "porta" in p or "corredor" in p:
        x, y = 0.10, 0.30
    elif "piso" in p or "superfície crítica" in p or "superficie critica" in p:
        x, y = 0.55, 0.15
    else:
        x, y = 0.50, 0.50
    return float(x), float(y)


def _safe_to_numeric(ser):
    import pandas as pd

    s = pd.Series(ser)
    if s.dtype == object:
        s = s.astype(str).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _find_col(df, keywords: List[str]) -> Optional[str]:
    cols = list(df.columns)
    low = [str(c).lower() for c in cols]
    for k in keywords:
        k2 = k.lower()
        for i, c in enumerate(low):
            if k2 in c:
                return cols[i]
    return None


def _detect_ponto_col(df) -> Optional[str]:
    return _find_col(df, ["ponto", "regiao", "região", "local", "posicao", "posição"])


def _detect_temp_cols(df) -> Tuple[Optional[str], Optional[str]]:
    ta = _find_col(df, ["ta", "temp_ar", "temperatura do ar", "temperatura_ar", "t_ar"])
    ts = _find_col(df, ["ts", "temp_superficie", "temperatura de superficie", "temperatura_superficie", "t_s"])
    if ta is None:
        ta = _find_col(df, ["temperatura", "temp"])
    return ta, ts


@st.cache_data(show_spinner=False)
def _idw_grid_cached(px, py, pv, n: int = 80, power: float = 2.0):
    """
    Retorna DataFrame com xi, yi (índices 0..n-1) e valor (interpolado).
    Mantém também x,y normalizados para debug (não usados no plot final).
    """
    import numpy as np
    import pandas as pd

    px = np.array(px, dtype=float)
    py = np.array(py, dtype=float)
    pv = np.array(pv, dtype=float)

    if len(px) == 0:
        return pd.DataFrame(columns=["xi", "yi", "x", "y", "valor"])

    xs = np.linspace(0.0, 1.0, n)
    ys = np.linspace(0.0, 1.0, n)

    rows = []
    eps = 1e-12
    for yi, y in enumerate(ys):
        for xi, x in enumerate(xs):
            dx = x - px
            dy = y - py
            d2 = dx * dx + dy * dy
            if np.any(d2 < eps):
                val = float(pv[int(np.argmin(d2))])
            else:
                d = np.sqrt(d2)
                w = 1.0 / np.power(d, power)
                val = float(np.sum(w * pv) / np.sum(w))
            rows.append({"xi": int(xi), "yi": int(yi), "x": float(x), "y": float(y), "valor": val})

    return pd.DataFrame(rows)


def _build_gradiente_chart(comp_por_ponto: List[Dict[str, Any]]):
    """
    IGUAL AO PADRÃO DA INVESTIGAÇÃO:
    - heatmap em grade discreta (xi/yi) -> dá “quadriculado”
    - pontos/labels também em xi/yi
    - y com sort="descending"
    Retorna: (chart|None, caption_txt, chosen_label)
    """
    import pandas as pd
    import altair as alt
    import numpy as np

    df = _to_df(comp_por_ponto)
    if df.empty:
        return None, "Sem dados de comparação por ponto.", ""

    col_ponto = _detect_ponto_col(df)
    if col_ponto is None:
        return None, "Não encontrei coluna de PONTO/REGIÃO em comparacao_por_ponto.", ""

    col_ta, col_ts = _detect_temp_cols(df)

    chosen = None
    label = ""
    if col_ta and col_ta in df.columns:
        chosen = col_ta
        label = "Ta"
    elif col_ts and col_ts in df.columns:
        chosen = col_ts
        label = "Ts"
    else:
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if num_cols:
            chosen = num_cols[0]
            label = str(chosen)
        else:
            # tenta converter colunas
            for c in df.columns:
                if c == col_ponto:
                    continue
                s = _safe_to_numeric(df[c])
                if s.notna().any():
                    df[c] = s
                    chosen = c
                    label = str(c)
                    break

    if not chosen or chosen not in df.columns:
        return None, "Não encontrei coluna numérica (Ta/Ts) para montar o gradiente.", ""

    pontos = df[col_ponto].astype(str).tolist()
    vals = _safe_to_numeric(df[chosen]).tolist()

    pts_rows = []
    for p, v in zip(pontos, vals):
        try:
            fv = float(v)
        except Exception:
            continue
        x, y = _ponto_to_xy(str(p))
        pts_rows.append({"ponto": str(p), "x": float(x), "y": float(y), "valor": float(fv)})

    if len(pts_rows) < 2:
        return None, "Poucos pontos válidos para interpolar.", ""

    dfp = pd.DataFrame(pts_rows)

    vmin = float(dfp["valor"].min())
    vmax = float(dfp["valor"].max())

    # Se min≈max, o mapa fica uniforme mesmo (isso é “correto” fisicamente).
    # Aqui a gente interrompe igual ao módulo da INVESTIGAÇÃO.
    if np.isclose(vmin, vmax):
        return None, "As temperaturas por ponto estão praticamente iguais (min≈max). O mapa tende a ficar uniforme.", label

    n = int(CFG.mapa_n)
    power = float(CFG.mapa_power)

    g = _idw_grid_cached(
        tuple(dfp["x"].tolist()),
        tuple(dfp["y"].tolist()),
        tuple(dfp["valor"].tolist()),
        n=n,
        power=power,
    )

    color_scale = alt.Scale(
        domain=[vmin, vmax],
        range=["#0000FF", "#00FFFF", "#00FF00", "#FFFF00", "#FF0000"],
        interpolate="rgb",
        clamp=True,
    )

    base = (
        alt.Chart(g)
        .mark_rect()
        .encode(
            x=alt.X("xi:O", axis=None),
            y=alt.Y("yi:O", axis=None, sort="descending"),
            color=alt.Color("valor:Q", title=f"{label} (°C)" if label in ("Ta", "Ts") else "Temp (°C)", scale=color_scale),
            tooltip=[alt.Tooltip("valor:Q", title="Temp (°C)", format=".2f")],
        )
        .properties(width=520, height=380)
    )

    dfp_plot = dfp.copy()
    dfp_plot["xi"] = (dfp_plot["x"] * (n - 1)).round().astype(int)
    dfp_plot["yi"] = (dfp_plot["y"] * (n - 1)).round().astype(int)

    pts = (
        alt.Chart(dfp_plot)
        .mark_point(filled=True, size=130)
        .encode(
            x=alt.X("xi:O", axis=None),
            y=alt.Y("yi:O", axis=None, sort="descending"),
            tooltip=[
                alt.Tooltip("ponto:N", title="Ponto"),
                alt.Tooltip("valor:Q", title="Temp (°C)", format=".2f"),
            ],
            color=alt.value("black"),
        )
    )

    labels = (
        alt.Chart(dfp_plot)
        .mark_text(align="left", dx=8, dy=-8)
        .encode(
            x=alt.X("xi:O", axis=None),
            y=alt.Y("yi:O", axis=None, sort="descending"),
            text=alt.Text("ponto:N"),
        )
    )

    chart = (base + pts + labels).configure_view(stroke=None)
    caption = f"Mapa espacial (IDW) usando {label} como variável base."
    return chart, caption, label


def _ensure_heatmap_png(ctx: Dict, state: Dict[str, Any], chart, chosen_label: str) -> Tuple[bool, str]:
    fig_path = _fig_heatmap_path(ctx)

    if fig_path.exists():
        try:
            png_bytes_disk = fig_path.read_bytes()
            if png_bytes_disk:
                state.setdefault("__sec4__", {})
                state["__sec4__"]["grad_png"] = png_bytes_disk
                state["__sec4__"]["grad_var_label"] = chosen_label
                state["__sec4__"]["grad_caption"] = f"Figura 4.1 — Gradiente espacial ({chosen_label})."
                state["__sec4__"]["grad_png_err"] = ""
                state["__sec4__"]["grad_png_path"] = fig_path.as_posix()
                return True, ""
            return False, "Arquivo existe, mas está vazio."
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    png_bytes, png_err = _altair_to_png_bytes(chart)
    if not png_bytes:
        return False, png_err or "Erro desconhecido ao gerar PNG."

    png_bytes_std = _pad_png_to_square(
        png_bytes,
        out_size=int(CFG.fig_square_size_px),
        pad_ratio=float(CFG.fig_square_pad_ratio),
    )

    try:
        fig_path.write_bytes(png_bytes_std)
    except Exception as e:
        return False, f"Falha ao salvar PNG: {type(e).__name__}: {e}"

    state.setdefault("__sec4__", {})
    state["__sec4__"]["grad_png"] = png_bytes_std
    state["__sec4__"]["grad_var_label"] = chosen_label
    state["__sec4__"]["grad_caption"] = f"Figura 4.1 — Gradiente espacial ({chosen_label})."
    state["__sec4__"]["grad_png_err"] = ""
    state["__sec4__"]["grad_png_path"] = fig_path.as_posix()
    return True, ""


# =============================================================================
# Prefill helpers
# =============================================================================
def _prefill_from_blocks(ctx: Dict) -> Dict[str, Any]:
    inv_proc = _safe_stage_data(ctx, "investigacao_procedimentos_mecanismos")
    inv_ativ = _safe_stage_data(ctx, "investigacao_atividades_praticas")
    inv_dados = _safe_stage_data(ctx, "investigacao_coleta_analise_dados")
    sol_reflex = _safe_stage_data(ctx, "solucao_reflexao_metacognicao")
    prob_def = _safe_stage_data(ctx, "problema_definicao_problema")
    prob_esc = _safe_stage_data(ctx, "problema_escopo_ambiente")
    prob_perg = _safe_stage_data(ctx, "problema_pergunta_norteadora")

    pergunta_norteadora = (
        prob_perg.get("pergunta_norteadora")
        or prob_perg.get("texto")
        or prob_perg.get("pergunta")
        or ""
    )

    ambiente = (
        prob_esc.get("ambiente_especifico")
        or prob_esc.get("ambiente")
        or prob_esc.get("texto")
        or ""
    )
    turno = prob_esc.get("turno", "")
    condicoes = prob_esc.get("condicoes", "")

    texto_problema = (
        prob_def.get("texto_problema")
        or prob_def.get("definicao_problema")
        or prob_def.get("texto")
        or ""
    )

    instrumentos = inv_proc.get("met_instrumentos", "") or ""

    cond_auto: List[str] = []
    if _nonempty(inv_ativ.get("cond_pessoas_faixa", "")):
        cond_auto.append(f"Pessoas: {inv_ativ.get('cond_pessoas_faixa','')}")
    if _nonempty(inv_ativ.get("cond_pessoas_detalhe", "")):
        cond_auto.append(f"Detalhe pessoas: {inv_ativ.get('cond_pessoas_detalhe','')}")
    if _nonempty(inv_ativ.get("cond_janelas_estado", "")):
        cond_auto.append(f"Janelas: {inv_ativ.get('cond_janelas_estado','')}")
    if _nonempty(inv_ativ.get("cond_janelas_detalhe", "")):
        cond_auto.append(f"Detalhe janelas: {inv_ativ.get('cond_janelas_detalhe','')}")
    if _nonempty(inv_ativ.get("cond_vent_tipo", "")) or _nonempty(inv_ativ.get("cond_vent_status", "")):
        cond_auto.append(
            f"Ventilação/AC: {inv_ativ.get('cond_vent_tipo','')} / {inv_ativ.get('cond_vent_status','')}".strip(" /")
        )
    if _nonempty(inv_ativ.get("cond_vent_detalhe", "")):
        cond_auto.append(f"Detalhe ventilação/AC: {inv_ativ.get('cond_vent_detalhe','')}")
    if _nonempty(inv_ativ.get("cond_insolacao", "")):
        cond_auto.append(f"Insolação: {inv_ativ.get('cond_insolacao','')}")
    if _nonempty(inv_ativ.get("cond_outros", "")):
        cond_auto.append(f"Outros: {inv_ativ.get('cond_outros','')}")

    lim_simpl = sol_reflex.get("lim_simplificacoes", "")
    lim_inc = sol_reflex.get("lim_incertezas", "")
    lim_var = sol_reflex.get("lim_variaveis_nao_controladas", "")

    data_records = inv_dados.get("data_records", [])

    return {
        "pergunta_norteadora": pergunta_norteadora,
        "ambiente": ambiente,
        "turno": turno,
        "condicoes": condicoes,
        "texto_problema": texto_problema,
        "instrumentos": instrumentos,
        "condicoes_auto": "\n".join(cond_auto).strip(),
        "lim_simplificacoes": lim_simpl,
        "lim_incertezas": lim_inc,
        "lim_variaveis_nao_controladas": lim_var,
        "data_records": data_records if isinstance(data_records, list) else [],
        "inv_proc": inv_proc,
        "inv_ativ": inv_ativ,
        "prob_esc": prob_esc,
    }


# =============================================================================
# RENDER
# =============================================================================
def render(ctx: Dict) -> None:
    path_json = _memorial_path(ctx)
    state = _ctx_get_state(ctx)

    if not _get(state, "__loaded__", False):
        saved = load_json(path_json) or {}
        _hydrate_state_from_saved(state, saved)
        _set(state, "__loaded__", True)

    pref = _prefill_from_blocks(ctx)

    st.title("Memorial Técnico")
    st.caption(CFG.orientacao_topo)
    st.markdown("---")

    # =========================================================================
    # 0) CAPA E IDENTIFICAÇÃO TÉCNICA
    # =========================================================================
    st.markdown("## Identificação Técnica")
    st.caption(
        "Critério: o texto deve deixar explícitos o sistema físico investigado e o ambiente estudado, "
        "de forma objetiva e sem ambiguidades."
    )

    capa_titulo = st.text_input(
        "Título técnico (claro e objetivo)",
        value=_get(state, "capa_titulo", CFG.titulo_base),
        key=f"{STAGE_ID}_capa_titulo",
        placeholder="Ex.: Análise das condições de conforto térmico em sala de aula do Bloco X",
    )
    _set(state, "capa_titulo", capa_titulo)

    ambiente_auto = pref.get("ambiente", "")
    if _nonempty(pref.get("turno", "")):
        ambiente_auto = (ambiente_auto + f" — Turno: {pref.get('turno','')}").strip(" —")
    if _nonempty(pref.get("condicoes", "")):
        ambiente_auto = (ambiente_auto + f"\nCondições típicas: {pref.get('condicoes','')}").strip()

    capa_ambiente = st.text_area(
        "Identificação do ambiente estudado",
        value=_get(state, "capa_ambiente", ambiente_auto),
        height=90,
        key=f"{STAGE_ID}_capa_ambiente",
        placeholder="Ex.: Sala 402 — Bloco A — Turno tarde — janelas com insolação direta etc.",
    )
    _set(state, "capa_ambiente", capa_ambiente)

    capa_disciplina = st.text_input(
        "Disciplina",
        value=_get(state, "capa_disciplina", ""),
        key=f"{STAGE_ID}_capa_disciplina",
        placeholder="Ex.: Física II, Física Geral",
    )
    _set(state, "capa_disciplina", capa_disciplina)

    capa_instituicao = st.text_input(
        "Instituição",
        value=_get(state, "capa_instituicao", ""),
        key=f"{STAGE_ID}_capa_instituicao",
        placeholder="UFFS / CL",
    )
    _set(state, "capa_instituicao", capa_instituicao)

    capa_periodo = st.text_input(
        "Período letivo",
        value=_get(state, "capa_periodo", ""),
        key=f"{STAGE_ID}_capa_periodo",
        placeholder="Ex.: 2026.1",
    )
    _set(state, "capa_periodo", capa_periodo)

    capa_integrantes = st.text_area(
        "Integrantes do grupo (um por linha)",
        value=_get(state, "capa_integrantes", ""),
        height=160,
        key=f"{STAGE_ID}_capa_integrantes",
        placeholder="Ex.: Einstein\nNewton\nDirac\nMaxwell\nGalileu",
    )
    _set(state, "capa_integrantes", capa_integrantes)

    capa_professor = st.text_input(
        "Professor",
        value=_get(state, "capa_professor", "Prof. Dr. Ney M. Barraz Jr."),
        key=f"{STAGE_ID}_capa_professor",
        placeholder="Prof. Dr. Ney M. Barraz Jr.",
    )
    _set(state, "capa_professor", capa_professor)

    capa_data = st.text_input(
        "Data",
        value=_get(state, "capa_data", ""),
        key=f"{STAGE_ID}_capa_data",
        placeholder="Ex.: 30/01/2026",
    )
    _set(state, "capa_data", capa_data)

    _render_save_button(path_json, state, "s0")
    st.markdown("---")

    # =========================================================================
    # 1) INTRODUÇÃO — DEFINIÇÃO DO PROBLEMA FÍSICO
    # =========================================================================
    st.markdown("## 1. Introdução — Caracterização objetiva do problema físico")
    st.caption(
        "Critério: demonstrar, com base em observações objetivas, que existe um problema físico real e mensurável. "
        "Não incluir soluções, hipóteses ou cálculos nesta etapa."
    )

    intro_contextualizacao = st.text_area(
        "1.1 Contextualização objetiva do ambiente (descrever apenas fatos observáveis)",
        value=_get(state, "intro_contextualizacao", pref.get("texto_problema", "") or ""),
        height=150,
        key=f"{STAGE_ID}_intro_contextualizacao",
    )
    _set(state, "intro_contextualizacao", intro_contextualizacao)

    intro_desconforto = st.text_area(
        "1.2 Evidências observáveis do desconforto térmico (o que foi visto ou relatado)",
        value=_get(state, "intro_desconforto", ""),
        height=150,
        key=f"{STAGE_ID}_intro_desconforto",
    )
    _set(state, "intro_desconforto", intro_desconforto)

    intro_just = st.text_area(
        "1.3 Interpretação física preliminar (mecanismos de troca de energia envolvidos)",
        value=_get(state, "intro_justificativa_fisica", ""),
        height=150,
        key=f"{STAGE_ID}_intro_justificativa_fisica",
    )
    _set(state, "intro_justificativa_fisica", intro_just)

    pergunta_auto = (pref.get("pergunta_norteadora", "") or "").strip()
    intro_pergunta = st.text_area(
        "1.4 Pergunta norteadora (explícita)",
        value=_get(state, "intro_pergunta_norteadora", pergunta_auto),
        height=90,
        key=f"{STAGE_ID}_intro_pergunta_norteadora",
    )
    _set(state, "intro_pergunta_norteadora", intro_pergunta)

    _render_save_button(path_json, state, "s1")
    st.markdown("---")

    # =========================================================================
    # 2) FUNDAMENTAÇÃO FÍSICA
    # =========================================================================
    st.markdown("## 2. Fundamentação Física")

    st.markdown("**2.1 Conceitos mobilizados (checklist)**")
    sel_atual = set(_as_list_str(_get(state, "fund_conceitos_sel", [])))

    fund_sel: List[str] = []
    for opt in list(CFG.conceitos_opcoes):
        marcado = st.checkbox(
            opt,
            value=(opt in sel_atual),
            key=f"{STAGE_ID}_fund_chk_{re.sub(r'[^a-zA-Z0-9_]+','_', str(opt)).strip('_')}",
        )
        if marcado:
            fund_sel.append(opt)
    _set(state, "fund_conceitos_sel", fund_sel)

    fund_modelo = st.text_area(
        "2.2 Modelo físico do sistema (o que troca energia com o quê?)",
        value=_get(state, "fund_modelo_mental", ""),
        height=130,
        key=f"{STAGE_ID}_fund_modelo_mental",
    )
    _set(state, "fund_modelo_mental", fund_modelo)

    fund_mecanismos = st.text_area(
        "2.3 Mecanismos de transferência (condução, convecção, radiação) e papel do ar",
        value=_get(state, "fund_mecanismos", pref.get("inv_proc", {}).get("v_ar_fluido", "") or ""),
        height=140,
        key=f"{STAGE_ID}_fund_mecanismos",
    )
    _set(state, "fund_mecanismos", fund_mecanismos)

    fund_primeira_lei = st.text_area(
        "2.4 Primeira Lei da Termodinâmica (enunciado + leitura qualitativa do balanço de energia)",
        value=_get(state, "fund_primeira_lei", pref.get("inv_proc", {}).get("v_primeira_lei", "") or ""),
        height=120,
        key=f"{STAGE_ID}_fund_primeira_lei",
    )
    _set(state, "fund_primeira_lei", fund_primeira_lei)

    _render_save_button(path_json, state, "s2")
    st.markdown("---")

    # =========================================================================
    # 3) METODOLOGIA
    # =========================================================================
    st.markdown("## 3. Metodologia")
    st.info("Esta seção pode ser pré-preenchida pela INVESTIGAÇÃO. Ajuste apenas para ficar claro e verificável.")

    prob_esc = pref.get("prob_esc", {}) if isinstance(pref.get("prob_esc"), dict) else {}
    inv_proc = pref.get("inv_proc", {}) if isinstance(pref.get("inv_proc"), dict) else {}
    inv_ativ = pref.get("inv_ativ", {}) if isinstance(pref.get("inv_ativ"), dict) else {}

    amb_especifico = (prob_esc.get("ambiente_especifico") or "").strip()
    turno = (prob_esc.get("turno") or "").strip()
    condicoes = (prob_esc.get("condicoes") or "").strip()

    pref_sistema_parts = []
    if _nonempty(amb_especifico):
        pref_sistema_parts.append(f"Ambiente: {amb_especifico}.")
    if _nonempty(turno):
        pref_sistema_parts.append(f"Turno de observação/medição: {turno}.")
    pref_sistema_parts.append(
        "Fronteiras relevantes consideradas: aberturas (portas/janelas), superfícies (paredes/piso/teto) e ocupação humana."
    )
    pref_met_sistema = " ".join([p for p in pref_sistema_parts if _nonempty(p)])

    grandezas_chk = inv_proc.get("grandezas", [])
    grandezas_txt = " ".join([str(g).strip() for g in grandezas_chk if str(g).strip()])

    fields = inv_ativ.get("medicoes_csv_fields", []) or []
    fields_set = {str(x).strip() for x in fields if str(x).strip()}

    tem_ta = ("Ta_C" in fields_set) or ("Ta" in grandezas_txt)
    tem_ts = ("Ts_C" in fields_set) or ("Ts" in grandezas_txt)
    tem_ur = ("UR_pct" in fields_set) or ("UR" in grandezas_txt)
    tem_v = ("v_ms" in fields_set) or ("v" in grandezas_txt) or ("ar" in grandezas_txt.lower())

    linhas_grandezas = []
    if tem_ta:
        linhas_grandezas.append("- Ta (Temperatura do ar): define o estado térmico do fluido e o gradiente que dirige trocas por convecção.")
    if tem_ts:
        linhas_grandezas.append("- Ts (Temperatura de superfícies): evidencia fontes/sumidouros e efeitos radiativos/condução com o entorno.")
    if tem_ur:
        linhas_grandezas.append("- UR (Umidade relativa): modula dissipação térmica do corpo (sensação térmica) e condições do ar.")
    if tem_v:
        linhas_grandezas.append("- v_ar (Velocidade do ar): controla taxa de convecção e renovação/mistura do ar no ambiente.")
    pref_met_grandezas = "\n".join(linhas_grandezas).strip()

    linhas_instr = []
    if tem_ta:
        linhas_instr.append("- Medição de Ta: termômetro (ou sensor digital) posicionado ao nível representativo do ar ambiente; aguardar estabilização.")
    if tem_ts:
        linhas_instr.append("- Medição de Ts: termômetro infravermelho/contato (conforme disponível); registrar a superfície e evitar sombreamento do sensor.")
    if tem_ur:
        linhas_instr.append("- Medição de UR: higrômetro/sensor de umidade; considerar resposta lenta e influência de correntes de ar.")
    if tem_v:
        linhas_instr.append("- Medição de v_ar: anemômetro; observar sensibilidade a turbulência local e posicionamento.")
    linhas_instr.append("- Limitações: resolução/precisão dependem do instrumento; leituras pontuais sofrem influência de proximidade de pessoas, sol direto e aberturas.")
    pref_met_instr = "\n".join(linhas_instr).strip()

    pontos_fixos = inv_ativ.get("pontos_fixos_7", []) or []
    rodadas = inv_ativ.get("rodadas_medicoes", []) or []
    n_pontos = inv_ativ.get("dados_futuros", {}).get("n_pontos", None)
    n_rodadas = inv_ativ.get("dados_futuros", {}).get("n_rodadas", None)
    desc_proc = (inv_ativ.get("dados_futuros", {}) or {}).get("descricao", "")

    horarios = []
    for r in rodadas:
        if isinstance(r, dict):
            h = str(r.get("horario", "")).strip()
            if h:
                horarios.append(h)
    horarios = sorted(set(horarios), key=lambda x: (len(x), x))

    pref_proc_lines = []
    if _nonempty(desc_proc):
        pref_proc_lines.append(f"{desc_proc}")
    else:
        if n_rodadas and n_pontos:
            pref_proc_lines.append(f"Foram realizadas {n_rodadas} rodadas de medição em {n_pontos} pontos fixos.")
        elif n_rodadas:
            pref_proc_lines.append(f"Foram realizadas {n_rodadas} rodadas de medição.")
        elif n_pontos:
            pref_proc_lines.append(f"Foram utilizados {n_pontos} pontos fixos de medição.")

    if horarios:
        pref_proc_lines.append(f"Horários/rodadas: {', '.join(horarios)}.")
    if isinstance(pontos_fixos, list) and pontos_fixos:
        pref_proc_lines.append("Pontos fixos: " + "; ".join([str(p).strip() for p in pontos_fixos if str(p).strip()]) + ".")

    pref_proc_lines.append(
        "Em cada ponto/horário, registraram-se as grandezas previstas e observações (obs) do estado do ambiente. "
        "Os dados foram consolidados em tabela (formato rodadas_json e/ou CSV) para comparação entre regiões e horários."
    )
    pref_met_proced = "\n".join([l for l in pref_proc_lines if _nonempty(l)]).strip()

    cond_lines = []
    if _nonempty(condicoes):
        cond_lines.append(condicoes)
    cond_lines.append("Registrar, quando aplicável: ocupação (nº de pessoas), estado de janelas/portas, ventilação/AC, insolação incidente e eventos pontuais.")
    pref_met_cond = "\n".join([l for l in cond_lines if _nonempty(l)]).strip()

    met_sistema = st.text_area("3.1 Definição do sistema físico estudado", value=_get(state, "met_sistema_fisico", pref_met_sistema), height=110, key=f"{STAGE_ID}_met_sistema_fisico")
    _set(state, "met_sistema_fisico", met_sistema)

    met_grandezas = st.text_area("3.2 Grandezas medidas e justificativa física de cada uma", value=_get(state, "met_grandezas", pref_met_grandezas), height=150, key=f"{STAGE_ID}_met_grandezas")
    _set(state, "met_grandezas", met_grandezas)

    met_instrumentos = st.text_area("3.3 Instrumentos utilizados e limitações conhecidas", value=_get(state, "met_instrumentos", pref_met_instr), height=150, key=f"{STAGE_ID}_met_instrumentos")
    _set(state, "met_instrumentos", met_instrumentos)

    met_proced = st.text_area("3.4 Procedimentos de medição (onde, quando, quantas vezes)", value=_get(state, "met_procedimentos", pref_met_proced), height=160, key=f"{STAGE_ID}_met_procedimentos")
    _set(state, "met_procedimentos", met_proced)

    met_cond = st.text_area("3.5 Condições ambientais registradas (pessoas/janelas/ventilação/insolação)", value=_get(state, "met_condicoes", pref_met_cond), height=160, key=f"{STAGE_ID}_met_condicoes")
    _set(state, "met_condicoes", met_cond)

    _render_save_button(path_json, state, "s3")
    st.markdown("---")

    # =========================================================================
    # 4) RESULTADOS E ANÁLISE FÍSICA
    # =========================================================================
    st.markdown("## 4) Resultados e Análise Física")

    inv_all = _load_investigacao(ctx)
    inv_stages = _pick_stages(inv_all)

    inv_org = inv_stages.get("investigacao_organizacao_dados", {}) if isinstance(inv_stages, dict) else {}
    inv_af = inv_stages.get("investigacao_analise_fisica_dados", {}) if isinstance(inv_stages, dict) else {}

    data_records = inv_org.get("data_records", [])
    if not isinstance(data_records, list):
        data_records = []

    stats_resumo = inv_org.get("stats_resumo", [])
    comp_por_ponto = inv_org.get("comparacao_por_ponto", [])

    if (not isinstance(stats_resumo, list) or len(stats_resumo) == 0) and isinstance(inv_af, dict):
        ev = inv_af.get("dados_organizados_evidence", {})
        if isinstance(ev, dict) and isinstance(ev.get("stats_resumo"), list):
            stats_resumo = ev.get("stats_resumo", [])
    if (not isinstance(comp_por_ponto, list) or len(comp_por_ponto) == 0) and isinstance(inv_af, dict):
        ev = inv_af.get("dados_organizados_evidence", {})
        if isinstance(ev, dict) and isinstance(ev.get("comparacao_por_ponto"), list):
            comp_por_ponto = ev.get("comparacao_por_ponto", [])

    if not isinstance(stats_resumo, list):
        stats_resumo = []
    if not isinstance(comp_por_ponto, list):
        comp_por_ponto = []

    st.markdown("### 4.1 Resultados e organização dos dados (DADO)")
    inv_path_guess = _investigacao_path(ctx)

    state.setdefault("__sec4__", {})
    state["__sec4__"]["inv_path"] = inv_path_guess.as_posix()
    state["__sec4__"]["stats_resumo"] = stats_resumo
    state["__sec4__"]["comp_por_ponto"] = comp_por_ponto
    state["__sec4__"].setdefault("grad_png", b"")
    state["__sec4__"].setdefault("grad_caption", "")
    state["__sec4__"].setdefault("grad_var_label", "")
    state["__sec4__"].setdefault("grad_png_path", "")
    state["__sec4__"].setdefault("grad_png_err", "")

    if len(data_records) == 0:
        st.warning(
            "Não encontrei dados organizados para este aluno em "
            f"`{inv_path_guess.as_posix()}`.\n\n"
            "Volte na INVESTIGAÇÃO e gere/organize os dados (data_records / stats_resumo / comparacao_por_ponto)."
        )
    else:
        tab1, tab2, tab3 = st.tabs(["Tabela bruta", "Resumo estatístico", "Comparação por ponto"])
        with tab1:
            _df_show_2dec(data_records)
        with tab2:
            if len(stats_resumo) > 0:
                _df_show_2dec(stats_resumo)
            else:
                st.info("Resumo estatístico (stats_resumo) não encontrado.")
        with tab3:
            if len(comp_por_ponto) > 0:
                _df_show_2dec(comp_por_ponto)
            else:
                st.info("Comparação por ponto (comparacao_por_ponto) não encontrada.")

        chart = None
        caption_txt = ""
        chosen_label = ""
        if len(comp_por_ponto) > 0:
            st.markdown("### Mapa espacial (gradiente) — apoio visual para a análise")
            chart, caption_txt, chosen_label = _build_gradiente_chart(comp_por_ponto)
            if chart is None:
                st.info(caption_txt)
            else:
                st.write(caption_txt)
                st.altair_chart(chart, use_container_width=True)

                cols_btn = st.columns([1, 2])
                with cols_btn[0]:
                    if st.button("Gerar figura padronizada (PNG)", key=f"{STAGE_ID}_sec4_build_png"):
                        with st.spinner("Garantindo PNG (vl-convert + pad 1:1) ..."):
                            ok, err = _ensure_heatmap_png(ctx, state, chart, chosen_label)
                        if ok:
                            fig_path = Path(state["__sec4__"].get("grad_png_path", "") or "")
                            if fig_path.exists():
                                st.success(f"Figura pronta: {fig_path.as_posix()} (não sobrescreve se já existir).")
                            else:
                                st.success("Figura pronta (bytes em memória).")
                        else:
                            state["__sec4__"]["grad_png_err"] = err or "Erro desconhecido."
                            st.warning("Não consegui gerar/garantir o PNG.")
                            st.code(state["__sec4__"]["grad_png_err"])

                with cols_btn[1]:
                    figp = state["__sec4__"].get("grad_png_path", "")
                    if state["__sec4__"].get("grad_png", b""):
                        st.caption("Status: PNG pronto para o PDF ✅")
                        if figp:
                            st.caption(f"Arquivo: {figp}")
                    else:
                        st.caption("Status: PNG ainda não gerado (PDF sairá sem a figura).")

    def _auto_resumo(stats: List[Dict[str, Any]]) -> str:
        if not isinstance(stats, list) or len(stats) == 0:
            return ""
        frases = []
        for r in stats:
            if not isinstance(r, dict):
                continue
            var = str(r.get("Variável", "")).strip()
            med = r.get("Média", None)
            vmin_ = r.get("Mín", None)
            vmax_ = r.get("Máx", None)
            if var and (med is not None) and (vmin_ is not None) and (vmax_ is not None):
                try:
                    frases.append(f"{var}: média {float(med):.2f} (mín {float(vmin_):.2f}; máx {float(vmax_):.2f}).")
                except Exception:
                    pass
            if len(frases) >= 4:
                break
        return " ".join(frases).strip()

    resumo_auto = _auto_resumo(stats_resumo)

    resumo_dados = st.text_area(
        "4.1.1 Síntese objetiva dos dados (médias, variações, tendências, sem explicar por quê)",
        value=_get(state, "resumo_dados", "") if _nonempty(_get(state, "resumo_dados", "")) else resumo_auto,
        height=140,
        key=f"{STAGE_ID}_resumo_dados",
    )
    _set(state, "resumo_dados", resumo_dados)

    st.markdown("### 4.2 Análise física (INTERPRETAÇÃO)")
    a_grad = ""
    a_equil = ""
    a_sel_mec = ""
    a_just_mec = ""
    a_conf = ""

    if isinstance(inv_af, dict):
        a_grad = (inv_af.get("a_gradientes") or "").strip()
        a_equil = (inv_af.get("d_equilibrio") or inv_af.get("v_equilibrio") or "").strip()
        a_sel_mec = (inv_af.get("sel_mecanismo") or "").strip()
        a_just_mec = (inv_af.get("d_just_mecanismos") or "").strip()
        a_conf = (inv_af.get("a_mov_ar_temp") or inv_af.get("a_comp_regioes") or "").strip()

    analise_grad = st.text_area(
        "4.2 Gradientes térmicos e padrões espaciais/temporais (onde muda e por quê?)",
        value=_get(state, "analise_gradientes", "") if _nonempty(_get(state, "analise_gradientes", "")) else a_grad,
        height=120,
        key=f"{STAGE_ID}_analise_gradientes",
    )
    _set(state, "analise_gradientes", analise_grad)

    analise_eq = st.text_area(
        "4.3 Equilíbrio térmico (ou não) do sistema: evidências e interpretação",
        value=_get(state, "analise_equilibrio", "") if _nonempty(_get(state, "analise_equilibrio", "")) else a_equil,
        height=120,
        key=f"{STAGE_ID}_analise_equilibrio",
    )
    _set(state, "analise_equilibrio", analise_eq)

    current_mec = _get(state, "analise_mecanismo_dom", "")
    if (not _nonempty(current_mec)) and _nonempty(a_sel_mec) and (a_sel_mec in CFG.mecanismo_opcoes):
        current_mec = a_sel_mec

    mecanismo_dom = st.selectbox(
        "4.4 Mecanismo(s) dominante(s) de transferência (seleção)",
        options=list(CFG.mecanismo_opcoes),
        index=list(CFG.mecanismo_opcoes).index(current_mec) if current_mec in CFG.mecanismo_opcoes else 0,
        key=f"{STAGE_ID}_analise_mecanismo_dom",
    )
    _set(state, "analise_mecanismo_dom", mecanismo_dom)

    mecanismo_just = st.text_area(
        "4.4.1 Justificativa com evidência (use dados/condições como suporte)",
        value=_get(state, "analise_mecanismo_just", "") if _nonempty(_get(state, "analise_mecanismo_just", "")) else a_just_mec,
        height=120,
        key=f"{STAGE_ID}_analise_mecanismo_just",
    )
    _set(state, "analise_mecanismo_just", mecanismo_just)

    analise_conforto = st.text_area(
        "4.5 Relação entre movimento do ar / superfícies / ar e o conforto térmico percebido",
        value=_get(state, "analise_conforto", "") if _nonempty(_get(state, "analise_conforto", "")) else a_conf,
        height=140,
        key=f"{STAGE_ID}_analise_conforto",
    )
    _set(state, "analise_conforto", analise_conforto)

    _render_save_button(path_json, state, "s4")
    st.markdown("---")

    # =========================================================================
    # 5) CONCLUSÕES
    # =========================================================================
    st.markdown("## 5) Conclusões")

    pergunta_ref = (_get(state, "intro_pergunta_norteadora", "") or "").strip()
    if _nonempty(pergunta_ref):
        st.markdown("**Pergunta norteadora (referência):**")
        st.write(pergunta_ref)

    conc_resposta = st.text_area("5.1 Resposta direta à pergunta norteadora (obrigatório)", value=_get(state, "conc_resposta", ""), height=120, key=f"{STAGE_ID}_conc_resposta")
    _set(state, "conc_resposta", conc_resposta)

    conc_sintese = st.text_area("5.2 Síntese do entendimento físico estabilizado (2–4 afirmações sustentadas por evidência)", value=_get(state, "conc_sintese", ""), height=120, key=f"{STAGE_ID}_conc_sintese")
    _set(state, "conc_sintese", conc_sintese)

    implic_sel = st.multiselect(
        "5.3 Implicações práticas do entendimento obtido (sem projeto de engenharia)",
        options=list(CFG.implicacoes_opcoes),
        default=_as_list_str(_get(state, "conc_implic_sel", [])),
        key=f"{STAGE_ID}_conc_implic_sel",
    )
    _set(state, "conc_implic_sel", implic_sel)

    if "Outra implicação (descrever abaixo)" in implic_sel:
        implic_outra = st.text_input(
            "5.3.1 Descreva a implicação 'Outra' (obrigatório se marcou)",
            value=_get(state, "conc_implic_outra", ""),
            key=f"{STAGE_ID}_conc_implic_outra",
        )
        _set(state, "conc_implic_outra", implic_outra)
    else:
        _set(state, "conc_implic_outra", "")

    _render_save_button(path_json, state, "s5")
    st.markdown("---")

    # =========================================================================
    # 6) LIMITAÇÕES E PERSPECTIVAS
    # =========================================================================
    st.markdown("## 6) Limitações e Perspectivas")

    lim_texto_auto = "\n".join(
        [
            f"- Simplificações adotadas: {pref.get('lim_simplificacoes','')}".strip(),
            f"- Incertezas experimentais: {pref.get('lim_incertezas','')}".strip(),
            f"- Variáveis não controladas: {pref.get('lim_variaveis_nao_controladas','')}".strip(),
        ]
    ).strip()

    lim_texto = st.text_area("6.1 Limitações (obrigatório)", value=_get(state, "lim_texto", lim_texto_auto), height=140, key=f"{STAGE_ID}_lim_texto")
    _set(state, "lim_texto", lim_texto)

    lim_inc = st.text_area("6.1.1 Incertezas experimentais (opcional)", value=_get(state, "lim_incertezas", pref.get("lim_incertezas", "") or ""), height=90, key=f"{STAGE_ID}_lim_incertezas")
    _set(state, "lim_incertezas", lim_inc)

    lim_var = st.text_area("6.1.2 Variáveis não controladas (opcional)", value=_get(state, "lim_variaveis_nao_controladas", pref.get("lim_variaveis_nao_controladas", "") or ""), height=90, key=f"{STAGE_ID}_lim_variaveis_nao_controladas")
    _set(state, "lim_variaveis_nao_controladas", lim_var)

    melhorias = st.text_area("6.2 Melhorias possíveis (obrigatório)", value=_get(state, "lim_melhorias", ""), height=110, key=f"{STAGE_ID}_lim_melhorias")
    _set(state, "lim_melhorias", melhorias)

    futuros = st.text_area("6.3 Aprofundamentos futuros (obrigatório)", value=_get(state, "lim_futuros", ""), height=110, key=f"{STAGE_ID}_lim_futuros")
    _set(state, "lim_futuros", futuros)

    _render_save_button(path_json, state, "s6")
    st.markdown("---")

    # =========================================================================
    # 7) REFERÊNCIAS
    # =========================================================================
    st.markdown("## 7) Referências (se utilizadas)")
    refs_texto = st.text_area("7.1 Referências (uma por linha)", value=_get(state, "refs_texto", ""), height=120, key=f"{STAGE_ID}_refs_texto")
    _set(state, "refs_texto", refs_texto)

    _render_save_button(path_json, state, "s7")
    st.markdown("---")

    # =========================================================================
    # Diagnóstico
    # =========================================================================
    st.markdown("## Diagnóstico")
    faltas = _compute_faltas(state)
    concluido = len(faltas) == 0
    _set(state, "concluido", bool(concluido))

    if concluido:
        st.success("Memorial pronto: estrutura completa e com campos mínimos preenchidos.")
    else:
        st.warning("Memorial ainda incompleto. Itens faltantes:")
        st.markdown("\n".join(faltas))

    st.markdown("---")

    # =========================================================================
    # Exportação (PDF opcional)
    # =========================================================================
    st.markdown("## Exportação")

    titulo_pdf = (_get(state, "capa_titulo", "") or CFG.titulo_base).strip()

    sec4 = state.get("__sec4__", {}) if isinstance(state.get("__sec4__"), dict) else {}
    inv_path_txt = str(sec4.get("inv_path", "")).strip()
    stats_resumo_pdf = sec4.get("stats_resumo", []) if isinstance(sec4.get("stats_resumo"), list) else []
    grad_png = sec4.get("grad_png", b"") if isinstance(sec4.get("grad_png"), (bytes, bytearray)) else b""
    grad_caption = str(sec4.get("grad_caption", "Figura 4.1 — Gradiente espacial.")).strip()

    mini_tables = []
    if CFG.pdf_incluir_mini_tabela_stats and isinstance(stats_resumo_pdf, list) and len(stats_resumo_pdf) > 0:
        mini_stats = stats_resumo_pdf[: max(1, int(CFG.pdf_mini_tabela_stats_max_linhas))]
        mini_tables.append(
            {
                "title": "Tabela 4.1 — Resumo estatístico (extrato)",
                "data": _records_to_table(mini_stats, max_rows=len(mini_stats)),
            }
        )

    nota_referencia = (
        "Nota de evidência: os dados completos (tabela bruta, comparação por ponto e registros) "
        f"foram entregues no Entregável Parcial / arquivo de investigação do aluno (origem: {inv_path_txt})."
        if _nonempty(inv_path_txt)
        else "Nota de evidência: os dados completos foram entregues no Entregável Parcial / arquivo de investigação do aluno."
    )

    pergunta_ref = (_get(state, "intro_pergunta_norteadora", "") or "").strip()

    sections = [
        {
            "h": "0) Capa e Identificação Técnica",
            "body": "\n\n".join(
                [
                    f"Título: {_get(state, 'capa_titulo', '')}".strip(),
                    f"Ambiente: {_get(state, 'capa_ambiente', '')}".strip(),
                    f"Disciplina: {_get(state, 'capa_disciplina', '')}".strip(),
                    f"Instituição: {_get(state, 'capa_instituicao', '')}".strip(),
                    f"Período: {_get(state, 'capa_periodo', '')}".strip(),
                    f"Integrantes:\n{_get(state, 'capa_integrantes', '')}".strip(),
                    f"Professor: {_get(state, 'capa_professor', '')}".strip(),
                    f"Data: {_get(state, 'capa_data', '')}".strip(),
                ]
            ).strip(),
        },
        {
            "h": "1) Introdução — Definição do Problema Físico",
            "body": "\n\n".join(
                [
                    _get(state, "intro_contextualizacao", ""),
                    _get(state, "intro_desconforto", ""),
                    _get(state, "intro_justificativa_fisica", ""),
                    ("Pergunta norteadora:\n" + _get(state, "intro_pergunta_norteadora", "")).strip(),
                ]
            ).strip(),
        },
        {
            "h": "2) Fundamentação Física",
            "body": "\n\n".join(
                [
                    "Conceitos mobilizados: " + ", ".join(_as_list_str(_get(state, "fund_conceitos_sel", []))),
                    _get(state, "fund_modelo_mental", ""),
                    _get(state, "fund_mecanismos", ""),
                    _get(state, "fund_primeira_lei", ""),
                ]
            ).strip(),
        },
        {
            "h": "3) Metodologia",
            "body": "\n\n".join(
                [
                    "Sistema físico:\n" + _get(state, "met_sistema_fisico", ""),
                    "Grandezas e justificativas:\n" + _get(state, "met_grandezas", ""),
                    "Instrumentos/limitações:\n" + _get(state, "met_instrumentos", ""),
                    "Procedimentos:\n" + _get(state, "met_procedimentos", ""),
                    "Condições do ambiente:\n" + _get(state, "met_condicoes", ""),
                ]
            ).strip(),
        },
        {
            "h": "4) Resultados e Análise Física",
            "body": "\n\n".join(
                [
                    "RESULTADOS (dado):\n" + _get(state, "resumo_dados", ""),
                    "ANÁLISE (interpretação):\n"
                    + "\n\n".join(
                        [
                            _get(state, "analise_gradientes", ""),
                            _get(state, "analise_equilibrio", ""),
                            f"Mecanismo dominante: {_get(state, 'analise_mecanismo_dom', '')}",
                            _get(state, "analise_mecanismo_just", ""),
                            _get(state, "analise_conforto", ""),
                        ]
                    ).strip(),
                    nota_referencia,
                ]
            ).strip(),
            "tables": mini_tables,
            "image_bytes": grad_png,
            "image_caption": grad_caption if grad_png else "",
            "image_w_frac": float(CFG.pdf_fig_width_frac),
        },
        {
            "h": "5) Conclusões",
            "body": "\n\n".join(
                [
                    ("Pergunta norteadora:\n" + pergunta_ref).strip() if _nonempty(pergunta_ref) else "",
                    "Resposta:\n" + _get(state, "conc_resposta", ""),
                    "Síntese:\n" + _get(state, "conc_sintese", ""),
                    (
                        "Implicações:\n- " + "\n- ".join(_as_list_str(_get(state, "conc_implic_sel", [])))
                        if _as_list_str(_get(state, "conc_implic_sel", []))
                        else ""
                    ),
                    (_get(state, "conc_implic_outra", "") if _nonempty(_get(state, "conc_implic_outra", "")) else ""),
                ]
            ).strip(),
        },
        {
            "h": "6) Limitações e Perspectivas",
            "body": "\n\n".join(
                [
                    "Limitações:\n" + _get(state, "lim_texto", ""),
                    ("Incertezas:\n" + _get(state, "lim_incertezas", "")).strip(),
                    ("Variáveis não controladas:\n" + _get(state, "lim_variaveis_nao_controladas", "")).strip(),
                    "Melhorias:\n" + _get(state, "lim_melhorias", ""),
                    "Aprofundamentos futuros:\n" + _get(state, "lim_futuros", ""),
                ]
            ).strip(),
        },
        {
            "h": "7) Referências",
            "body": _get(state, "refs_texto", "").strip(),
        },
    ]

    if REPORTLAB_OK and not grad_png:
        st.info("Para incluir a figura no PDF: vá na Seção 4 e clique em “Gerar figura padronizada (PNG)”.")
    if REPORTLAB_OK:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Gerar PDF", key=f"{STAGE_ID}_gerar_pdf"):
                pdf_bytes = _build_pdf_bytes(titulo_pdf, sections)
                pdf_path = _pdf_path(ctx)
                pdf_path.write_bytes(pdf_bytes)
                st.session_state[f"{STAGE_ID}_pdf_bytes"] = pdf_bytes
                st.success("PDF gerado e salvo.")
        with col2:
            pdf_bytes_cached = st.session_state.get(f"{STAGE_ID}_pdf_bytes")
            if pdf_bytes_cached:
                st.download_button(
                    "Baixar PDF",
                    data=pdf_bytes_cached,
                    file_name=f"memorial_tecnico_{_sanitize_filename(_get_aluno_name(ctx))}.pdf",
                    mime="application/pdf",
                    key=f"{STAGE_ID}_download_pdf",
                )
            else:
                st.caption("Gere o PDF para liberar o download.")
    else:
        st.warning("PDF indisponível (reportlab não instalado).")
        st.code(f"Erro de importação: {REPORTLAB_ERR}")
