import streamlit as st
import json
import os
from dotenv import load_dotenv
from infrastructure.pdf_reader import extract_text_from_pdf
from infrastructure.ai_client import extract_transactions_with_ai
from infrastructure.sheets_client import update_google_sheet

# Carrega as variáveis de ambiente
load_dotenv()
sheet_url = os.getenv("SPREADSHEET_URL")

# Configuração da página web
st.set_page_config(page_title="Extrator de Faturas", page_icon="🧾")

st.title("🧾 Leitor de Fatura Bradesco")
st.write("Faça o upload do seu PDF. A IA irá extrair os gastos, remover estornos/pagamentos e enviar para o Sheets.")

# Componente de Upload de Arquivo
uploaded_file = st.file_uploader("Arraste sua fatura aqui", type="pdf")

if uploaded_file is not None:
    # Botão para iniciar o fluxo
    if st.button("Processar Fatura e Enviar para o Sheets"):
        
        # Passo 1: Extração
        with st.spinner("Lendo o arquivo PDF..."):
            texto_bruto = extract_text_from_pdf(uploaded_file)
            
        # Passo 2: Inteligência Artificial
        with st.spinner("Analisando transações com o Gemini..."):
            json_response = extract_transactions_with_ai(texto_bruto)
            
            try:
                dados_estruturados = json.loads(json_response)
                transacoes = dados_estruturados.get("transacoes", [])
            except json.JSONDecodeError:
                st.error("Erro ao interpretar a resposta da IA. Tente novamente.")
                st.stop()

        if not transacoes:
            st.warning("Nenhuma transação encontrada nesta fatura.")
            st.stop()

        # Mostra uma tabela visual na tela para você conferir os dados
        st.success(f"{len(transacoes)} transações extraídas com sucesso!")
        st.dataframe(transacoes, use_container_width=True)
        
        # Passo 3: Inserção no Google Sheets
        with st.spinner("Enviando dados para a planilha principal..."):
            update_google_sheet(transacoes, sheet_url)
            
        # Efeito visual de sucesso
        st.balloons()
        st.success("Tudo pronto! Planilha atualizada.")