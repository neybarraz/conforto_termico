# blocks/solucao/seminario_pbl.py
# =============================================================================
# Seminário PBL — Estrutura fixa (engenharia) + Rubrica em tabela + Upload PDF
#
# Atualização solicitada:
# - Nome do aluno obtido automaticamente COM A MESMA LÓGICA do memorial_tecnico.py:
#   _get_aluno_name(ctx) + _sanitize_filename(s)
# - Salva somente PDF em: data/pdf/<nome_do_aluno>_seminario.pdf
#
# Observação: NÃO há checklist interativo; a estrutura é lista fixa.
# Única interação: upload do PDF.
# Sem diagnóstico e sem resumo no final.
# =============================================================================

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st


STAGE_ID = "solucao_seminario_pbl"

# Estrutura profissional, padrão, independente do tema (13 slides)
SLIDE_STRUCTURE: List[Dict[str, Any]] = [
    {"secao": "Introdução", "n": 1, "titulo": "Problema", "conteudo": "Defina o problema observado e por que ele importa (impacto/risco/qualidade)."},
    {"secao": "Introdução", "n": 2, "titulo": "Contexto", "conteudo": "Descreva o ambiente/sistema: onde, quando, condições e restrições relevantes."},
    {"secao": "Introdução", "n": 3, "titulo": "Pergunta norteadora", "conteudo": "Pergunta objetiva que será respondida com dados. Evite ambiguidade."},
    {"secao": "Introdução", "n": 4, "titulo": "Defesa do grupo (tese)", "conteudo": "Uma frase: 'Defendemos que ___ (mecanismo) porque ___ (evidência) dentro de ___ (limite)'."},

    {"secao": "Método", "n": 5, "titulo": "Método (visão geral)", "conteudo": "Desenho do teste: pontos, rodadas, controles e registro de condições."},
    {"secao": "Método", "n": 6, "titulo": "Medidas e instrumentação", "conteudo": "Grandezas, sensores, resolução/precisão, procedimento e limitações instrumentais."},

    {"secao": "Resultados", "n": 7, "titulo": "Gráficos (principais)", "conteudo": "1–2 gráficos essenciais. Leia: tendência, máximos/mínimos, comparação, variação."},
    {"secao": "Resultados", "n": 8, "titulo": "Dados secundários (apoio)", "conteudo": "Tabela curta/resumo estatístico/observações auxiliares que sustentam a tese."},

    {"secao": "Interpretação física", "n": 9, "titulo": "Interpretação física I (mecanismo dominante)", "conteudo": "Causalidade física: como o mecanismo produz o padrão observado nos dados."},
    {"secao": "Interpretação física", "n": 10, "titulo": "Interpretação física II (evidências e contraprova)", "conteudo": "Duas evidências fortes + um contraexemplo/condição onde o mecanismo enfraquece (limite)."},

    {"secao": "Fechamento", "n": 11, "titulo": "Conclusão", "conteudo": "Responda a pergunta norteadora explicitamente. Declare condições de validade."},
    {"secao": "Fechamento", "n": 12, "titulo": "Incertezas, limites e melhorias", "conteudo": "3 limitações relevantes + 2 melhorias concretas para repetir com maior confiabilidade."},

    {"secao": "Defesa", "n": 13, "titulo": "Perguntas prováveis + respostas curtas", "conteudo": "Respostas no padrão: DADO → CONCEITO → CONCLUSÃO (sem 'achismo')."},
]

# Rubrica em formato: "% — Critério" | "Descrição"
RUBRIC_TABLE: List[Dict[str, str]] = [
    {"col1": "15% — Problema, contexto e pergunta", "col2": "Clareza do problema, delimitação do contexto e pergunta norteadora objetiva e respondível."},
    {"col1": "15% — Método e controle de condições", "col2": "Como/onde/quando; nº de rodadas; variáveis controladas/registradas; coerência do procedimento."},
    {"col1": "20% — Dados e leitura de gráficos", "col2": "Seleção enxuta e leitura correta (tendência, comparação, variabilidade); sem exagero de figuras."},
    {"col1": "25% — Interpretação física e causalidade", "col2": "Defesa do mecanismo dominante com causalidade física sustentada por evidência."},
    {"col1": "15% — Incertezas, limites e melhorias", "col2": "Identificação de fontes de erro/viés e propostas concretas de melhoria, com prioridade."},
    {"col1": "10% — Defesa oral", "col2": "Respostas coerentes (dado→conceito→conclusão), postura científica e reconhecimento de limites."},
]


# =============================================================================
# Nome do aluno (MESMO PADRÃO DO memorial_tecnico.py)
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


def _seminario_pdf_path(ctx: Dict) -> Path:
    aluno = _sanitize_filename(_get_aluno_name(ctx))
    p = Path("data") / "pdf" / f"{aluno}_05_seminario.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# =============================================================================
# Render
# =============================================================================
def render(ctx: Dict[str, Any] | None = None) -> None:
    if not isinstance(ctx, dict):
        ctx = {}

    st.title("Seminário PBL — Estrutura, Critérios e Envio do PDF")
    st.caption("Padrão de apresentação técnico (engenharia), independente do tema. Única ação: anexar o PDF.")

    st.markdown("---")

    # Estrutura (lista fixa, sem interações)
    st.subheader("Estrutura do seminário (13 slides)")
    st.write(
        "Sequência fixa recomendada para defesa técnica: afirmação → evidência → mecanismo → limites."
    )

    current_section = None
    for item in SLIDE_STRUCTURE:
        if item["secao"] != current_section:
            current_section = item["secao"]
            st.markdown(f"**{current_section}**")
        st.markdown(f"- **Slide {item['n']}: {item['titulo']}** — {item['conteudo']}")

    st.markdown("---")

    # Rubrica em tabela (2 colunas)
    st.subheader("Critérios de avaliação")
    st.caption("Tabela de avaliação (peso e descrição do que será avaliado).")

    table_rows = [
        {"% da avaliação — Critério de avaliação": r["col1"], "Descrição da avaliação": r["col2"]}
        for r in RUBRIC_TABLE
    ]
    st.table(table_rows)

    st.markdown("---")

    # Upload PDF (única interação) + salvamento com nome automático
    st.subheader("Envio do seminário (PDF obrigatório)")

    aluno_nome = _get_aluno_name(ctx)
    aluno_slug = _sanitize_filename(aluno_nome)

    # Se veio "anon", o app principal não está passando nome de forma confiável.
    if aluno_slug == "anon":
        st.error(
            "Não foi possível obter o nome do aluno automaticamente (ctx/state retornou 'anon'). "
            "O app principal precisa fornecer o nome em ctx (ex.: ctx['nome_aluno']) ou em ctx['state']."
        )
        st.stop()

    out_path = _seminario_pdf_path(ctx)
    st.write(f"Aluno: **{aluno_nome}**")
    st.caption(f"Destino do arquivo: {out_path.as_posix()}")

    uploaded = st.file_uploader(
        "Anexe o PDF do seminário",
        type=["pdf"],  # bloqueia outros tipos no seletor
        accept_multiple_files=False,
        key=f"{STAGE_ID}_uploader",
    )

    if uploaded is not None:
        # Validação extra: extensão e MIME
        fname = (uploaded.name or "").lower()
        mime = (uploaded.type or "").lower()
        is_pdf_ext = fname.endswith(".pdf")
        is_pdf_mime = (mime == "application/pdf")

        if not (is_pdf_ext or is_pdf_mime):
            st.error("Arquivo rejeitado: somente PDF é aceito.")
            st.stop()

        out_path.write_bytes(uploaded.getbuffer())
        st.success("PDF enviado e salvo com sucesso.")
