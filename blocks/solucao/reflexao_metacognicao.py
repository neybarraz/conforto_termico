# blocks/solucao/reflexao_metacognicao.py
# =============================================================================
# 1) REFLEXÃO E METACOGNIÇÃO — SOLUÇÃO
# =============================================================================
# Persistência:
# - JSON do bloco: data/solucao/reflexao_<nome_do_aluno>.json
#
# Incremento:
# - PDF do bloco:  data/pdf/reflexao_<nome_do_aluno>.pdf
# =============================================================================

from __future__ import annotations

from typing import Dict, Any, List
from pathlib import Path
import re

import streamlit as st

from storage.io_csv import load_json, save_json


STAGE_ID = "solucao_reflexao_metacognicao"


# =============================================================================
# PDF (ReportLab) — padrão igual ao memorial_tecnico.py
# =============================================================================
try:
    from io import BytesIO

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    REPORTLAB_OK = True
    REPORTLAB_ERR = None
except Exception as err:
    REPORTLAB_OK = False
    REPORTLAB_ERR = err


# ------------------------------- Utilidades ---------------------------------

def _ctx_get_state(ctx: Dict) -> Dict[str, Any]:
    if isinstance(ctx, dict) and isinstance(ctx.get("state"), dict):
        return ctx["state"]
    key = "__pbl_state__solucao_reflexao_metacognicao"
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


def _as_list_of_str(x: Any) -> List[str]:
    if isinstance(x, list):
        return [str(i) for i in x if str(i).strip()]
    return []


def _sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "anon"
    s = s.lower()
    s = s.replace(" ", "_")
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


def _reflexao_path(ctx: Dict) -> Path:
    aluno = _sanitize_filename(_get_aluno_name(ctx))
    p = Path("data") / "solucao" / f"reflexao_{aluno}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# =============================================================================
# PDF helpers
# =============================================================================

def _pdf_path(ctx: Dict) -> Path:
    aluno = _sanitize_filename(_get_aluno_name(ctx))
    p = Path("data") / "pdf" / f"{aluno}_03_reflexao.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _nl_to_br(s: str) -> str:
    return (s or "").replace("\n", "<br/>").strip()


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
        header = str(sec.get("h", "")).strip()
        if header:
            story.append(Paragraph(header, h2))

        txt = sec.get("body", "")
        story.append(
            Paragraph(_nl_to_br(txt) if _nonempty(txt) else "(não preenchido)", body_compact)
        )
        story.append(Spacer(1, 8))

        tbl = sec.get("table")
        if isinstance(tbl, list) and tbl:
            t = Table(tbl, repeatRows=1, splitByRow=1)
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

    doc.build(story)
    return buf.getvalue()


# ------------------------------- Payload ------------------------------------

def _build_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        # 1) percurso
        "percurso_hipoteses": _get(state, "percurso_hipoteses", ""),
        "percurso_resultados": _get(state, "percurso_resultados", ""),
        "percurso_decisoes_sel": _as_list_of_str(_get(state, "percurso_decisoes_sel", [])),
        "percurso_decisoes_outra": _get(state, "percurso_decisoes_outra", ""),

        # 2) conceitos
        "conceitos_sel": _as_list_of_str(_get(state, "conceitos_sel", [])),
        "conceitos_justificativa": _get(state, "conceitos_justificativa", ""),

        # 3) evidências
        "evidencia_principal": _get(state, "evidencia_principal", ""),
        "equilibrio_resposta": _get(state, "equilibrio_resposta", ""),
        "equilibrio_evidencia": _get(state, "equilibrio_evidencia", ""),
        "mecanismo_dominante": _get(state, "mecanismo_dominante", ""),
        "mecanismo_justificativa": _get(state, "mecanismo_justificativa", ""),

        # 4) limites
        "lim_simplificacoes": _get(state, "lim_simplificacoes", ""),
        "lim_incertezas": _get(state, "lim_incertezas", ""),
        "lim_variaveis_nao_controladas": _get(state, "lim_variaveis_nao_controladas", ""),

        # 5) autoavaliação
        "auto_temp_vs_calor": int(_get(state, "auto_temp_vs_calor", 3) or 3),
        "auto_equilibrio": int(_get(state, "auto_equilibrio", 3) or 3),
        "auto_mecanismos": int(_get(state, "auto_mecanismos", 3) or 3),
        "auto_primeira_lei": int(_get(state, "auto_primeira_lei", 3) or 3),
        "auto_leitura_graficos": int(_get(state, "auto_leitura_graficos", 3) or 3),

        # status
        "concluido": bool(_get(state, "concluido", False)),
    }


def _compute_faltas(state: Dict[str, Any], mecanismo_opcoes: List[str]) -> List[str]:
    faltas: List[str] = []

    if not _nonempty(_get(state, "percurso_hipoteses", "")):
        faltas.append("- Preencha: hipóteses iniciais (1.1).")
    if not _nonempty(_get(state, "percurso_resultados", "")):
        faltas.append("- Preencha: resultados obtidos (1.2).")

    decisoes_sel_now = _as_list_of_str(_get(state, "percurso_decisoes_sel", []))
    if len(decisoes_sel_now) == 0:
        faltas.append("- Selecione: decisões metodológicas (1.3).")
    if "Outra (descrever abaixo)." in decisoes_sel_now and not _nonempty(_get(state, "percurso_decisoes_outra", "")):
        faltas.append("- Preencha: decisão 'Outra' (1.3).")

    conceitos_sel_now = _as_list_of_str(_get(state, "conceitos_sel", []))
    if len(conceitos_sel_now) == 0:
        faltas.append("- Marque ao menos 1 conceito mobilizado (2.1).")
    if not _nonempty(_get(state, "conceitos_justificativa", "")):
        faltas.append("- Preencha: justificativa dos conceitos (2.2).")

    if not _nonempty(_get(state, "evidencia_principal", "")):
        faltas.append("- Preencha: evidência principal (3.1).")
    if _get(state, "equilibrio_resposta", "") not in ["Sim", "Não", "Parcialmente"]:
        faltas.append("- Selecione: aproximação de equilíbrio térmico (3.2).")
    else:
        if not _nonempty(_get(state, "equilibrio_evidencia", "")):
            faltas.append("- Preencha: evidência do equilíbrio (3.2).")

    if _get(state, "mecanismo_dominante", "") not in mecanismo_opcoes:
        faltas.append("- Selecione: mecanismo dominante (3.3).")
    if not _nonempty(_get(state, "mecanismo_justificativa", "")):
        faltas.append("- Preencha: justificativa do mecanismo dominante (3.3).")

    if not _nonempty(_get(state, "lim_simplificacoes", "")):
        faltas.append("- Preencha: simplificações adotadas (4.1).")
    if not _nonempty(_get(state, "lim_incertezas", "")):
        faltas.append("- Preencha: incertezas experimentais (4.2).")
    if not _nonempty(_get(state, "lim_variaveis_nao_controladas", "")):
        faltas.append("- Preencha: variáveis não controladas (4.3).")

    return faltas


def _save_all(path_json: Path, state: Dict[str, Any], mecanismo_opcoes: List[str]) -> None:
    faltas = _compute_faltas(state, mecanismo_opcoes)
    concluido = len(faltas) == 0
    _set(state, "concluido", bool(concluido))

    payload = _build_payload(state)
    payload["concluido"] = bool(concluido)

    save_json(path_json, payload)

    if concluido:
        st.success("Salvo e marcado como concluído.")
    else:
        st.success("Salvo. Ainda há pendências para concluir.")


def _render_save_button(path_json: Path, state: Dict[str, Any], mecanismo_opcoes: List[str], key_suffix: str) -> None:
    if st.button("Salvar", key=f"{STAGE_ID}_salvar_{key_suffix}"):
        _save_all(path_json, state, mecanismo_opcoes)


# --------------------------------- Render -----------------------------------

def render(ctx: Dict) -> None:
    path_json = _reflexao_path(ctx)
    state = _ctx_get_state(ctx)

    if not _get(state, "__loaded__", False):
        saved = load_json(path_json) or {}
        _hydrate_state_from_saved(state, saved)
        _set(state, "__loaded__", True)

    st.title("Reflexão e Metacognição")
    st.caption(
        "Consolide o raciocínio físico após a investigação: explicite decisões, evidências, limites "
        "e faça uma autoavaliação conceitual coerente com o percurso."
    )
    st.markdown("---")

    mecanismo_opcoes = [
        "Condução",
        "Convecção natural",
        "Convecção forçada",
        "Radiação térmica",
        "Combinação de mecanismos",
    ]

    # =========================================================================
    # PARTE 1/5
    # =========================================================================
    st.markdown("## 1) Percurso da investigação")

    st.info(
        "Antes de responder, relembre o que vocês fizeram na investigação:\n"
        "- Definiram grandezas e um método de coleta (procedimentos/mecanismos).\n"
        "- Realizaram medições em 7 pontos do ambiente, em 3 horários.\n"
        "- Registraram condições do ambiente e observações qualitativas "
        "(insolação, pessoas, portas/janelas, ventilação).\n"
        "- Organizaram os dados (estatísticas e comparação por ponto) ANTES de interpretar.\n"
        "- Fizeram a análise física: identificaram padrões, justificaram mecanismo(s) "
        "e conectaram com conceitos (equilíbrio, 1ª Lei etc.).\n\n"
        "Use apenas o que vocês mediram, organizaram e analisaram como evidência. "
        "Evite responder com base no que \"deveria\" acontecer."
    )

    st.markdown("1.1 Hipóteses iniciais formuladas (antes das medições)")
    hipoteses = st.text_area(
        " ",
        value=_get(state, "percurso_hipoteses", ""),
        height=110,
        key=f"{STAGE_ID}_percurso_hipoteses",
        placeholder="Antes de medir, suspeitávamos que a região próxima à janela teria Ts maior "
                    "devido à insolação direta; também esperávamos gradiente de Ta entre janela e centro.",
        help="Escreva o que vocês acreditavam que iria acontecer ANTES de coletar os dados. "
             "Máximo de 2–3 frases. Não explique ainda os mecanismos.",
        label_visibility="collapsed",
    )
    _set(state, "percurso_hipoteses", hipoteses)

    st.markdown("1.2 Resultados efetivamente obtidos (após as medições)")
    resultados = st.text_area(
        "  ",
        value=_get(state, "percurso_resultados", ""),
        height=110,
        key=f"{STAGE_ID}_percurso_resultados",
        placeholder="Após as medições, observamos Ts maior próximo à janela em horários com sol; "
                    "Ta variou pouco entre os pontos; UR permaneceu aproximadamente constante; "
                    "corrente de ar foi percebida quando a porta abriu.",
        help="Descreva apenas o que os dados e observações mostraram. "
             "Não explique o porquê ainda. Use comparações simples entre pontos ou horários.",
        label_visibility="collapsed",
    )
    _set(state, "percurso_resultados", resultados)

    decisoes_opcoes = [
        "Planejamos comparar pontos (janela vs. centro vs. fundo).",
        "Escolhemos horários distintos para observar variação temporal.",
        "Mudamos ponto/posição do sensor para reduzir viés de leitura.",
        "Repetimos medições para checar consistência.",
        "Registramos condições (pessoas/janelas/insolação) para interpretar dados.",
        "Reformulamos hipótese após dados iniciais.",
        "Outra (descrever abaixo).",
    ]

    st.markdown("1.3 Decisões metodológicas tomadas durante a investigação")
    st.caption(
        "Marque apenas decisões que vocês REALMENTE tomaram durante a investigação. "
        "Não marque itens apenas porque estavam no roteiro."
    )

    _defaults = set(_as_list_of_str(_get(state, "percurso_decisoes_sel", [])))
    _sel: List[str] = []
    for i, opt in enumerate(decisoes_opcoes):
        checked = st.checkbox(
            opt,
            value=(opt in _defaults),
            key=f"{STAGE_ID}_percurso_decisao_{i}",
        )
        if checked:
            _sel.append(opt)

    decisoes_sel = _sel
    _set(state, "percurso_decisoes_sel", decisoes_sel)

    if "Outra (descrever abaixo)." in decisoes_sel:
        st.markdown("1.3.1 Descreva a decisão 'Outra'")
        decisoes_outra = st.text_input(
            "   ",
            value=_get(state, "percurso_decisoes_outra", ""),
            key=f"{STAGE_ID}_percurso_decisoes_outra",
            placeholder="Ex.: Reposicionamos o sensor mais afastado da parede para reduzir "
                        "influência direta da temperatura da superfície.",
            label_visibility="collapsed",
        )
        _set(state, "percurso_decisoes_outra", decisoes_outra)
    else:
        _set(state, "percurso_decisoes_outra", "")

    _render_save_button(path_json, state, mecanismo_opcoes, "p1")
    st.markdown("---")

    # =========================================================================
    # PARTE 2/5
    # =========================================================================
    st.markdown("## 2) Conceitos físicos mobilizados")

    st.info(
        "Nesta etapa, selecione apenas os conceitos que vocês REALMENTE mobilizaram para interpretar os dados.\n"
        "Dica: conceito mobilizado é aquele que aparece na justificativa do mecanismo, na discussão da análise física "
        "ou na explicação de um padrão observado (não apenas um conceito \"que existe no conteúdo\")."
    )

    conceitos_opcoes = [
        "Equilíbrio térmico",
        "Condução",
        "Convecção natural",
        "Convecção forçada",
        "Radiação térmica",
        "Papel do ar como fluido térmico",
        "Interpretação energética do sistema (Primeira Lei)",
    ]

    st.markdown("2.1 Conceitos físicos utilizados na interpretação")
    st.caption("Marque de 1 a 3 conceitos principais.")

    _defaults = set(_as_list_of_str(_get(state, "conceitos_sel", [])))
    _sel2: List[str] = []
    for i, opt in enumerate(conceitos_opcoes):
        checked = st.checkbox(
            opt,
            value=(opt in _defaults),
            key=f"{STAGE_ID}_conceito_{i}",
        )
        if checked:
            _sel2.append(opt)

    _set(state, "conceitos_sel", _sel2)

    st.markdown("2.2 Justificativa (como cada conceito ajudou a interpretar os dados?)")
    conceitos_just = st.text_area(
        "    ",
        value=_get(state, "conceitos_justificativa", ""),
        height=150,
        key=f"{STAGE_ID}_conceitos_justificativa",
        placeholder="Modelo (copie e adapte):\n"
                    "- [Conceito]: usamos para explicar [padrão observado]. "
                    "Evidência: [comparação por ponto/horário ou observação registrada].\n\n"
                    "Ex.: Radiação térmica: Ts foi maior perto da janela nos horários com sol. "
                    "Evidência: Ts janela > Ts centro.\n"
                    "Convecção forçada: sensação mudou rapidamente quando a porta abriu. "
                    "Evidência: corrente de ar + mudança percebida.",
        help="Para cada conceito marcado acima, explique em 1–2 frases e cite a evidência.",
        label_visibility="collapsed",
    )
    _set(state, "conceitos_justificativa", conceitos_just)

    _render_save_button(path_json, state, mecanismo_opcoes, "p2")
    st.markdown("---")

    # =========================================================================
    # PARTE 3/5
    # =========================================================================
    st.markdown("## 3) Evidências que sustentam a interpretação")

    st.info(
        "Aqui você deve sustentar sua interpretação com EVIDÊNCIAS.\n"
        "Regra prática: toda conclusão precisa de um dado/observação que a apoie."
    )

    st.markdown("3.1 Qual dado/observação sustenta sua conclusão principal?")
    evidencia_principal = st.text_area(
        "     ",
        value=_get(state, "evidencia_principal", ""),
        height=150,
        key=f"{STAGE_ID}_evidencia_principal",
        placeholder="Modelo:\n"
                    "- Conclusão: [o que vocês afirmam].\n"
                    "- Evidência: [qual dado/observação mostra isso].",
        label_visibility="collapsed",
    )
    _set(state, "evidencia_principal", evidencia_principal)

    st.markdown("3.2 Aproximação de equilíbrio térmico")
    st.caption("Escolha apenas UMA opção. Use 'Parcialmente' se depender do ponto/horário.")
    equilibrio_opcoes = ["Sim", "Não", "Parcialmente"]
    _eq_saved = _get(state, "equilibrio_resposta", "")
    equilibrio_resp = st.radio(
        "      ",
        options=equilibrio_opcoes,
        index=equilibrio_opcoes.index(_eq_saved) if _eq_saved in equilibrio_opcoes else 0,
        key=f"{STAGE_ID}_equilibrio_resposta",
        horizontal=True,
        label_visibility="collapsed",
    )
    _set(state, "equilibrio_resposta", equilibrio_resp)

    st.markdown("3.2.1 Evidência do equilíbrio")
    equilibrio_evid = st.text_area(
        "       ",
        value=_get(state, "equilibrio_evidencia", ""),
        height=150,
        key=f"{STAGE_ID}_equilibrio_evidencia",
        placeholder="Onde/Quando + evidência (Ta/Ts estáveis, próximos ou variáveis).",
        label_visibility="collapsed",
    )
    _set(state, "equilibrio_evidencia", equilibrio_evid)

    st.markdown("3.3 Mecanismo dominante")
    mecanismo_dom = st.radio(
        "        ",
        options=mecanismo_opcoes,
        index=mecanismo_opcoes.index(_get(state, "mecanismo_dominante", mecanismo_opcoes[0]))
        if _get(state, "mecanismo_dominante", "") in mecanismo_opcoes else 0,
        key=f"{STAGE_ID}_mecanismo_dominante",
        horizontal=True,
        label_visibility="collapsed",
    )
    _set(state, "mecanismo_dominante", mecanismo_dom)

    st.markdown("3.3.1 Justificativa curta do mecanismo")
    mecanismo_just = st.text_area(
        "         ",
        value=_get(state, "mecanismo_justificativa", ""),
        height=150,
        key=f"{STAGE_ID}_mecanismo_justificativa",
        placeholder="Padrão observado + mecanismo + evidência.",
        label_visibility="collapsed",
    )
    _set(state, "mecanismo_justificativa", mecanismo_just)

    _render_save_button(path_json, state, mecanismo_opcoes, "p3")
    st.markdown("---")

    # =========================================================================
    # PARTE 4/5
    # =========================================================================
    st.markdown("## 4) Limites da investigação")

    st.info(
        "Nesta etapa, reconheça os LIMITES do seu estudo. "
        "Isso mostra maturidade científica."
    )

    st.markdown("4.1 Simplificações adotadas")
    lim_simpl = st.text_area(
        "          ",
        value=_get(state, "lim_simplificacoes", ""),
        height=150,
        key=f"{STAGE_ID}_lim_simplificacoes",
        placeholder="O que simplificamos + consequência.",
        label_visibility="collapsed",
    )
    _set(state, "lim_simplificacoes", lim_simpl)

    st.markdown("4.2 Incertezas experimentais")
    lim_incert = st.text_area(
        "           ",
        value=_get(state, "lim_incertezas", ""),
        height=150,
        key=f"{STAGE_ID}_lim_incertezas",
        placeholder="Fonte da incerteza + possível efeito.",
        label_visibility="collapsed",
    )
    _set(state, "lim_incertezas", lim_incert)

    st.markdown("4.3 Variáveis não controladas")
    lim_var = st.text_area(
        "            ",
        value=_get(state, "lim_variaveis_nao_controladas", ""),
        height=150,
        key=f"{STAGE_ID}_lim_variaveis_nao_controladas",
        placeholder="Variável + impacto possível.",
        label_visibility="collapsed",
    )
    _set(state, "lim_variaveis_nao_controladas", lim_var)

    _render_save_button(path_json, state, mecanismo_opcoes, "p4")
    st.markdown("---")

    # =========================================================================
    # PARTE 5/5
    # =========================================================================
    st.markdown("## 5) Autoavaliação conceitual")

    st.info(
        "Esta autoavaliação é para você refletir sobre o que realmente compreendeu ao longo do PBL.\n"
        "Use a escala com honestidade:\n"
        "- 1 = não domino / não consigo explicar;\n"
        "- 3 = domino parcialmente / explico com ajuda;\n"
        "- 5 = domino com segurança / consigo explicar com exemplos do seu próprio estudo."
    )

    st.markdown("5.1 Diferença entre temperatura e calor (aplicada ao seu caso)")
    a_temp_calor = st.slider(
        "             ",
        min_value=1, max_value=5,
        value=int(_get(state, "auto_temp_vs_calor", 3) or 3),
        key=f"{STAGE_ID}_auto_temp_vs_calor",
        help="Explique com exemplos do seu estudo (Ta, Ts, sensação térmica).",
        label_visibility="collapsed",
    )
    _set(state, "auto_temp_vs_calor", int(a_temp_calor))

    st.markdown("5.2 Equilíbrio térmico no ambiente analisado")
    a_equil = st.slider(
        "              ",
        min_value=1, max_value=5,
        value=int(_get(state, "auto_equilibrio", 3) or 3),
        key=f"{STAGE_ID}_auto_equilibrio",
        help="Você consegue identificar onde há (ou não) equilíbrio com base nos dados?",
        label_visibility="collapsed",
    )
    _set(state, "auto_equilibrio", int(a_equil))

    st.markdown("5.3 Mecanismos de transferência de calor (condução, convecção, radiação)")
    a_mec = st.slider(
        "               ",
        min_value=1, max_value=5,
        value=int(_get(state, "auto_mecanismos", 3) or 3),
        key=f"{STAGE_ID}_auto_mecanismos",
        help="Você consegue justificar o mecanismo dominante usando evidências?",
        label_visibility="collapsed",
    )
    _set(state, "auto_mecanismos", int(a_mec))

    st.markdown("5.4 Primeira Lei da Termodinâmica aplicada ao ambiente")
    a_primeira = st.slider(
        "                ",
        min_value=1, max_value=5,
        value=int(_get(state, "auto_primeira_lei", 3) or 3),
        key=f"{STAGE_ID}_auto_primeira_lei",
        help="Você consegue descrever entradas/saídas de energia no ambiente analisado?",
        label_visibility="collapsed",
    )
    _set(state, "auto_primeira_lei", int(a_primeira))

    st.markdown("5.5 Leitura e interpretação física de gráficos e dados")
    a_graficos = st.slider(
        "                 ",
        min_value=1, max_value=5,
        value=int(_get(state, "auto_leitura_graficos", 3) or 3),
        key=f"{STAGE_ID}_auto_leitura_graficos",
        help="Você consegue explicar padrões sem apenas repetir números?",
        label_visibility="collapsed",
    )
    _set(state, "auto_leitura_graficos", int(a_graficos))

    _render_save_button(path_json, state, mecanismo_opcoes, "p5")

    # =========================================================================
    # Critério de conclusão (diagnóstico)
    # =========================================================================
    faltas = _compute_faltas(state, mecanismo_opcoes)
    concluido = len(faltas) == 0
    _set(state, "concluido", bool(concluido))

    if concluido:
        st.success("Etapa pronta: reflexão coerente, evidências explícitas e limites reconhecidos.")
    else:
        st.warning("Etapa ainda incompleta. Itens faltantes:")
        st.markdown("\n".join(faltas))

    # =========================================================================
    # Exportação (PDF)
    # =========================================================================
    st.markdown("---")
    st.markdown("## Exportação")

    aluno_nome = _get_aluno_name(ctx)
    aluno_slug = _sanitize_filename(aluno_nome)
    titulo_pdf = f"Reflexão e Metacognição — {aluno_nome}".strip()

    decisoes_sel_now = _as_list_of_str(_get(state, "percurso_decisoes_sel", []))
    conceitos_sel_now = _as_list_of_str(_get(state, "conceitos_sel", []))

    auto_table = [
        ["Item", "Autoavaliação (1–5)"],
        ["Temperatura vs calor", str(int(_get(state, "auto_temp_vs_calor", 3) or 3))],
        ["Equilíbrio térmico", str(int(_get(state, "auto_equilibrio", 3) or 3))],
        ["Mecanismos", str(int(_get(state, "auto_mecanismos", 3) or 3))],
        ["Primeira Lei", str(int(_get(state, "auto_primeira_lei", 3) or 3))],
        ["Leitura de gráficos", str(int(_get(state, "auto_leitura_graficos", 3) or 3))],
    ]

    sections = [
        {
            "h": "1) Percurso da investigação",
            "body": "\n\n".join(
                [
                    "Hipóteses iniciais:\n" + _get(state, "percurso_hipoteses", ""),
                    "Resultados obtidos:\n" + _get(state, "percurso_resultados", ""),
                    ("Decisões metodológicas:\n- " + "\n- ".join(decisoes_sel_now)) if decisoes_sel_now else "Decisões metodológicas:\n(não preenchido)",
                    ("Outra decisão:\n" + _get(state, "percurso_decisoes_outra", "")).strip(),
                ]
            ).strip(),
        },
        {
            "h": "2) Conceitos físicos mobilizados",
            "body": "\n\n".join(
                [
                    ("Conceitos:\n- " + "\n- ".join(conceitos_sel_now)) if conceitos_sel_now else "Conceitos:\n(não preenchido)",
                    "Justificativa:\n" + _get(state, "conceitos_justificativa", ""),
                ]
            ).strip(),
        },
        {
            "h": "3) Evidências",
            "body": "\n\n".join(
                [
                    "Evidência principal:\n" + _get(state, "evidencia_principal", ""),
                    "Equilíbrio térmico:\n" + _get(state, "equilibrio_resposta", ""),
                    "Evidência do equilíbrio:\n" + _get(state, "equilibrio_evidencia", ""),
                    "Mecanismo dominante:\n" + _get(state, "mecanismo_dominante", ""),
                    "Justificativa do mecanismo:\n" + _get(state, "mecanismo_justificativa", ""),
                ]
            ).strip(),
        },
        {
            "h": "4) Limites da investigação",
            "body": "\n\n".join(
                [
                    "Simplificações:\n" + _get(state, "lim_simplificacoes", ""),
                    "Incertezas:\n" + _get(state, "lim_incertezas", ""),
                    "Variáveis não controladas:\n" + _get(state, "lim_variaveis_nao_controladas", ""),
                ]
            ).strip(),
        },
        {
            "h": "5) Autoavaliação conceitual",
            "body": "Tabela de autoavaliação (escala 1–5).",
            "table": auto_table,
        },
    ]

    if REPORTLAB_OK:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Gerar PDF", key=f"{STAGE_ID}_gerar_pdf"):
                # opcional: salvar JSON antes de gerar
                # _save_all(path_json, state, mecanismo_opcoes)

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
                    file_name=f"reflexao_{aluno_slug}.pdf",
                    mime="application/pdf",
                    key=f"{STAGE_ID}_download_pdf",
                )
            else:
                st.caption("Gere o PDF para liberar o download.")
    else:
        st.warning("PDF indisponível (reportlab não instalado).")
        st.code(f"Erro de importação: {REPORTLAB_ERR}")
