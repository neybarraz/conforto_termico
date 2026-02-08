# app.py
from __future__ import annotations

import importlib
from typing import Callable, Dict, List, Tuple, Optional

import streamlit as st

from config.settings import APP_TITLE
from storage.paths import get_students_csv_path
from ui.auth import load_students_csv, authenticate, is_enabled_for_phase


def _safe_import_render(module_path: str) -> Tuple[Callable[[Dict], None] | None, str | None]:
    try:
        mod = importlib.import_module(module_path)
        render_func = getattr(mod, "render", None)
        if not callable(render_func):
            return None, f"Módulo '{module_path}' não possui função render(ctx)."
        return render_func, None
    except Exception as e:
        return None, f"Não foi possível importar '{module_path}': {e}"


def _render_stage(title: str, module_path: str, ctx: Dict) -> None:
    # st.subheader(title)
    render_func, err = _safe_import_render(module_path)
    if err:
        st.warning(err)
        st.info("Etapa ainda não implementada ou com erro. Ajuste/crie o arquivo em blocks/.")
        return
    render_func(ctx=ctx)


# =============================================================================
# LOGIN ÚNICO (GLOBAL) + GATE POR FASE (SEM PEDIR SENHA DE NOVO)
# =============================================================================
def _ensure_login(records, ctx: Dict) -> bool:
    """
    Login único:
    - aluno escolhe nome + senha UMA vez
    - salva student no session_state
    - ctx recebe aluno/grupo_id/grupo_nome em toda execução
    """
    if st.session_state.get("auth_ok", False) and st.session_state.get("student") is not None:
        student = st.session_state["student"]
        ctx["aluno"] = student.nome
        ctx["grupo_id"] = student.grupo_id
        ctx["grupo_nome"] = student.grupo_nome
        return True

    if not records:
        st.error("Arquivo de alunos não encontrado ou vazio. Crie/edite data/alunos.csv.")
        st.caption(f"Caminho esperado: {get_students_csv_path()}")
        return False

    st.subheader("Acesso do Aluno")
    nomes = [r.nome for r in records]
    nome_sel = st.selectbox("Selecione seu nome", options=nomes, index=0, key="sel_nome_global")
    senha = st.text_input("Senha", type="password", key="pwd_global")

    if st.button("Entrar", key="btn_login_global"):
        ok, student = authenticate(records, nome_sel, senha)
        if not ok or student is None:
            st.error("Nome ou senha inválidos.")
            return False

        st.session_state["auth_ok"] = True
        st.session_state["student"] = student

        ctx["aluno"] = student.nome
        ctx["grupo_id"] = student.grupo_id
        ctx["grupo_nome"] = student.grupo_nome

        st.success(f"Acesso liberado: {student.nome} — Grupo {student.grupo_id} ({student.grupo_nome})")
        st.rerun()

    st.info("Faça login uma única vez para acessar o aplicativo.")
    return False


def _logout_button() -> None:
    # Logout global (serve para qualquer aba)
    if st.button("Sair (logout)", key="btn_logout_global"):
        st.session_state["auth_ok"] = False
        st.session_state["student"] = None
        st.rerun()


def _gate_phase(phase_label: str) -> bool:
    """
    Gate por fase SEM senha:
    - requer login global já feito
    - checa habilitação da fase no student do session_state
    """
    student = st.session_state.get("student")
    if student is None:
        return False

    if not is_enabled_for_phase(student, phase_label):
        st.error("Você não está habilitado para acessar esta fase no momento.")
        return False

    return True


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    # Contexto global (o que não muda por aluno)
    ctx: Dict = {
        "tema": "Conforto Térmico em Ambientes do Campus",
        "turma": "Física 2",
    }

    # Carrega alunos do CSV
    records = load_students_csv(get_students_csv_path())

    # LOGIN ÚNICO (antes das abas)
    if not _ensure_login(records, ctx):
        st.stop()

    # Cabeçalho de status (já logado)
    st.success(f"Acesso liberado: {ctx['aluno']} — Grupo {ctx['grupo_id']} ({ctx['grupo_nome']})")
    _logout_button()

    fases: List[Tuple[str, List[Tuple[str, str]]]] = [
        ("Problema", [
            ("Contextualização", "blocks.problema.contextualizacao"),
            ("Escopo do problema", "blocks.problema.escopo_do_problema"),
            ("Pergunta central", "blocks.problema.pergunta_central"),
            ("Diagnóstico inicial", "blocks.problema.diagnostico_inicial"),
            ("Objetivos do projeto", "blocks.problema.objetivos"),
            ("Critérios de avaliação", "blocks.problema.criterios_de_avaliacao"),
            ("Conteúdos Essenciais", "blocks.problema.conteudos_essenciais"),
            ("Registro parcial do problema", "blocks.problema.registro_parcial_do_problema"),
        ]),
        ("Investigação", [
            ("Grandezas Físicas Medidas", "blocks.investigacao.01_grandezas_fisicas"),
            ("Cenário da Coleta", "blocks.investigacao.02_cenario_da_coleta"),
            ("Dimensões do Ambiente", "blocks.investigacao.03_dimensoes_do_ambiente"),
            ("Medidas", "blocks.investigacao.04_medidas"),
            ("Análises Física, parte I", "blocks.investigacao.05_analise_fisica_I"),  
            ("Análises Física, parte II", "blocks.investigacao.05_analise_fisica_II"),           
            ("Entregável Parcial", "blocks.investigacao.06_registro_parcial_da_investigacao"),
            # ("Entregável Parcial", "blocks.investigacao.06_registro_parcial_da_investigacao_2"),
            # ("Entregável Parcial", "blocks.investigacao.06_registro_parcial_da_investigacao_3"),



        ]),
        ("Solução", [
            ("Reflexão e Metacognição", "blocks.solucao.reflexao_metacognicao"),
            ("Memorial Técnico", "blocks.solucao.memorial_tecnico"),
            ("Seminário", "blocks.solucao.seminario"),
            # ("Síntese da Fase (Solução)", "blocks.solucao.sintese_solucao"),
        ]),
        ("Avaliação", [
            ("Prova", "blocks.avaliacao.prova"),
            ("Avaliação Recuperativa", "blocks.avaliacao.recuperativa"),
        ]),
    ]

    tabs = st.tabs([nome for nome, _ in fases])

    for tab, (nome_fase, etapas) in zip(tabs, fases):
        with tab:
            # Gate por fase (sem senha)
            if not _gate_phase(nome_fase):
                st.stop()

            for titulo_etapa, module_path in etapas:
                with st.expander(titulo_etapa, expanded=False):
                    _render_stage(titulo_etapa, module_path, ctx)

            st.divider()


if __name__ == "__main__":
    main()
