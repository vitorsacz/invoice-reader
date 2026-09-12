import os

import streamlit as st
from dotenv import load_dotenv

from ui.upload_tab import render_upload_tab
from ui.dashboard_tab import render_dashboard_tab
from ui.planilha_tab import render_planilha_tab
from ui.categoria_tab import render_categoria_tab

load_dotenv()
sheet_url = os.getenv("SPREADSHEET_URL")

st.set_page_config(page_title="Leitor de Faturas", page_icon="🧾", layout="wide")

tab_upload, tab_dashboard, tab_planilha, tab_categoria = st.tabs(
    ["📤 Nova Fatura", "📊 Dashboard", "🗂️ Visão da Planilha", "🥧 Por Categoria"]
)

with tab_upload:
    render_upload_tab(sheet_url)

with tab_dashboard:
    render_dashboard_tab(sheet_url)

with tab_planilha:
    render_planilha_tab(sheet_url)

with tab_categoria:
    render_categoria_tab(sheet_url)
