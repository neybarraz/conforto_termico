# ui/sidebar.py
from typing import Dict
import streamlit as st

def render_sidebar() -> Dict:
    st.sidebar.header("Contexto")
    turma = st.sidebar.text_input("Turma", value="Física 2 - 2026-1")
    grupo = st.sidebar.text_input("Grupo", value="G1")
    return {"turma": turma, "grupo": grupo}
