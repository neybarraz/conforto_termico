# blocks/problema/contextualizacao_entregavel_parcial.py
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from io import BytesIO
from pathlib import Path
from reportlab.platypus import KeepInFrame
from typing import Any, Dict, List, Tuple

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from storage.io_csv import load_json, save_json
from storage.paths import stage_path

# =========================================================
# ETAPA: Entregável parcial
# (Contextualização + Escopo + Pergunta Central + Diagnóstico Inicial + Conteúdos Essenciais)
# =========================================================
STAGE_ID = "problema_entregavel_parcial_contextualizacao"
OUT_DIR = Path("data/pdf")

# ---------------------------------------------------------
# Constantes de stages / títulos
# ---------------------------------------------------------
TARGET_STAGE_ID = "problema_definicao"
TARGET_STAGE_TITLE = "Contextualização"

ESCOPO_STAGE_ID = "problema_escopo_ambiente"
ESCOPO_TITLE = "Escopo do Problema"

PERGUNTA_STAGE_ID = "problema_pergunta_norteadora"
PERGUNTA_TITLE = "Pergunta Central"

DIAG_STAGE_ID = "problema_diagnostico_inicial"
DIAG_TITLE = "Diagnóstico Inicial"

CONTEUDOS_STAGE_ID = "problema_conteudos_essenciais"
CONTEUDOS_TITLE = "Conteúdos Essenciais"

# ---------------------------------------------------------
# Labels globais (fallback)
# ---------------------------------------------------------
_GLOBAL_LABELS: Dict[str, str] = {
    "aluno": "Aluno (a)",
    "grupo_id": "Grupo (ID)",
    "grupo_nome": "Nome do Grupo",
    "ambiente": "Ambiente",
    "texto": "Quais sinais de desconforto térmico você já observou nesse ambiente?",
    "saved_at": "Salvo em",
    "generated_at": "Gerado em",
    "updated_at": "Atualizado em",
    "stage_id": "Etapa",
    # Escopo
    "ambiente_especifico": "Ambiente específico",
    "turno": "Turno",
    "condicoes": "Condições",
    # Pergunta central
    "pergunta_aluno": "Como você reformularia a pergunta acima com suas próprias palavras?",
    # Diagnóstico
    "resultado.percentual": "Porcentagem de acertos",
    "reflexao": "Ponto de partida conceitual",
    "likert": "Autoavaliação (Likert)",
    "concluido": "Concluído",
    # Likert (nomes exigidos no PDF)
    "likert.l1_temp_calor": "Temperatura x Calor",
    "likert.l2_equilibrio": "Equilíbrio térmico",
    "likert.l3_conducao": "Condução",
    "likert.l4_conveccao": "Convecção",
    "likert.l5_radiacao": "Radiação",
    "likert.l6_ar_fluido": "Ar como fluido térmico",
    # Conteúdos Essenciais (todos entendimentos)
    "entendimentos.temp_escalas": "O que você entendeu deste tema: Temperatura e Escalas Térmicas?",
    "entendimentos.teoria_cinetica": "O que você entendeu deste tema: Teoria Cinética dos Gases?",
    "entendimentos.calor_transferencia": "O que você entendeu deste tema: Calor e Formas de Transferência?",
    "entendimentos.conducao": "O que você entendeu deste tema: Condução — calor por contato direto?",
    "entendimentos.conveccao": "O que você entendeu deste tema: Convecção — calor transportado pelo movimento do ar?",
    "entendimentos.radiacao": "O que você entendeu deste tema: Radiação térmica — calor na forma de ondas?",
    "entendimentos.integracao": "O que você entendeu deste tema: Integração dos mecanismos?",
    "entendimentos.primeira_lei": "O que você entendeu deste tema: Primeira Lei da Termodinâmica?",
    "entendimentos.equilibrio_termico": "O que você entendeu deste tema: Equilíbrio Térmico?",
    "conteudos": "Conteúdos",
    "checklist": "Checklist",
    "sintese": "Síntese",
    "lacunas": "Lacunas",
}

# ---------------------------------------------------------
# Configuração por stage
# ---------------------------------------------------------
STAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    TARGET_STAGE_ID: {
        "preferred_keys": ["ambiente", "texto"],
        "hidden_keys": {
            "saved_at",
            "generated_at",
            "updated_at",
            "aluno",
            "grupo_id",
            "grupo_nome",
            "stage_id",
        },
        "allowed_keys": {"ambiente", "texto"},
        "labels": {},
    },
    ESCOPO_STAGE_ID: {
        "preferred_keys": ["saved_at", "ambiente_especifico", "turno", "condicoes"],
        "hidden_keys": {
            "generated_at",
            "updated_at",
            "aluno",
            "grupo_id",
            "grupo_nome",
            "stage_id",
        },
        "allowed_keys": {"saved_at", "ambiente_especifico", "turno", "condicoes"},
        "labels": {},
    },
    PERGUNTA_STAGE_ID: {
        "preferred_keys": ["saved_at", "pergunta_aluno"],
        "hidden_keys": {
            "generated_at",
            "updated_at",
            "aluno",
            "grupo_id",
            "grupo_nome",
            "stage_id",
            "pergunta_norteadora",
            "confirmado",
        },
        "allowed_keys": {"saved_at", "pergunta_aluno"},
        "labels": {
            "pergunta_aluno": "Como você reformularia a pergunta acima com suas próprias palavras?",
        },
    },
    DIAG_STAGE_ID: {
        "preferred_keys": ["saved_at", "likert", "resultado", "reflexao", "concluido"],
        "hidden_keys": {
            "generated_at",
            "updated_at",
            "aluno",
            "grupo_id",
            "grupo_nome",
            "stage_id",
            "objetivas",
            "resultado.respondidas",
            "resultado.acertos",
        },
        "allowed_keys": {"saved_at", "likert", "resultado", "reflexao", "concluido"},
        "labels": {},
    },
    CONTEUDOS_STAGE_ID: {
        "preferred_keys": ["entendimentos", "saved_at", "conteudos", "checklist", "sintese", "lacunas"],
        "hidden_keys": {
            "generated_at",
            "updated_at",
            "aluno",
            "grupo_id",
            "grupo_nome",
            "stage_id",
            "concluido",
        },
        "allowed_keys": {"entendimentos", "saved_at", "conteudos", "checklist", "sintese", "lacunas"},
        "labels": {},
    },
}

# =========================================================
# utilidades gerais
# =========================================================
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_filename(name: str) -> str:
    name = (name or "").strip() or "Aluno"
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "Aluno"


def _nl_to_br(s: str) -> str:
    return (s or "").replace("\n", "<br/>").strip()


def _escape_xml(s: Any) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _key_prefix(ctx: Dict) -> str:
    aluno = (ctx.get("aluno") or "Aluno").strip()
    grupo_id = (ctx.get("grupo_id") or "").strip()
    safe = _safe_filename(aluno)
    return f"{STAGE_ID}__{safe}__{grupo_id or 'G'}"


def _ctx_get_state(ctx: Dict) -> Dict[str, Any]:
    if isinstance(ctx, dict) and isinstance(ctx.get("state"), dict):
        return ctx["state"]
    key = "__pbl_state__problema_entregavel_parcial_contextualizacao"
    if key not in st.session_state:
        st.session_state[key] = {}
    return st.session_state[key]


def _get(state: Dict[str, Any], k: str, default: Any) -> Any:
    return state.get(k, default)


def _set(state: Dict[str, Any], k: str, v: Any) -> None:
    state[k] = v


def _problema_path(aluno: str) -> Path:
    base = Path("data") / "problema"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"problema_{_safe_filename(aluno)}.json"


def _stage_conf(stage_id: str) -> Dict[str, Any]:
    return STAGE_CONFIG.get(stage_id, {})


def _field_label(stage_id: str, key: str) -> str:
    conf = _stage_conf(stage_id)
    labels = conf.get("labels") or {}
    return labels.get(key) or _GLOBAL_LABELS.get(key) or key


def _allowed_keys(stage_id: str) -> set[str]:
    conf = _stage_conf(stage_id)
    allowed = conf.get("allowed_keys")
    if isinstance(allowed, set):
        return allowed
    if isinstance(allowed, (list, tuple)):
        return set(allowed)
    return set()


def _ordered_keys(stage_id: str, stage_dict: Dict[str, Any]) -> List[str]:
    if not isinstance(stage_dict, dict):
        return []
    conf = _stage_conf(stage_id)
    preferred: List[str] = list(conf.get("preferred_keys") or [])
    hidden: set[str] = set(conf.get("hidden_keys") or set())
    keys = list(stage_dict.keys())

    ordered: List[str] = []
    for k in preferred:
        if k in keys and k not in hidden:
            ordered.append(k)
    for k in sorted(keys):
        if k not in ordered and k not in hidden:
            ordered.append(k)

    allowed = _allowed_keys(stage_id)
    if allowed:
        ordered = [k for k in ordered if k in allowed]
    return ordered


# =========================================================
# FIX REAL (igual ao code que funciona):
# manter um dict "editável" por stage em state["edited_stages"].
# NÃO depender de st.session_state de widgets para hidratar do JSON.
# =========================================================
def _ensure_edited_stages(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    edited_stages = state.setdefault("edited_stages", {})
    if not isinstance(edited_stages, dict):
        edited_stages = {}
        state["edited_stages"] = edited_stages
    return edited_stages


def _prime_stage_if_missing(edited_stages: Dict[str, Dict[str, Any]], stage_id: str, stage_data: Dict[str, Any]) -> None:
    if stage_id not in edited_stages or not isinstance(edited_stages.get(stage_id), dict):
        edited_stages[stage_id] = dict(stage_data) if isinstance(stage_data, dict) else {}
        return

    # Se já existe, só completa chaves que não existem (não sobrescreve edições)
    cur = edited_stages[stage_id]
    if isinstance(stage_data, dict):
        for k, v in stage_data.items():
            if k not in cur:
                cur[k] = v


# =========================================================
# PDF helpers
# =========================================================
def _rubrica_line_table(styles: Dict[str, ParagraphStyle]) -> Table:
    h = ParagraphStyle("rb_h", parent=styles["body"], fontName="Helvetica-Bold", fontSize=9, leading=11)
    b = ParagraphStyle("rb", parent=styles["body"], fontName="Helvetica", fontSize=9, leading=11)
    row = [
        Paragraph("Avaliação do professor:", h),
        Paragraph("[ ] Aprendiz", b),
        Paragraph("[ ] Mago", b),
        Paragraph("[ ] Mestre", b),
        Paragraph("[ ] Feiticeiro", b),
    ]
    total_w = A4[0] - (1.6 * cm) - (1.6 * cm)
    label_w = 5.8 * cm
    opt_w = (total_w - label_w) / 4.0
    t = Table([row], colWidths=[label_w, opt_w, opt_w, opt_w, opt_w])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.grey),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _section_block(title: str, content_flowables: List[Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    story: List[Any] = []
    story.append(Paragraph(title, styles["h"]))

    left = content_flowables if content_flowables else [Paragraph("—", styles["body"])]

    outer_w = A4[0] - (1.6 * cm) - (1.6 * cm)

    # Se o conteúdo for uma Table, coloca direto no story e deixa quebrar em páginas
    if len(left) == 1 and isinstance(left[0], Table):
        t = left[0]
        try:
            t.splitByRow = 1
        except Exception:
            pass

        story.append(t)
        story.append(Spacer(1, 6))
        story.append(_rubrica_line_table(styles))
        story.append(Spacer(1, 8))
        return story

    # caso normal: caixa externa
    box = Table([[left]], colWidths=[outer_w])
    box.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(box)
    story.append(Spacer(1, 6))
    story.append(_rubrica_line_table(styles))
    story.append(Spacer(1, 8))
    return story




def _kv_table(stage_id: str, rows: List[Tuple[str, str]], styles: Dict[str, ParagraphStyle]) -> Table:
    data = []
    for k, v in rows:
        label = _field_label(stage_id, k)
        data.append(
            [
                Paragraph(f"<b>{_escape_xml(label)}</b>", styles["body"]),
                Paragraph(_nl_to_br(_escape_xml(v)) or "—", styles["body"]),
            ]
        )

    outer_w = A4[0] - (1.6 * cm) - (1.6 * cm)
    inner_w = outer_w - 12  # padding
    left_w = 6.0 * cm
    right_w = max(1.0, inner_w - left_w)

    t = Table(data, colWidths=[left_w, right_w])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f9fafb")),
            ]
        )
    )
    return t


def _fmt_value(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (str, int, float, bool)):
        return str(val)
    try:
        return json.dumps(val, ensure_ascii=False)
    except Exception:
        return str(val)


def _stage_to_flowables(stage_id: str, stage_data: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    if not isinstance(stage_data, dict) or not stage_data:
        return [Paragraph("—", styles["body"])]

    # Diagnóstico Inicial (PDF)
    if stage_id == DIAG_STAGE_ID:
        rows: List[Tuple[str, str]] = []
        if "saved_at" in stage_data:
            rows.append(("saved_at", _fmt_value(stage_data.get("saved_at"))))

        likert = stage_data.get("likert")
        if isinstance(likert, dict) and likert:
            lk_keys = [
                "l1_temp_calor",
                "l2_equilibrio",
                "l3_conducao",
                "l4_conveccao",
                "l5_radiacao",
                "l6_ar_fluido",
            ]
            for k in lk_keys:
                if k in likert:
                    rows.append((f"likert.{k}", _fmt_value(likert.get(k))))

        resultado = stage_data.get("resultado")
        if isinstance(resultado, dict) and "percentual" in resultado:
            rows.append(("resultado.percentual", _fmt_value(resultado.get("percentual"))))

        if "reflexao" in stage_data:
            rows.append(("reflexao", _fmt_value(stage_data.get("reflexao"))))

        if "concluido" in stage_data:
            rows.append(("concluido", _fmt_value(stage_data.get("concluido"))))

        return [_kv_table(stage_id, rows, styles)] if rows else [Paragraph("—", styles["body"])]

    # Conteúdos Essenciais (PDF)
    if stage_id == CONTEUDOS_STAGE_ID:
        rows: List[Tuple[str, str]] = []

        entend = stage_data.get("entendimentos")
        if isinstance(entend, dict) and entend:
            ent_keys = [
                "temp_escalas",
                "teoria_cinetica",
                "calor_transferencia",
                "conducao",
                "conveccao",
                "radiacao",
                "integracao",
                "primeira_lei",
                "equilibrio_termico",
            ]
            for k in ent_keys:
                if k in entend:
                    rows.append((f"entendimentos.{k}", _fmt_value(entend.get(k))))

        if "saved_at" in stage_data:
            rows.append(("saved_at", _fmt_value(stage_data.get("saved_at"))))

        # conteudos = stage_data.get("conteudos")
        # if isinstance(conteudos, list) and conteudos:
        #     rows.append(("conteudos", "\n".join(str(x) for x in conteudos)))

        # checklist = stage_data.get("checklist")
        # if isinstance(checklist, dict) and checklist:
        #     parts: List[str] = []
        #     for nome in sorted(checklist.keys()):
        #         item = checklist.get(nome) or {}
        #         if isinstance(item, dict):
        #             parts.append(f"{nome}: domina={item.get('domina')} | precisa_estudar={item.get('precisa_estudar')}")
        #         else:
        #             parts.append(f"{nome}: {_fmt_value(item)}")
        #     rows.append(("checklist", "\n".join(parts)))

        # if "sintese" in stage_data:
        #     rows.append(("sintese", _fmt_value(stage_data.get("sintese"))))

        # lacunas = stage_data.get("lacunas")
        # if isinstance(lacunas, list) and lacunas:
        #     rows.append(("lacunas", "\n".join(str(x) for x in lacunas)))

        return [_kv_table(stage_id, rows, styles)] if rows else [Paragraph("—", styles["body"])]

    # default
    ordered = _ordered_keys(stage_id, stage_data)
    rows_default: List[Tuple[str, str]] = []
    for k in ordered:
        rows_default.append((k, _fmt_value(stage_data.get(k))))
    return [_kv_table(stage_id, rows_default, styles)] if rows_default else [Paragraph("—", styles["body"])]


def _build_pdf_bytes(header: Dict[str, str], sections: List[Tuple[str, List[Any]]]) -> bytes:
    buf = BytesIO()

    styles_base = getSampleStyleSheet()
    styles: Dict[str, ParagraphStyle] = {
        "title": ParagraphStyle(
            "TitleCustom",
            parent=styles_base["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceAfter=10,
        ),
        "h": ParagraphStyle(
            "HCustom",
            parent=styles_base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=styles_base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "SmallCustom",
            parent=styles_base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=4,
        ),
    }

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Entregável Parcial — Problema",
        author="PBL App",
    )

    story: List[Any] = []
    story.append(Paragraph("Entregável Parcial — Problema", styles["title"]))

    header_lines = [
        f"<b>Aluno:</b> {_escape_xml(header.get('aluno', '—'))}",
        f"<b>Grupo:</b> {_escape_xml(header.get('grupo', '—'))}",
        f"<b>Data/Hora:</b> {_escape_xml(_now_iso())}",
    ]
    story.append(Paragraph("<br/>".join(header_lines), styles["body"]))
    story.append(Spacer(1, 8))

    for title, flow in sections:
        story += _section_block(title, flow, styles)

    story.append(
        Paragraph(
            "Observação: este PDF inclui seções selecionadas do problema (com possíveis edições para a versão de entrega).",
            styles["small"],
        )
    )

    doc.build(story)
    return buf.getvalue()


# =========================================================
# UI (edição das seções) — AGORA COMO O CÓDIGO QUE FUNCIONA
# =========================================================
def _render_stage_editor(
    kp: str,
    stage_id: str,
    stage_title: str,
    stage_data: Dict[str, Any],
    edited_stages: Dict[str, Dict[str, Any]],
    locked: bool,
) -> Dict[str, Any]:
    st.markdown(f"### {stage_title}")
    # st.caption(f"id: {stage_id}")

    # garante stage no estado editável e puxa do JSON na primeira vez
    _prime_stage_if_missing(edited_stages, stage_id, stage_data)
    current = edited_stages.get(stage_id, {})
    if not isinstance(current, dict):
        current = {}
        edited_stages[stage_id] = current

    # -------------------------
    # DIAGNÓSTICO: percentual RO + reflexao editável
    # -------------------------
    if stage_id == DIAG_STAGE_ID:
        resultado = current.get("resultado") if isinstance(current.get("resultado"), dict) else {}
        percentual = ""
        if isinstance(resultado, dict) and "percentual" in resultado:
            percentual = str(resultado.get("percentual"))

        st.text_input(
            _GLOBAL_LABELS.get("resultado.percentual", "Porcentagem de acertos"),
            value=percentual,
            disabled=True,
            key=f"{kp}_{stage_id}_percentual_ro",
        )

        reflexao_val = "" if current.get("reflexao") is None else str(current.get("reflexao"))
        current["reflexao"] = st.text_area(
            _GLOBAL_LABELS.get("reflexao", "Ponto de partida conceitual"),
            value=reflexao_val,
            height=140,
            disabled=locked,
            key=f"{kp}_{stage_id}_reflexao_ta",
        )

        st.markdown("---")
        return current

    # -------------------------
    # CONTEÚDOS: entendimentos (todos) + conteudos + sintese + lacunas editáveis
    # checklist RO
    # -------------------------
    if stage_id == CONTEUDOS_STAGE_ID:
        ent_keys = [
            "temp_escalas",
            "teoria_cinetica",
            "calor_transferencia",
            "conducao",
            "conveccao",
            "radiacao",
            "integracao",
            "primeira_lei",
            "equilibrio_termico",
        ]

        if not isinstance(current.get("entendimentos"), dict):
            current["entendimentos"] = {}
        ent = current["entendimentos"]

        for k in ent_keys:
            ent_val = "" if ent.get(k) is None else str(ent.get(k))
            ent[k] = st.text_area(
                _GLOBAL_LABELS.get(f"entendimentos.{k}", f"Entendimentos: {k}"),
                value=ent_val,
                height=110,
                disabled=locked,
                key=f"{kp}_{stage_id}_{k}_ta",
            )

        # conteudos (lista -> textarea)
        # conteudos = current.get("conteudos")
        # conteudos_text = "\n".join(str(x) for x in conteudos) if isinstance(conteudos, list) else ""
        # conteudos_new = st.text_area(
        #     _GLOBAL_LABELS.get("conteudos", "Conteúdos"),
        #     value=conteudos_text,
        #     height=140,
        #     disabled=locked,
        #     key=f"{kp}_{stage_id}_conteudos_ta",
        # )
        # current["conteudos"] = [ln.strip() for ln in conteudos_new.splitlines() if ln.strip()]

        # # checklist RO
        # checklist = current.get("checklist")
        # if isinstance(checklist, dict) and checklist:
        #     parts: List[str] = []
        #     for nome in sorted(checklist.keys()):
        #         item = checklist.get(nome) or {}
        #         if isinstance(item, dict):
        #             parts.append(f"{nome}: domina={item.get('domina')} | precisa_estudar={item.get('precisa_estudar')}")
        #         else:
        #             parts.append(f"{nome}: {item}")
        #     st.text_area(
        #         _GLOBAL_LABELS.get("checklist", "Checklist"),
        #         value="\n".join(parts),
        #         height=160,
        #         disabled=True,
        #         key=f"{kp}_{stage_id}_checklist_ro",
        #     )

        # # sintese
        # sintese_val = "" if current.get("sintese") is None else str(current.get("sintese"))
        # current["sintese"] = st.text_area(
        #     _GLOBAL_LABELS.get("sintese", "Síntese"),
        #     value=sintese_val,
        #     height=110,
        #     disabled=locked,
        #     key=f"{kp}_{stage_id}_sintese_ta",
        # )

        # # lacunas (lista -> textarea)
        # lacunas = current.get("lacunas")
        # lacunas_text = "\n".join(str(x) for x in lacunas) if isinstance(lacunas, list) else ""
        # lacunas_new = st.text_area(
        #     _GLOBAL_LABELS.get("lacunas", "Lacunas"),
        #     value=lacunas_text,
        #     height=110,
        #     disabled=locked,
        #     key=f"{kp}_{stage_id}_lacunas_ta",
        # )
        # current["lacunas"] = [ln.strip() for ln in lacunas_new.splitlines() if ln.strip()]

        # st.markdown("---")
        return current

    # -------------------------
    # DEFAULT: render só allowed_keys (igual ao “funciona”)
    # -------------------------
    ordered = _ordered_keys(stage_id, current)
    allowed = _allowed_keys(stage_id)
    ordered = [k for k in ordered if (not allowed) or (k in allowed)]

    # regra: esconder saved_at nas seções que você já escondia
    if stage_id in {ESCOPO_STAGE_ID, PERGUNTA_STAGE_ID}:
        ordered = [k for k in ordered if k != "saved_at"]

    for k in ordered:
        v = current.get(k)
        label = _field_label(stage_id, k)

        if isinstance(v, str):
            if len(v) > 80 or "\n" in v:
                current[k] = st.text_area(
                    label, value=v, height=140, disabled=locked, key=f"{kp}_{stage_id}_{k}_ta"
                )
            else:
                current[k] = st.text_input(label, value=v, disabled=locked, key=f"{kp}_{stage_id}_{k}_ti")
            continue

        current[k] = st.text_input(
            label,
            value="" if v is None else str(v),
            disabled=locked,
            key=f"{kp}_{stage_id}_{k}_fb",
        )

    st.markdown("---")
    return current


# =========================================================
# render (UI)
# =========================================================
def render(ctx: Dict) -> None:
    kp = _key_prefix(ctx)

    aluno = (ctx.get("aluno") or "Aluno").strip()
    grupo_id = (ctx.get("grupo_id") or "").strip()
    grupo_nome = (ctx.get("grupo_nome") or "").strip()

    if grupo_id and grupo_nome:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id} ({grupo_nome})")
    elif grupo_id:
        st.caption(f"Aluno: {aluno} — Grupo {grupo_id}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = OUT_DIR / f"{_safe_filename(aluno).lower()}_01_problema.pdf"
    locked = pdf_path.exists()

    if locked:
        st.success("Entregável bloqueado porque o PDF já existe.")
        st.caption(f"PDF: {pdf_path}")
        st.info("Se o professor apagar o PDF, esta tela destrava automaticamente.")
        st.markdown("---")

    container_path = _problema_path(aluno)
    root = load_json(container_path) or {}

    if not isinstance(root, dict):
        st.error("Não foi possível ler o JSON consolidado em data/problema para este aluno.")
        st.caption(f"Esperado: {container_path}")
        return

    stages: Dict[str, Any] = root.get("stages", {}) if isinstance(root.get("stages"), dict) else {}
    if not stages:
        st.error("Não foi possível localizar o objeto 'stages' no JSON consolidado.")
        st.caption(f"Arquivo: {container_path}")
        return

    contextualizacao_data = stages.get(TARGET_STAGE_ID, {})
    if not isinstance(contextualizacao_data, dict):
        contextualizacao_data = {}

    escopo_data = stages.get(ESCOPO_STAGE_ID, {})
    if not isinstance(escopo_data, dict):
        escopo_data = {}

    pergunta_data = stages.get(PERGUNTA_STAGE_ID, {})
    if not isinstance(pergunta_data, dict):
        pergunta_data = {}

    diag_data = stages.get(DIAG_STAGE_ID, {})
    if not isinstance(diag_data, dict):
        diag_data = {}

    conteudos_data = stages.get(CONTEUDOS_STAGE_ID, {})
    if not isinstance(conteudos_data, dict):
        conteudos_data = {}

    draft_path = stage_path(ctx, STAGE_ID)
    state = _ctx_get_state(ctx)


    # carregar rascunho (AGORA lendo o mesmo formato do code que funciona: edited_stages)
    if not _get(state, "__loaded__", False):
        saved_draft = load_json(draft_path) or {}
        if isinstance(saved_draft, dict):
            if isinstance(saved_draft.get("edited_stages"), dict):
                state["edited_stages"] = saved_draft["edited_stages"]
            # compat: aceita seu formato antigo edited_map, se existir
            elif isinstance(saved_draft.get("edited_map"), dict):
                # converte edited_map -> edited_stages
                state["edited_stages"] = saved_draft["edited_map"]

            if isinstance(saved_draft.get("ui_cache"), dict):
                for k, v in saved_draft["ui_cache"].items():
                    if k not in state:
                        state[k] = v

        _set(state, "__loaded__", True)

    edited_stages = _ensure_edited_stages(state)

    # “prime” com JSON atual (sem sobrescrever edições)
    _prime_stage_if_missing(edited_stages, TARGET_STAGE_ID, contextualizacao_data)
    _prime_stage_if_missing(edited_stages, ESCOPO_STAGE_ID, escopo_data)
    _prime_stage_if_missing(edited_stages, PERGUNTA_STAGE_ID, pergunta_data)
    _prime_stage_if_missing(edited_stages, DIAG_STAGE_ID, diag_data)
    _prime_stage_if_missing(edited_stages, CONTEUDOS_STAGE_ID, conteudos_data)

    edited_contextualizacao = _render_stage_editor(
        kp=kp,
        stage_id=TARGET_STAGE_ID,
        stage_title=TARGET_STAGE_TITLE,
        stage_data=contextualizacao_data,
        edited_stages=edited_stages,
        locked=locked,
    )

    edited_escopo = _render_stage_editor(
        kp=kp,
        stage_id=ESCOPO_STAGE_ID,
        stage_title=ESCOPO_TITLE,
        stage_data=escopo_data,
        edited_stages=edited_stages,
        locked=locked,
    )

    edited_pergunta = _render_stage_editor(
        kp=kp,
        stage_id=PERGUNTA_STAGE_ID,
        stage_title=PERGUNTA_TITLE,
        stage_data=pergunta_data,
        edited_stages=edited_stages,
        locked=locked,
    )

    edited_diag = _render_stage_editor(
        kp=kp,
        stage_id=DIAG_STAGE_ID,
        stage_title=DIAG_TITLE,
        stage_data=diag_data,
        edited_stages=edited_stages,
        locked=locked,
    )

    edited_conteudos = _render_stage_editor(
        kp=kp,
        stage_id=CONTEUDOS_STAGE_ID,
        stage_title=CONTEUDOS_TITLE,
        stage_data=conteudos_data,
        edited_stages=edited_stages,
        locked=locked,
    )

    msg = st.empty()
    col1, col2 = st.columns([1, 1])

    # with col1:
    #     if st.button("Salvar rascunho (edições)", key=f"{kp}_draft", disabled=locked):
    #         payload = {
    #             "stage_id": STAGE_ID,
    #             "saved_at": _now_iso(),
    #             "source_json": str(container_path),
    #             "aluno": aluno,
    #             "grupo_id": grupo_id,
    #             "grupo_nome": grupo_nome,
    #             "edited_stages": edited_stages,  # <<< igual ao “code que funciona”
    #             "ui_cache": {k: v for k, v in state.items() if str(k).startswith("__")},
    #         }
    #         save_json(draft_path, payload)
    #         msg.success("Rascunho salvo (sem alterar o JSON original do aluno).")

    with col2:
        if st.button("Gerar PDF (inclui e trava)", key=f"{kp}_submit", disabled=locked):
            header = {
                "aluno": aluno,
                "grupo": f"{grupo_id} {('- ' + grupo_nome) if grupo_nome else ''}".strip() or "—",
            }

            styles_base = getSampleStyleSheet()
            styles_pdf: Dict[str, ParagraphStyle] = {
                "body": ParagraphStyle(
                    "BodyCustom",
                    parent=styles_base["BodyText"],
                    fontName="Helvetica",
                    fontSize=10.5,
                    leading=14,
                    spaceAfter=6,
                )
            }

            # usa SEMPRE edited_stages (se existir), senão cai no original
            def _final_stage(sid: str, original: Dict[str, Any]) -> Dict[str, Any]:
                v = edited_stages.get(sid, original)
                return v if isinstance(v, dict) else original

            flow_contextualizacao = _stage_to_flowables(TARGET_STAGE_ID, _final_stage(TARGET_STAGE_ID, contextualizacao_data), styles_pdf)
            flow_escopo = _stage_to_flowables(ESCOPO_STAGE_ID, _final_stage(ESCOPO_STAGE_ID, escopo_data), styles_pdf)
            flow_pergunta = _stage_to_flowables(PERGUNTA_STAGE_ID, _final_stage(PERGUNTA_STAGE_ID, pergunta_data), styles_pdf)
            flow_diag = _stage_to_flowables(DIAG_STAGE_ID, _final_stage(DIAG_STAGE_ID, diag_data), styles_pdf)
            flow_conteudos = _stage_to_flowables(CONTEUDOS_STAGE_ID, _final_stage(CONTEUDOS_STAGE_ID, conteudos_data), styles_pdf)

            pdf_bytes = _build_pdf_bytes(
                header=header,
                sections=[
                    (TARGET_STAGE_TITLE, flow_contextualizacao),
                    (ESCOPO_TITLE, flow_escopo),
                    (PERGUNTA_TITLE, flow_pergunta),
                    (DIAG_TITLE, flow_diag),
                    (CONTEUDOS_TITLE, flow_conteudos),
                ],
            )

            pdf_path.write_bytes(pdf_bytes)

            export_payload = {
                "stage_id": STAGE_ID,
                "generated_at": _now_iso(),
                "pdf_path": str(pdf_path),
                "source_json": str(container_path),
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
                "exported_stage_ids": [
                    TARGET_STAGE_ID,
                    ESCOPO_STAGE_ID,
                    PERGUNTA_STAGE_ID,
                    DIAG_STAGE_ID,
                    CONTEUDOS_STAGE_ID,
                ],
                "exported_stages": {
                    TARGET_STAGE_ID: _final_stage(TARGET_STAGE_ID, contextualizacao_data),
                    ESCOPO_STAGE_ID: _final_stage(ESCOPO_STAGE_ID, escopo_data),
                    PERGUNTA_STAGE_ID: _final_stage(PERGUNTA_STAGE_ID, pergunta_data),
                    DIAG_STAGE_ID: _final_stage(DIAG_STAGE_ID, diag_data),
                    CONTEUDOS_STAGE_ID: _final_stage(CONTEUDOS_STAGE_ID, conteudos_data),
                },
                "edited_stages_snapshot": edited_stages,
            }
            save_json(draft_path, export_payload)

            msg.success("PDF gerado. O entregável agora está bloqueado pelo PDF.")
            st.caption(f"PDF salvo em: {pdf_path}")
            st.download_button(
                "Baixar PDF",
                data=pdf_bytes,
                file_name=pdf_path.name,
                mime="application/pdf",
            )
            st.rerun()
