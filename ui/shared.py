import pandas as pd
import streamlit as st

from infrastructure.sheets_reader import fetch_categorias_df, fetch_transacoes_df

# Paleta categorica validada (skill de dataviz) — ordem fixa de slots, nunca ciclada.
CATEGORICAL_HUES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
GRIDLINE = "#e1e0d9"


@st.cache_data(ttl=90, show_spinner="Buscando dados atualizados da planilha...")
def carregar_dados(sheet_url: str) -> pd.DataFrame:
    return fetch_transacoes_df(sheet_url)


@st.cache_data(ttl=90, show_spinner="Buscando categorias da planilha...")
def carregar_categorias(sheet_url: str) -> pd.DataFrame:
    return fetch_categorias_df(sheet_url)


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
