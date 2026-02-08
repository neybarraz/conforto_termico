# blocks/investigacao/06_registro_parcial__investigacao_completo.py
from __future__ import annotations

import json
import re
import unicodedata
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from storage.io_csv import load_json, save_json
from storage.paths import stage_path


# =========================================================
# CONFIG (PDF único)
# =========================================================
OUT_DIR = Path("data/pdf")
INV_DIR = Path("data/investigacao")

# ÚNICO PDF / ÚNICO lock / ÚNICO botão
STAGE_ID = "investigacao_entregavel_readonly_v6__completo"
PDF_SUFFIX = "02_investigacao.pdf"


# =========================================================
# =============== 06a — RESTANTE (lógica original) =========
# =========================================================

A_STAGE_TITLE_OVERRIDES: Dict[str, str] = {
    "investigacao_grandezas_fisicas_medidas": "Grandezas físicas e medidas",
    "investigacao_contexto_medicao": "Contexto da medição",
    "investigacao_estrutura_do_ambiente": "Estrutura do ambiente",
    "investigacao_coleta_de_dados": "Coleta de dados",
    # IMPORTANTE: aqui NÃO incluímos:
    # - investigacao_grafico_gradiente_termico
    # - investigacao_analise_radiacao_conforto
}

A_LABEL_OVERRIDES: Dict[str, str] = {
    "last_loaded_at": "Último carregamento",
    "last_generated_at": "Última geração",
    "horario_ref": "Horário de referência",
    "horario": "Horário da coleta",

    "rodadas_medicoes": "Rodadas de medições",
    "ta_rows": "Tabela Ta (ar)",
    "ts_rows": "Tabela Ts (superfície)",
    "Ta_C": "Ta (°C)",
    "Ts_C": "Ts (°C)",
    "UR_pct": "UR (%)",
    "v_ms": "v (m/s)",

    "ambiente_medicao": "Ambiente de medição",
    "hora": "Hora:",
    "ambiente_id": "Ambiente",
    "condicoes_coleta": "Condições da coleta",
    "ocupacao": "Ocupação",
    "incidencia_solar": "Incidência solar",
    "condicao_externa": "Condição externa",
    "ventilacao_aberturas": "Ventilação — Aberturas",
    "ventilacao_mecanica": "Ventilação — Mecânica",
    "percepcao_termica": "Percepção térmica",
    "descricao": "Faça uma breve descrição da sensação térmica:",
    "diferencas_regioes": "Percebeu alguma diferença entre as regiões no interior do ambiente?",
    "janelas": "As janelas estão abertas?",
    "portas": "As portas estão fechadas?",
    "tipo": "Qual é a ventilação mecânica?",
    "estado": "A ventilação mecânica está ligada?",
    "sensacao": "Qual é a sensação térmica percebida?",
    "intensidade": "Qual a intensidade percebida?",

    "grandezas_detalhes": "Grandezas e instrumentos",
    "instrumento": "Instrumento",
    "tempo_espera": "Tempo de espera",

    "figura_png": "Figura",
    "orientacao_dimensoes": "Orientação e dimensões",
    "orientacao_topo": "Orientação do topo",
    "dimensoes": "Dimensões",
    "largura_m": "Largura (m)",
    "profundidade_m": "Profundidade (m)",
    "paredes_aberturas": "Paredes e aberturas",
    "estrutura_ambiente": "Estrutura do ambiente",
    "paredes": "Paredes",
    "porta": "Porta",
    "janela": "Janela",
    "vm": "Ventilação mecânica (VM)",
    "existe": "Existe",
    "inicio_frac": "Início (fração)",
    "fim_frac": "Fim (fração)",
    "center_frac": "Centro (fração)",
    "pos_frac": "Posição (fração)",
    "pontos_medicao": "Pontos de medição",
    "id": "ID",
    "label": "Label",
    "x_frac": "x (fração)",
    "y_frac": "y (fração)",

    "respostas": "Respostas",
    "snapshot": "Snapshot",
    "ts_ids": "IDs Ts",
    "ta_id": "ID Ta",
    "ta_C": "Ta (°C)",
    "ts_C": "Ts (°C)",
    "deltas_C": "ΔT (°C)",
    "fluxo": "Fluxo",
    "ts1": "ts1",
    "ts2": "ts2",
    "delta_C": "ΔT (°C)",
    "delta": "ΔT (°C)",
    "escolha": "Escolha",
    "gabarito_esperado": "Gabarito esperado",
    "esperado": "Esperado",
    "conforto_radiativo": "Conforto radiativo",
    "referencia": "Referência",
    "ts_media_C": "Ts média (°C)",
    "ts_media_minus_ta_C": "Ts média − Ta (°C)",

    "params_fixos": "Parâmetros fixos",
    "meta": "Metadados",

    "conf_01": "Um único valor de temperatura média descreve o conforto neste ambiente? Por quê?",
    "conf_02": "Como a posição do ocupante em relação às paredes afeta o conforto (radiação + convecção)?",
    "conf_03": "Cite 2 estratégias de projeto para reduzir os gradientes observados (envoltória/isolamento/ventilação/sombreamento).",

    "modes_01": "Condução: como o calor chega à superfície interna das paredes? O que a condução determina (Ts)?",
    "modes_02": "Convecção: como a parede troca calor com o ar próximo? Por que existe gradiente perto da parede (camada limite)?",
    "modes_03": "Radiação: mesmo sem tocar nas paredes, um ocupante sentiria diferença? Explique usando temperatura radiante média.",

    "obs_01": "O que as cores diferentes representam fisicamente neste mapa?",
    "obs_02": "Se a imagem é vista de cima e os quatro lados são paredes, por que a temperatura não é uniforme no interior?",
    "obs_03": "Onde estão os maiores gradientes de temperatura? O que isso sugere sobre o papel das paredes?",

    "pl_01": "Escreva a Primeira Lei e indique qual termo você considera desprezível neste caso (W≈0 ou não). Justifique.",
    "pl_02": "Com W≈0, explique por que o mapa de T pode ser interpretado como consequência de Q (trocas de calor).",

    "reg_01": "Este mapa parece representar regime permanente ou transitório? Qual evidência sustenta sua resposta?",
    "reg_02": "Em regime permanente, o que a Primeira Lei implica para o balanço de energia (Q_entra = Q_sai)?",

    "ut_01": "Em um gás como o ar, o que a temperatura mede (interpretação microscópica)?",
    "ut_02": "Se a temperatura varia no espaço, o que isso indica sobre a distribuição de energia interna?",

    "syn_01": "Síntese final",
}

A_STAGE_ORDER = [
    "investigacao_grandezas_fisicas_medidas",
    "investigacao_contexto_medicao",
    "investigacao_estrutura_do_ambiente",
    "investigacao_coleta_de_dados",
]

A_HIDDEN_KEYS = {
    "saved_at",
    "last_loaded_at",
    "last_generated_at",
}

A_PROMPT_KEYS = {"descricao", "diferencas_regioes", "justificativa", "texto", "conforto"}
A_PROMPT_PATH_CONTAINS = set()


# =========================================================
# utilidades (compartilhadas / do 06a)
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
    return (name or "aluno").lower()



def _investigacao_path(aluno: str) -> Path:
    INV_DIR.mkdir(parents=True, exist_ok=True)
    return INV_DIR / f"{_safe_filename(aluno)}_investigacao.json"


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


def _nl_to_br(s: str) -> str:
    return (s or "").replace("\n", "<br/>").strip()


def _fmt_value(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (str, int, float, bool)):
        return str(val)
    try:
        return json.dumps(val, ensure_ascii=False, indent=2)
    except Exception:
        return str(val)


def _title_for_stage(stage_id: str) -> str:
    return A_STAGE_TITLE_OVERRIDES.get(stage_id, stage_id)


def _label_for_key(key: str) -> str:
    return A_LABEL_OVERRIDES.get(key, f"IDENTIFICAR: {key}")


def _sort_key_like_obs01(k: str) -> Tuple[str, int]:
    m = re.match(r"^([a-zA-Z_]+)0*([0-9]+)$", (k or "").strip())
    if m:
        return (m.group(1), int(m.group(2)))
    return ("zz", 10**9)


def _is_list_of_dicts(x: Any) -> bool:
    return isinstance(x, list) and x and all(isinstance(i, dict) for i in x)


def _should_render_as_prompt(path: str, key: str) -> bool:
    if key in A_PROMPT_KEYS:
        return True
    for p in A_PROMPT_PATH_CONTAINS:
        if p in (path or ""):
            return True
    return False


def _looks_like_instruction_text(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return False
    if t.endswith(":") or t.endswith("?"):
        return True
    instr = ["Justifique", "Explique", "Descreva", "Faça", "Cite", "Indique", "Escreva", "Calcule"]
    return any(w.lower() in t.lower() for w in instr)


# =========================================================
# PDF helpers (do 06a)
# =========================================================
def _make_pdf_styles() -> Dict[str, ParagraphStyle]:
    styles_base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCustom",
            parent=styles_base["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "H1Custom",
            parent=styles_base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "H2Custom",
            parent=styles_base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            spaceBefore=8,
            spaceAfter=4,
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


def _pdf_kv_table(rows: List[Tuple[str, str]], styles: Dict[str, ParagraphStyle]) -> Table:
    data = []
    for k, v in rows:
        data.append(
            [
                Paragraph(f"<b>{_escape_xml(k)}</b>", styles["body"]),
                Paragraph(_nl_to_br(_escape_xml(v)) or "—", styles["body"]),
            ]
        )

    outer_w = A4[0] - (1.6 * cm) - (1.6 * cm)
    inner_w = outer_w - 12
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


def _pdf_table_from_rows(headers: List[str], rows: List[List[str]]) -> Table:
    styles_base = getSampleStyleSheet()

    cell_style = ParagraphStyle(
        "CellWrap",
        parent=styles_base["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=13,
        wordWrap="CJK",  # <- quebra mesmo sem espaços (NNNNNN11111...)
    )

    head_style = ParagraphStyle(
        "HeadWrap",
        parent=styles_base["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        wordWrap="CJK",
    )

    # Converte tudo para Paragraph (inclui cabeçalho)
    data = [[Paragraph(str(h or ""), head_style) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c or ""), cell_style) for c in r])

    t = Table(data, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t



def _pdf_blank_box(height_pts: int = 72) -> Table:
    t = Table([[""]], colWidths=[A4[0] - (1.6 * cm) - (1.6 * cm)], rowHeights=[height_pts])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#9ca3af")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )
    return t


def _pdf_box_text(text: str, styles: Dict[str, ParagraphStyle]) -> Table:
    w = A4[0] - (1.6 * cm) - (1.6 * cm)
    p = Paragraph(_nl_to_br(_escape_xml(text)) or "—", styles["body"])
    t = Table([[p]], colWidths=[w])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#9ca3af")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _build_pdf_bytes(header: Dict[str, str], story: List[Any]) -> bytes:
    buf = BytesIO()
    styles = _make_pdf_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Entregável — Investigação (Completo)",
        author="PBL App",
    )

    base: List[Any] = []
    base.append(Paragraph("Entregável — Investigação (Completo)", styles["title"]))

    header_lines = [
        f"<b>Aluno:</b> {_escape_xml(header.get('aluno', '—'))}",
        f"<b>Grupo:</b> {_escape_xml(header.get('grupo', '—'))}",
        f"<b>Data/Hora:</b> {_escape_xml(_now_iso())}",
    ]
    base.append(Paragraph("<br/>".join(header_lines), styles["body"]))
    base.append(Spacer(1, 10))

    base.extend(story)
    base.append(Spacer(1, 8))
    # base.append(
    #     Paragraph(
    #         "Observação: PDF gerado a partir do conteúdo exibido na tela (modo somente leitura).",
    #         styles["small"],
    #     )
    # )

    doc.build(base)
    return buf.getvalue()


# =========================================================
# Render plan (do 06a)
# =========================================================
class RenderItem:
    # kind: h1 | h2 | kv | table | image | plain | blank | spacer
    def __init__(self, kind: str, title: str = "", payload: Any = None):
        self.kind = kind
        self.title = title
        self.payload = payload


def _collect_items_from_value(key: str, val: Any, path: str) -> List[RenderItem]:
    items: List[RenderItem] = []

    if key in A_HIDDEN_KEYS:
        return items

    # ---------------------------------------------------------
    # SPECIAL-CASE: rodadas_medicoes (Coleta de dados)
    # ---------------------------------------------------------
    if key == "rodadas_medicoes" and isinstance(val, list):
        items.append(RenderItem("h2", title=_label_for_key(key)))

        for idx, rodada in enumerate(val, start=1):
            if not isinstance(rodada, dict):
                continue

            horario = _fmt_value(rodada.get("horario") or rodada.get("horario_ref") or "").strip()
            items.append(RenderItem("h2", title=f"{_label_for_key('horario')}: {horario or '—'}"))

            # Ta
            ta_rows = rodada.get("ta_rows")
            if isinstance(ta_rows, list) and ta_rows and all(isinstance(r, dict) for r in ta_rows):
                headers_keys = ["id", "Ta_C", "UR_pct", "v_ms"]
                headers = [_label_for_key(k) for k in headers_keys]
                rows = [[_fmt_value(r.get(k, "")) for k in headers_keys] for r in ta_rows]
                items.append(RenderItem("h2", title=_label_for_key("ta_rows")))
                items.append(RenderItem("table", payload={"headers": headers, "rows": rows}))

            # Ts
            ts_rows = rodada.get("ts_rows")
            if isinstance(ts_rows, list) and ts_rows and all(isinstance(r, dict) for r in ts_rows):
                headers_keys = ["id", "Ts_C"]
                headers = [_label_for_key(k) for k in headers_keys]
                rows = [[_fmt_value(r.get(k, "")) for k in headers_keys] for r in ts_rows]
                items.append(RenderItem("h2", title=_label_for_key("ts_rows")))
                items.append(RenderItem("table", payload={"headers": headers, "rows": rows}))

            if idx != len(val):
                items.append(RenderItem("spacer"))

        return items

    # Figura
    if isinstance(val, str) and key == "figura_png":
        items.append(RenderItem("h2", title=_label_for_key(key)))
        items.append(RenderItem("image", payload=val))
        return items

    # grandezas_detalhes como tabela única
    if isinstance(val, dict) and key == "grandezas_detalhes":
        rows: List[List[str]] = []
        for grandeza, info in val.items():
            if isinstance(info, dict):
                rows.append(
                    [
                        str(grandeza),
                        _fmt_value(info.get("instrumento", "")).strip(),
                        _fmt_value(info.get("tempo_espera", "")).strip(),
                    ]
                )
            else:
                rows.append([str(grandeza), _fmt_value(info).strip(), ""])
        rows.sort(key=lambda r: r[0].lower())

        items.append(RenderItem("h2", title=_label_for_key(key)))
        items.append(
            RenderItem(
                "table",
                payload={
                    "headers": ["Grandeza", _label_for_key("instrumento"), _label_for_key("tempo_espera")],
                    "rows": rows,
                },
            )
        )
        return items

    # dict geral
    if isinstance(val, dict):
        filtered = {k: v for k, v in val.items() if k not in A_HIDDEN_KEYS}

        simple = all(not isinstance(v, (dict, list)) for v in filtered.values())
        if simple and filtered:
            rows_kv = []
            for k2 in sorted(filtered.keys(), key=_sort_key_like_obs01):
                rows_kv.append((_label_for_key(k2), _fmt_value(filtered.get(k2))))
            items.append(RenderItem("h2", title=_label_for_key(key) if key else path))
            items.append(RenderItem("kv", payload=rows_kv))
            return items

        if key:
            items.append(RenderItem("h2", title=_label_for_key(key)))
        for k2 in sorted(filtered.keys(), key=lambda s: str(s)):
            items.extend(_collect_items_from_value(k2, filtered[k2], f"{path}.{k2}" if path else k2))
        return items

    # lista de dicts -> tabela
    if _is_list_of_dicts(val):
        keys: List[str] = []
        seen = set()
        for row in val:
            for k2 in row.keys():
                if k2 in A_HIDDEN_KEYS:
                    continue
                if k2 not in seen:
                    keys.append(k2)
                    seen.add(k2)

        headers = [_label_for_key(k) for k in keys]
        rows = []
        for row in val:
            rows.append([_fmt_value(row.get(k)) for k in keys])

        items.append(RenderItem("h2", title=_label_for_key(key) if key else path))
        items.append(RenderItem("table", payload={"headers": headers, "rows": rows}))
        return items

    # lista genérica -> texto compacto
    if isinstance(val, list):
        joined = ", ".join([_fmt_value(x) for x in val])
        items.append(RenderItem("h2", title=_label_for_key(key) if key else path))
        items.append(RenderItem("plain", payload=joined))
        return items

    # valor simples
    val_txt = _fmt_value(val).strip()

    if _should_render_as_prompt(path, key) and _looks_like_instruction_text(val_txt):
        items.append(RenderItem("h2", title=val_txt if val_txt else _label_for_key(key)))
        items.append(RenderItem("blank", payload={"height": 90}))
        return items

    if key:
        items.append(RenderItem("h2", title=_label_for_key(key)))
    items.append(RenderItem("plain", payload=val_txt))
    return items


def _collect_story_from_stage(stage_id: str, stage_obj: Any) -> List[RenderItem]:
    items: List[RenderItem] = []
    items.append(RenderItem("h1", title=_title_for_stage(stage_id)))

    # =========================================================
    # SPECIAL-CASE: "Estrutura do ambiente"
    # Mostrar SOMENTE:
    #   1) figura_png
    #   2) dimensões (largura_m, profundidade_m)
    # =========================================================
    if isinstance(stage_obj, dict) and _title_for_stage(stage_id) == "Estrutura do ambiente":
        fig = stage_obj.get("figura_png")
        if isinstance(fig, str) and fig:
            items.extend(_collect_items_from_value("figura_png", fig, stage_id))

        dims = None
        if isinstance(stage_obj.get("dimensoes"), dict):
            dims = stage_obj.get("dimensoes")
        elif (
            isinstance(stage_obj.get("orientacao_dimensoes"), dict)
            and isinstance(stage_obj["orientacao_dimensoes"].get("dimensoes"), dict)
        ):
            dims = stage_obj["orientacao_dimensoes"].get("dimensoes")

        if isinstance(dims, dict):
            rows_kv = []
            if "largura_m" in dims:
                rows_kv.append((_label_for_key("largura_m"), _fmt_value(dims.get("largura_m"))))
            if "profundidade_m" in dims:
                rows_kv.append((_label_for_key("profundidade_m"), _fmt_value(dims.get("profundidade_m"))))

            if rows_kv:
                items.append(RenderItem("h2", title=_label_for_key("dimensoes")))
                items.append(RenderItem("kv", payload=rows_kv))

        items.append(RenderItem("spacer"))
        return items

    # default (outros stages)
    if isinstance(stage_obj, dict):
        if "figura_png" in stage_obj:
            items.extend(_collect_items_from_value("figura_png", stage_obj.get("figura_png"), stage_id))

        keys = [
            k for k in stage_obj.keys()
            if k not in ("stage_id", "figura_png")
            and k not in A_HIDDEN_KEYS
        ]

        for k in sorted(keys):
            items.extend(_collect_items_from_value(k, stage_obj.get(k), f"{stage_id}.{k}"))
    else:
        items.append(RenderItem("plain", payload=_fmt_value(stage_obj)))

    items.append(RenderItem("spacer"))
    return items


# =========================================================
# UI render — compact box padrão (do 06a)
# =========================================================
def _ui_box_value_compact(text: str) -> None:
    with st.container(border=True):
        safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br/>")
        st.markdown(
            f"""
            <div style="
                padding-top: 6px;
                padding-bottom: 10px;
                padding-left: 12px;
                padding-right: 12px;
                line-height: 1.45;
                font-size: 0.95rem;
                color: rgba(200, 220, 255, 0.75);
                ">
                {safe if safe else "&nbsp;"}
            </div>
            """,
            unsafe_allow_html=True,
        )


def _ui_box_blank(key: str, height: int = 110) -> None:
    with st.container(border=True):
        st.text_area(
            label="",
            value="",
            disabled=True,
            height=height,
            label_visibility="collapsed",
            key=key,
        )


def _ui_box_table(df_rows: List[Dict[str, Any]]) -> None:
    with st.container(border=True):
        st.dataframe(df_rows, use_container_width=True, hide_index=True)


def _ui_box_kv(rows):
    df = pd.DataFrame(rows, columns=["Campo", "Valor"]).set_index("Campo")
    with st.container(border=True):
        st.table(df)


def _render_items_to_ui(items: List["RenderItem"], aluno: str) -> None:
    safe_aluno = _safe_filename(aluno)

    for i, it in enumerate(items):
        base_key = f"{STAGE_ID}__{safe_aluno}__{i}"

        if it.kind == "h1":
            st.markdown(f"### {it.title}")

        elif it.kind == "h2":
            st.markdown(f"**{it.title}**")

        elif it.kind == "kv":
            _ui_box_kv(it.payload or [])

        elif it.kind == "table":
            payload = it.payload or {}
            headers = payload.get("headers", [])
            rows = payload.get("rows", [])
            df_rows = [dict(zip(headers, r)) for r in rows]
            _ui_box_table(df_rows)

        elif it.kind == "image":
            p = str(it.payload or "")
            with st.container(border=True):
                if p and Path(p).exists():
                    st.image(p, use_container_width=True)
                else:
                    st.info(f"Imagem não encontrada: {p}")

        elif it.kind == "plain":
            _ui_box_value_compact("" if it.payload is None else str(it.payload))

        elif it.kind == "blank":
            h = int((it.payload or {}).get("height", 90))
            _ui_box_blank(key=f"{base_key}__blank", height=h)

        elif it.kind == "spacer":
            st.markdown("---")


def _render_items_to_pdf_story(items: List["RenderItem"], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    story: List[Any] = []

    for it in items:
        if it.kind == "h1":
            story.append(Paragraph(_escape_xml(it.title), styles["h1"]))

        elif it.kind == "h2":
            story.append(Paragraph(_escape_xml(it.title), styles["h2"]))

        elif it.kind == "kv":
            rows = it.payload or []
            story.append(_pdf_kv_table(rows, styles))
            story.append(Spacer(1, 8))

        elif it.kind == "table":
            payload = it.payload or {}
            headers = payload.get("headers", [])
            rows = payload.get("rows", [])
            story.append(_pdf_table_from_rows(headers, rows))
            story.append(Spacer(1, 8))

        elif it.kind == "image":
            p = str(it.payload or "")
            if p and Path(p).exists():
                img = RLImage(p)
                max_w = A4[0] - (1.6 * cm) - (1.6 * cm)
                if img.drawWidth > max_w:
                    scale = max_w / float(img.drawWidth)
                    img.drawWidth *= scale
                    img.drawHeight *= scale
                story.append(img)
                story.append(Spacer(1, 8))
            else:
                story.append(Paragraph(_escape_xml(f"Imagem não encontrada: {p}"), styles["small"]))

        elif it.kind == "plain":
            story.append(_pdf_box_text(str(it.payload or ""), styles))
            story.append(Spacer(1, 8))

        elif it.kind == "blank":
            h = int((it.payload or {}).get("height", 90))
            story.append(_pdf_blank_box(height_pts=h))
            story.append(Spacer(1, 10))

        elif it.kind == "spacer":
            story.append(Spacer(1, 10))

    return story


# =========================================================
# ============ 06b2 — ANALISE RADIAÇÃO (lógica original) ===
# =========================================================
B_STAGE_KEY = "investigacao_analise_radiacao_conforto"
B_CANTOS = ["NO", "NE", "SO", "SE"]


@dataclass
class B_Snapshot:
    ta_id: str
    ts_ids: List[str]
    ta_C: float
    ts_C: List[float]
    deltas_C: List[float]


@dataclass
class B_FluxoItem:
    delta_C: float
    escolha: str
    justificativa: str
    gabarito_esperado: str


@dataclass
class B_ConfortoRadiativo:
    texto: str
    referencia: Dict[str, Any]


@dataclass
class B_Canto:
    nome: str
    snapshot: Optional[B_Snapshot]
    fluxo_ts1: Optional[B_FluxoItem]
    fluxo_ts2: Optional[B_FluxoItem]
    conforto: Optional[B_ConfortoRadiativo]


def _b_get(d: Dict[str, Any], *keys: str, default=None):
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _b_parse_snapshot(raw: Dict[str, Any]) -> Optional[B_Snapshot]:
    if not isinstance(raw, dict):
        return None
    try:
        return B_Snapshot(
            ta_id=str(raw.get("ta_id", "")),
            ts_ids=list(raw.get("ts_ids", [])),
            ta_C=float(raw.get("ta_C")),
            ts_C=list(raw.get("ts_C", [])),
            deltas_C=list(raw.get("deltas_C", [])),
        )
    except Exception:
        return None


def _b_parse_fluxo_item(raw: Dict[str, Any]) -> Optional[B_FluxoItem]:
    if not isinstance(raw, dict):
        return None
    try:
        return B_FluxoItem(
            delta_C=float(raw.get("delta_C")),
            escolha=str(raw.get("escolha", "")),
            justificativa=str(raw.get("justificativa", "")),
            gabarito_esperado=str(raw.get("gabarito_esperado", "")),
        )
    except Exception:
        return None


def _b_parse_conforto(raw: Dict[str, Any]) -> Optional[B_ConfortoRadiativo]:
    if not isinstance(raw, dict):
        return None
    return B_ConfortoRadiativo(
        texto=str(raw.get("texto", "")),
        referencia=raw.get("referencia", {}) if isinstance(raw.get("referencia"), dict) else {},
    )


def _b_extract_canto(stage_obj: Dict[str, Any], canto_nome: str) -> B_Canto:
    raw_canto = _b_get(stage_obj, "respostas", canto_nome, default={})
    if not isinstance(raw_canto, dict):
        raw_canto = {}

    snapshot = _b_parse_snapshot(raw_canto.get("snapshot", {}))
    fluxo = raw_canto.get("fluxo", {}) if isinstance(raw_canto.get("fluxo"), dict) else {}
    fluxo_ts1 = _b_parse_fluxo_item(fluxo.get("ts1", {}))
    fluxo_ts2 = _b_parse_fluxo_item(fluxo.get("ts2", {}))
    conforto = _b_parse_conforto(raw_canto.get("conforto_radiativo", {}))

    return B_Canto(
        nome=canto_nome,
        snapshot=snapshot,
        fluxo_ts1=fluxo_ts1,
        fluxo_ts2=fluxo_ts2,
        conforto=conforto,
    )


def _b_extract_all_cantos(root: Dict[str, Any]) -> Dict[str, B_Canto]:
    stages = root.get("stages", {}) if isinstance(root.get("stages"), dict) else {}
    stage_obj = stages.get(B_STAGE_KEY, {}) if isinstance(stages.get(B_STAGE_KEY), dict) else {}
    return {c: _b_extract_canto(stage_obj, c) for c in B_CANTOS}


def _b_pretty_choice(x: str) -> str:
    m = {"ar_ganhando": "ar ganhando calor", "ar_perdendo": "ar perdendo calor", "nao_sei": "não sei"}
    x = (x or "").strip()
    return m.get(x, x or "—")


def _b_ui_snapshot(c: B_Canto):
    if not c.snapshot:
        st.info("Sem snapshot.")
        return

    s = c.snapshot
    rows = [{"Temperatura (°C)": round(s.ta_C, 1), "ΔT (°C)": "—"}]

    for ts_id, ts_val, delta in zip(s.ts_ids, s.ts_C, s.deltas_C):
        rows.append({"Temperatura (°C)": round(ts_val, 1), "ΔT (°C)": round(float(delta), 1)})

    index = ["Ta"] + s.ts_ids
    df = pd.DataFrame(rows, index=index)
    st.dataframe(df, use_container_width=True)


def _b_ui_fluxo_e_conforto(c: B_Canto):
    ts_ids = (c.snapshot.ts_ids if c.snapshot else []) or []
    pares: List[tuple[str, Optional[B_FluxoItem]]] = []

    if len(ts_ids) >= 1:
        pares.append((ts_ids[0], c.fluxo_ts1))
    if len(ts_ids) >= 2:
        pares.append((ts_ids[1], c.fluxo_ts2))
    if not pares:
        pares = [("ts1", c.fluxo_ts1), ("ts2", c.fluxo_ts2)]

    rows = []
    index = []
    for sensor_id, f in pares:
        escolha = _b_pretty_choice(f.escolha) if f else "—"
        justificativa = (f.justificativa or "").strip() if f else ""
        justificativa = justificativa or "—"
        index.append(sensor_id)
        rows.append(
            {
                "O que acontece com o ar?": escolha,
                "Justificativa (ΔT e leitura física)": justificativa,
            }
        )

    df_fluxo = pd.DataFrame(rows, index=index)
    st.table(df_fluxo)

    texto_conforto = (c.conforto.texto or "").strip() if c.conforto else ""
    st.markdown(
        "**Com base em Ta, Ts e no sinal médio (Ts−Ta), descreva se este canto tende a causar alívio radiativo, "
        "neutralidade ou desconforto radiativo. Explique em 2–5 linhas.**"
    )
    st.write(texto_conforto or "—")


def _b_ui_canto_section(c: B_Canto):
    st.markdown(f"## Canto {c.nome}")
    with st.container(border=True):
        _b_ui_snapshot(c)
        st.markdown("")
        _b_ui_fluxo_e_conforto(c)


def _b_to_render_items(root: Dict[str, Any]) -> List[RenderItem]:
    items: List[RenderItem] = []
    items.append(RenderItem("h1", title="Análise — radiação e conforto"))

    cantos = _b_extract_all_cantos(root)
    for nome in B_CANTOS:
        c = cantos.get(nome)
        if not c:
            continue

        items.append(RenderItem("h2", title=f"Canto {nome}"))

        # Snapshot (table)
        if c.snapshot:
            s = c.snapshot
            headers = ["Ponto", "Temperatura (°C)", "ΔT (°C)"]
            rows = [["Ta", f"{round(float(s.ta_C), 1)}", "—"]]
            for ts_id, ts_val, delta in zip(s.ts_ids, s.ts_C, s.deltas_C):
                rows.append([str(ts_id), f"{round(float(ts_val), 1)}", f"{round(float(delta), 1)}"])
            items.append(RenderItem("table", payload={"headers": headers, "rows": rows}))
        else:
            items.append(RenderItem("plain", payload="Sem snapshot."))

        # Fluxo (table)
        ts_ids = (c.snapshot.ts_ids if c.snapshot else []) or []
        pares: List[tuple[str, Optional[B_FluxoItem]]] = []
        if len(ts_ids) >= 1:
            pares.append((ts_ids[0], c.fluxo_ts1))
        if len(ts_ids) >= 2:
            pares.append((ts_ids[1], c.fluxo_ts2))
        if not pares:
            pares = [("ts1", c.fluxo_ts1), ("ts2", c.fluxo_ts2)]

        headers = ["Sensor", "O que acontece com o ar?", "Justificativa (ΔT e leitura física)"]
        rows: List[List[str]] = []
        for sensor_id, f in pares:
            escolha = _b_pretty_choice(f.escolha) if f else "—"
            justificativa = (f.justificativa or "").strip() if f else ""
            justificativa = justificativa or "—"
            rows.append([str(sensor_id), str(escolha), str(justificativa)])
        items.append(RenderItem("table", payload={"headers": headers, "rows": rows}))

        # Conforto
        items.append(
            RenderItem(
                "h2",
                title=(
                    "Com base em Ta, Ts e no sinal médio (Ts−Ta), descreva se este canto tende a causar alívio radiativo, "
                    "neutralidade ou desconforto radiativo. Explique em 2–5 linhas."
                ),
            )
        )
        texto_conforto = (c.conforto.texto or "").strip() if c.conforto else ""
        items.append(RenderItem("plain", payload=texto_conforto or "—"))

        items.append(RenderItem("spacer"))

    return items


# =========================================================
# ========== 06b1 — GRÁFICO GRADIENTE (lógica original) ====
# =========================================================
C_STAGE_KEY = "investigacao_grafico_gradiente_termico"
C_STAGE_TITLE = "Gráfico de gradiente térmico"

C_HIDDEN_KEYS = {
    "saved_at",
    "last_loaded_at",
    "last_generated_at",
    "horario_ref",
    "meta",
    "params_fixos",
    "syn_01",
}

C_LABEL_OVERRIDES: Dict[str, str] = {
    "figura_png": "Figura",
    "conf_01": "Um único valor de temperatura média descreve o conforto neste ambiente? Por quê?",
    "conf_02": "Como a posição do ocupante em relação às paredes afeta o conforto (radiação + convecção)?",
    "conf_03": "Cite 2 estratégias de projeto para reduzir os gradientes observados (envoltória/isolamento/ventilação/sombreamento).",
    "modes_01": "Condução: como o calor chega à superfície interna das paredes? O que a condução determina (Ts)?",
    "modes_02": "Convecção: como a parede troca calor com o ar próximo? Por que existe gradiente perto da parede (camada limite)?",
    "modes_03": "Radiação: mesmo sem tocar nas paredes, um ocupante sentiria diferença? Explique usando temperatura radiante média.",

    "obs_01": "O que as cores diferentes representam fisicamente neste mapa?",
    "obs_02": "Se a imagem é vista de cima e os quatro lados são paredes, por que a temperatura não é uniforme no interior?",
    "obs_03": "Onde estão os maiores gradientes de temperatura? O que isso sugere sobre o papel das paredes?",

    "pl_01": "Escreva a Primeira Lei e indique qual termo você considera desprezível neste caso (W≈0 ou não). Justifique.",
    "pl_02": "Com W≈0, explique por que o mapa de T pode ser interpretado como consequência de Q (trocas de calor).",

    "reg_01": "Este mapa parece representar regime permanente ou transitório? Qual evidência sustenta sua resposta?",
    "reg_02": "Em regime permanente, o que a Primeira Lei implica para o balanço de energia (Q_entra = Q_sai)?",

    "ut_01": "Em um gás como o ar, o que a temperatura mede (interpretação microscópica)?",
    "ut_02": "Se a temperatura varia no espaço, o que isso indica sobre a distribuição de energia interna?",
}


@dataclass
class C_GradienteTermico:
    figura_png: Optional[str]
    respostas: Dict[str, Any]


def _c_label(key: str) -> str:
    return C_LABEL_OVERRIDES.get(key, key)


def _c_get(d: Dict[str, Any], *keys: str, default=None):
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _c_extract_gradiente(root: Dict[str, Any]) -> Optional[C_GradienteTermico]:
    stages = root.get("stages", {}) if isinstance(root.get("stages"), dict) else {}
    stage_obj = stages.get(C_STAGE_KEY, {}) if isinstance(stages.get(C_STAGE_KEY), dict) else {}
    if not stage_obj:
        return None

    figura = stage_obj.get("figura_png")
    figura = str(figura) if isinstance(figura, str) and figura.strip() else None

    respostas = stage_obj.get("respostas", {})
    if not isinstance(respostas, dict):
        respostas = {}
    respostas = {k: v for k, v in respostas.items() if k not in C_HIDDEN_KEYS}

    return C_GradienteTermico(figura_png=figura, respostas=respostas)


def _c_ui_figura(m: C_GradienteTermico):
    st.markdown("**Figura**")
    if not m.figura_png:
        st.info("Sem figura.")
        return
    p = Path(m.figura_png)
    if p.exists():
        st.image(str(p), use_container_width=True)
    else:
        st.info(f"Imagem não encontrada: {m.figura_png}")


def _c_ui_respostas(m: C_GradienteTermico):
    st.markdown("**Respostas**")
    if not m.respostas:
        st.info("Sem respostas.")
        return

    def sort_key(k: str) -> Tuple[str, int]:
        mm = re.match(r"^([a-zA-Z_]+)0*([0-9]+)$", (k or "").strip())
        if mm:
            return (mm.group(1), int(mm.group(2)))
        return ("zz", 10**9)

    for k in sorted(m.respostas.keys(), key=sort_key):
        prompt = _c_label(k)
        resposta = m.respostas.get(k)
        txt = "" if resposta is None else str(resposta).strip()

        st.markdown(f"**{prompt}**")
        with st.container(border=True):
            safe = (
                txt.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br/>")
            )
            st.markdown(
                f"""
                <div style="
                    padding-top: 6px;
                    padding-bottom: 10px;
                    padding-left: 12px;
                    padding-right: 12px;
                    line-height: 1.45;
                    font-size: 0.95rem;
                    color: rgba(200, 220, 255, 0.75);
                    ">
                    {safe if safe else "&nbsp;"}
                </div>
                """,
                unsafe_allow_html=True,
            )


def _c_ui_stage(m: C_GradienteTermico):
    st.markdown(f"## {C_STAGE_TITLE}")
    with st.container(border=True):
        _c_ui_figura(m)
        st.markdown("")
        _c_ui_respostas(m)


def _c_to_render_items(root: Dict[str, Any]) -> List[RenderItem]:
    items: List[RenderItem] = []
    items.append(RenderItem("h1", title=C_STAGE_TITLE))

    m = _c_extract_gradiente(root)
    if not m:
        items.append(RenderItem("plain", payload=f"Stage não encontrado no JSON: {C_STAGE_KEY}"))
        items.append(RenderItem("spacer"))
        return items

    items.append(RenderItem("h2", title="Figura"))
    if m.figura_png:
        items.append(RenderItem("image", payload=m.figura_png))
    else:
        items.append(RenderItem("plain", payload="—"))

    items.append(RenderItem("h2", title="Respostas"))

    def sort_key(k: str) -> Tuple[str, int]:
        mm = re.match(r"^([a-zA-Z_]+)0*([0-9]+)$", (k or "").strip())
        if mm:
            return (mm.group(1), int(mm.group(2)))
        return ("zz", 10**9)

    for k in sorted(m.respostas.keys(), key=sort_key):
        items.append(RenderItem("h2", title=_c_label(k)))
        items.append(RenderItem("plain", payload=str(m.respostas.get(k) or "").strip() or "—"))

    items.append(RenderItem("spacer"))
    return items


# =========================================================
# MAIN (ÚNICO)
# =========================================================
def render(ctx: Dict) -> None:
    aluno_ctx = (ctx.get("aluno") or "").strip()
    grupo_id_ctx = (ctx.get("grupo_id") or "").strip()
    grupo_nome_ctx = (ctx.get("grupo_nome") or "").strip()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = _investigacao_path(aluno_ctx or "Aluno")
    root = load_json(json_path) or {}
    if not isinstance(root, dict):
        st.error("Não foi possível ler o JSON de investigação.")
        st.caption(f"Esperado: {json_path}")
        return

    # botão de atualização (mantém comportamento dos seus blocos)
    if st.button("Atualizar os dados", key=f"{STAGE_ID}__reload"):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        try:
            st.cache_resource.clear()
        except Exception:
            pass
        st.rerun()

    aluno = (aluno_ctx or root.get("aluno") or "Aluno").strip()
    grupo_id = grupo_id_ctx or (root.get("grupo_id") or "")
    grupo_nome = grupo_nome_ctx or (root.get("grupo_nome") or "")
    grupo = f"{grupo_id} {('- ' + grupo_nome) if grupo_nome else ''}".strip() or "—"

    # PDF único
    pdf_path = OUT_DIR / f"{_safe_filename(aluno)}_{PDF_SUFFIX}"
    locked = pdf_path.exists()

    st.caption(
        f"Aluno: {aluno}"
        + (
            f" — Grupo {grupo_id} ({grupo_nome})"
            if grupo_id and grupo_nome
            else (f" — Grupo {grupo_id}" if grupo_id else "")
        )
    )

    if locked:
        st.success(
            "Entregável bloqueado porque o PDF desta parte já existe. Se o professor apagar o PDF, esta tela destrava automaticamente."
        )

    stages = root.get("stages", {}) if isinstance(root.get("stages"), dict) else {}
    if not stages:
        st.info("JSON não possui stages para exibir.")
        return

    # =========================================================
    # 1) RESTANTE (06a) — na ordem do 06a
    # =========================================================
    render_plan: List[RenderItem] = []
    for sid in A_STAGE_ORDER:
        if sid in stages:
            render_plan.extend(_collect_story_from_stage(sid, stages.get(sid)))

    _render_items_to_ui(render_plan, aluno)

    # =========================================================
    # 2) ANALISE RADIAÇÃO (06b2)
    # =========================================================
    st.markdown("---")
    st.markdown("### Análise — radiação e conforto")
    cantos = _b_extract_all_cantos(root)
    for nome in B_CANTOS:
        _b_ui_canto_section(cantos[nome])

    # =========================================================
    # 3) GRÁFICO GRADIENTE (06b1)
    # =========================================================
    st.markdown("---")
    m = _c_extract_gradiente(root)
    if not m:
        st.info(f"Stage não encontrado no JSON: {C_STAGE_KEY}")
    else:
        _c_ui_stage(m)

    # =========================================================
    # GERAR PDF ÚNICO (na mesma ordem acima)
    # =========================================================
    if st.button(
        "Gerar PDF",
        disabled=locked,
        key=f"{STAGE_ID}__{_safe_filename(aluno)}__submit",
    ):
        header = {
            "aluno": aluno,
            "grupo": grupo,
        }

        styles = _make_pdf_styles()

        # story = 06a + 06b2 + 06b1 (na ordem dos códigos)
        pdf_items: List[RenderItem] = []
        pdf_items.extend(render_plan)
        pdf_items.extend(_b_to_render_items(root))
        pdf_items.extend(_c_to_render_items(root))

        pdf_story = _render_items_to_pdf_story(pdf_items, styles)
        pdf_bytes = _build_pdf_bytes(header=header, story=pdf_story)

        pdf_path.write_bytes(pdf_bytes)

        try:
            draft_path = stage_path(ctx, STAGE_ID)
            export_payload = {
                "stage_id": STAGE_ID,
                "generated_at": _now_iso(),
                "pdf_path": str(pdf_path),
                "source_json": str(json_path),
                "aluno": aluno,
                "grupo_id": grupo_id,
                "grupo_nome": grupo_nome,
                "rendered_stage_ids": list(A_STAGE_ORDER) + [B_STAGE_KEY, C_STAGE_KEY],
            }
            save_json(draft_path, export_payload)
        except Exception:
            pass

        st.success("PDF gerado. Esta parte agora está bloqueada pelo PDF.")
        # st.caption(f"PDF salvo em: {pdf_path}")
        # st.download_button(
        #     "Baixar PDF",
        #     data=pdf_bytes,
        #     file_name=pdf_path.name,
        #     mime="application/pdf",
        # )
        # st.rerun()
