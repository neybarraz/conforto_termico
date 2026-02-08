# blocks/solucao/sintese_solucao.py
# =============================================================================
# 4) SÍNTESE DA FASE SOLUÇÃO (CHECKPOINT FINAL) — SOLUÇÃO
#
# Objetivo: consolidar a compreensão física e validar que a fase SOLUÇÃO está pronta
# para a AVALIAÇÃO individual.
#
# Dependências (leitura de outros blocos via JSON):
# - SOLUÇÃO: solucao_reflexao_metacognicao  (concluido)
# - SOLUÇÃO: solucao_memorial_tecnico       (concluido)
# - SOLUÇÃO: solucao_seminario              (concluido)
# - (Opcional) PROBLEMA: problema_pergunta_norteadora (para mostrar referência)
#
# Persistência:
# - JSON do bloco: stage_path(ctx, STAGE_ID)
# =============================================================================

from __future__ import annotations

from typing import Dict, Any, List

import streamlit as st

from storage.paths import stage_path
from storage.io_csv import load_json, save_json


STAGE_ID = "solucao_sintese"


# ------------------------------- Utilidades ---------------------------------

def _ctx_get_state(ctx: Dict) -> Dict[str, Any]:
    if isinstance(ctx, dict) and isinstance(ctx.get("state"), dict):
        return ctx["state"]
    key = "__pbl_state__solucao_sintese"
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


def _count_lines(text: str) -> int:
    if not isinstance(text, str):
        return 0
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return len(lines)


# --------------------------------- Render -----------------------------------

def render(ctx: Dict) -> None:
    path_json = stage_path(ctx, STAGE_ID)
    state = _ctx_get_state(ctx)

    # Carrega 1x
    if not _get(state, "__loaded__", False):
        saved = load_json(path_json) or {}
        _hydrate_state_from_saved(state, saved)
        _set(state, "__loaded__", True)

    st.title("Síntese da fase SOLUÇÃO")
    st.caption(
        "Checkpoint final: consolide a compreensão física (em poucas linhas) e valide que "
        "reflexão, memorial e seminário estão concluídos. Ao final, declare prontidão para a avaliação individual."
    )
    st.markdown("---")

    # =========================================================================
    # Importações (status + referências)
    # =========================================================================
    reflex = _safe_stage_data(ctx, "solucao_reflexao_metacognicao")
    memorial = _safe_stage_data(ctx, "solucao_memorial_tecnico")
    seminario = _safe_stage_data(ctx, "solucao_seminario")

    # (Opcional) pergunta norteadora
    prob_perg = _safe_stage_data(ctx, "problema_pergunta_norteadora")
    pergunta = (
        prob_perg.get("pergunta_norteadora")
        or prob_perg.get("texto")
        or prob_perg.get("pergunta")
        or ""
    )

    reflex_ok = bool(reflex.get("concluido", False))
    memorial_ok = bool(memorial.get("concluido", False))
    semin_ok = bool(seminario.get("concluido", False))

    # Referências úteis (para ajudar a síntese sem reescrever tudo)
    mecanismo_dom = memorial.get("ra_mecanismo_dom", "") or reflex.get("mecanismo_dominante", "")
    conc_resposta = memorial.get("conc_resposta", "") or ""
    lim_texto = memorial.get("lim_texto", "")
    if not _nonempty(lim_texto):
        lim_texto = "\n".join([
            f"- Simplificações: {reflex.get('lim_simplificacoes','')}".strip(),
            f"- Incertezas: {reflex.get('lim_incertezas','')}".strip(),
            f"- Variáveis não controladas: {reflex.get('lim_variaveis_nao_controladas','')}".strip(),
        ]).strip()

    # =========================================================================
    # 1) Compreensão do fenômeno (texto curto obrigatório, 6–10 linhas)
    # =========================================================================
    st.markdown("## 1) Compreensão do fenômeno (texto curto obrigatório, 6–10 linhas)")

    if _nonempty(pergunta):
        st.markdown("**Pergunta norteadora (referência):**")
        st.write(pergunta)

    st.info(
        "Escreva em linhas curtas. Cada linha deve cumprir uma função (observação, explicação, conclusão, limite). "
        "Meta: 6 a 10 linhas."
    )

    template_sug = []
    template_sug.append("Observamos: (mensurável) ...")
    template_sug.append("O padrão mais relevante foi: ...")
    template_sug.append("Explicamos fisicamente por: (mecanismo + energia) ...")
    template_sug.append("Mecanismo dominante sugerido: ...")
    template_sug.append("Concluímos: (resposta à pergunta) ...")
    template_sug.append("Os dados permitem afirmar: ...")
    template_sug.append("Não podemos afirmar: (limite explícito) ...")

    with st.expander("Ver sugestão de estrutura (opcional)"):
        st.code("\n".join(template_sug), language="text")
        if _nonempty(mecanismo_dom) or _nonempty(conc_resposta):
            st.caption("Sugestões importadas (para você adaptar):")
            st.write({
                "Mecanismo dominante (importado)": mecanismo_dom or "(não definido)",
                "Resposta do memorial (importada)": conc_resposta[:220] + ("..." if len(conc_resposta) > 220 else ""),
            })

    sintese_texto = st.text_area(
        "Síntese (6–10 linhas)",
        value=_get(state, "sintese_texto", ""),
        height=210,
        key=f"{STAGE_ID}_sintese_texto",
        placeholder="\n".join(template_sug[:6]),
    )
    _set(state, "sintese_texto", sintese_texto)

    linhas = _count_lines(sintese_texto)
    st.caption(f"Linhas contadas (não vazias): {linhas}")

    st.markdown("---")

    # =========================================================================
    # 2) Decisões e implicações (lista curta obrigatória)
    # =========================================================================
    st.markdown("## 2) Decisões e implicações (lista curta obrigatória)")

    dec_met = st.text_area(
        "2.1 Decisão metodológica mais importante (qual e por quê)",
        value=_get(state, "decisao_metodologica", ""),
        height=100,
        key=f"{STAGE_ID}_decisao_metodologica",
        placeholder="Ex.: fixamos pontos e horários para comparar regiões; isso reduziu ambiguidade na interpretação.",
    )
    _set(state, "decisao_metodologica", dec_met)

    imp_pratica = st.text_area(
        "2.2 Principal implicação prática (sem engenharia)",
        value=_get(state, "implicacao_pratica", ""),
        height=90,
        key=f"{STAGE_ID}_implicacao_pratica",
        placeholder="Ex.: abrir janelas em certos momentos aumenta convecção e reduz desconforto quando Ts está alta.",
    )
    _set(state, "implicacao_pratica", imp_pratica)

    imp_conceit = st.text_area(
        "2.3 Principal implicação conceitual (o que aprenderam de Física)",
        value=_get(state, "implicacao_conceitual", ""),
        height=90,
        key=f"{STAGE_ID}_implicacao_conceitual",
        placeholder="Ex.: entendemos que Ts e radiação podem dominar mesmo quando Ta varia pouco; conforto não depende só de Ta.",
    )
    _set(state, "implicacao_conceitual", imp_conceit)

    st.markdown("---")

    # =========================================================================
    # 3) Critério de conclusão (validações)
    # =========================================================================
    st.markdown("## 3) Critério de conclusão (validações)")

    st.caption("O app tenta ler automaticamente o status concluído de cada bloco. Se estiver incorreto, revise o bloco correspondente e salve.")

    c1 = st.checkbox(
        "Reflexão preenchida e coerente com dados (confirmar)",
        value=bool(_get(state, "confirm_reflexao", reflex_ok)),
        key=f"{STAGE_ID}_confirm_reflexao",
        help="Importado automaticamente quando possível.",
    )
    _set(state, "confirm_reflexao", bool(c1))

    c2 = st.checkbox(
        "Memorial completo conforme template (confirmar)",
        value=bool(_get(state, "confirm_memorial", memorial_ok)),
        key=f"{STAGE_ID}_confirm_memorial",
        help="Importado automaticamente quando possível.",
    )
    _set(state, "confirm_memorial", bool(c2))

    c3 = st.checkbox(
        "Seminário registrado (confirmar)",
        value=bool(_get(state, "confirm_seminario", semin_ok)),
        key=f"{STAGE_ID}_confirm_seminario",
        help="Importado automaticamente quando possível.",
    )
    _set(state, "confirm_seminario", bool(c3))

    prontidao = st.checkbox(
        "Estamos prontos para a AVALIAÇÃO individual (declaração obrigatória)",
        value=bool(_get(state, "declaracao_prontidao", False)),
        key=f"{STAGE_ID}_declaracao_prontidao",
    )
    _set(state, "declaracao_prontidao", bool(prontidao))

    # Status importado para debug/transparência
    with st.expander("Status importado dos blocos (somente leitura)"):
        st.write({
            "Reflexão (concluido)": reflex_ok,
            "Memorial (concluido)": memorial_ok,
            "Seminário (concluido)": semin_ok,
            "Mecanismo dominante (importado)": mecanismo_dom or "(não definido)",
        })
        if _nonempty(lim_texto):
            st.markdown("**Limites importados (referência):**")
            st.write(lim_texto)

    st.markdown("---")

    # =========================================================================
    # Diagnóstico final
    # =========================================================================
    st.markdown("## Diagnóstico final")

    faltas: List[str] = []

    # Síntese: 6–10 linhas e não vazia
    if not _nonempty(_get(state, "sintese_texto", "")):
        faltas.append("- Preencha a síntese (1).")
    else:
        if linhas < 6 or linhas > 10:
            faltas.append(f"- Ajuste a síntese para 6–10 linhas (atual: {linhas}).")

    # Decisões/implicações
    if not _nonempty(_get(state, "decisao_metodologica", "")):
        faltas.append("- Preencha: decisão metodológica mais importante (2.1).")
    if not _nonempty(_get(state, "implicacao_pratica", "")):
        faltas.append("- Preencha: principal implicação prática (2.2).")
    if not _nonempty(_get(state, "implicacao_conceitual", "")):
        faltas.append("- Preencha: principal implicação conceitual (2.3).")

    # Validações
    if not bool(_get(state, "confirm_reflexao", False)):
        faltas.append("- Confirme: reflexão preenchida (3).")
    if not bool(_get(state, "confirm_memorial", False)):
        faltas.append("- Confirme: memorial completo (3).")
    if not bool(_get(state, "confirm_seminario", False)):
        faltas.append("- Confirme: seminário registrado (3).")
    if not bool(_get(state, "declaracao_prontidao", False)):
        faltas.append("- Marque a declaração de prontidão para a avaliação individual (3).")

    concluido = len(faltas) == 0
    _set(state, "concluido", bool(concluido))

    if concluido:
        st.success("Fase SOLUÇÃO concluída. Checkpoint final atendido; pronto para AVALIAÇÃO individual.")
    else:
        st.warning("Checkpoint ainda incompleto. Itens faltantes:")
        st.markdown("\n".join(faltas))

    st.markdown("---")

    # =========================================================================
    # Salvar
    # =========================================================================
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Salvar", key=f"{STAGE_ID}_salvar"):
            payload = {
                "sintese_texto": _get(state, "sintese_texto", ""),
                "sintese_linhas": int(linhas),

                "decisao_metodologica": _get(state, "decisao_metodologica", ""),
                "implicacao_pratica": _get(state, "implicacao_pratica", ""),
                "implicacao_conceitual": _get(state, "implicacao_conceitual", ""),

                "confirm_reflexao": bool(_get(state, "confirm_reflexao", False)),
                "confirm_memorial": bool(_get(state, "confirm_memorial", False)),
                "confirm_seminario": bool(_get(state, "confirm_seminario", False)),
                "declaracao_prontidao": bool(_get(state, "declaracao_prontidao", False)),

                # Importados (úteis para rastreabilidade)
                "_import_reflexao_concluido": reflex_ok,
                "_import_memorial_concluido": memorial_ok,
                "_import_seminario_concluido": semin_ok,
                "_import_mecanismo_dom": mecanismo_dom,
                "_import_conclusao_memorial": conc_resposta,

                "concluido": bool(_get(state, "concluido", False)),
            }
            save_json(path_json, payload)

            if payload["concluido"]:
                st.success("Salvo e marcado como concluído.")
            else:
                st.success("Salvo. Atenção: ainda há pendências para concluir.")

    with col2:
        st.markdown("**Resumo atual**")
        st.write({
            "Linhas na síntese": linhas,
            "Reflexão (importado)": reflex_ok,
            "Memorial (importado)": memorial_ok,
            "Seminário (importado)": semin_ok,
            "Declaração": bool(_get(state, "declaracao_prontidao", False)),
            "Concluído": bool(_get(state, "concluido", False)),
        })
