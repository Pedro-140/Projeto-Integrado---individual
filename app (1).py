"""Painel principal. Na integração do grupo, basta importar o módulo de cada colega
e adicionar uma aba com `modulo.render()`."""
import streamlit as st

import mulheres
import rendimento

st.set_page_config(page_title="Indicadores Demográficos - IBGE", page_icon="📊", layout="wide")
st.title("📊 Indicadores Demográficos do IBGE")

abas = st.tabs(["👩 Mulheres", "💰 Rendimento dos Responsáveis"])
with abas[0]:
    mulheres.render()
with abas[1]:
    rendimento.render()
