import streamlit as st
import json
import os
from dotenv import load_dotenv
from infrastructure.pdf_reader import extract_text_from_pdf
from infrastructure.ai_client import extract_transactions_with_ai
from infrastructure.sheets_client import update_google_sheet

load_dotenv()
sheet_url = os.getenv("SPREADSHEET_URL")

st.set_page_config(page_title="Extrator de Faturas", page_icon="🧾")

st.title("🧾 Leitor de Fatura Bradesco")
st.write("Faça o upload do seu PDF. A IA irá extrair os gastos e enviar para o Sheets com o novo visual.")

uploaded_file = st.file_uploader("Arraste sua fatura aqui", type="pdf")

if uploaded_file is not None:
    if st.button("Processar Fatura e Enviar para o Sheets"):
        
        with st.spinner("Lendo o arquivo PDF..."):
            texto_bruto = extract_text_from_pdf(uploaded_file)
            
        with st.spinner("Analisando transações com o Gemini..."):
            json_response = extract_transactions_with_ai(texto_bruto)
            
            try:
                dados_estruturados = json.loads(json_response)
                # Pega a lista de transações para validação no front-end
                transacoes = dados_estruturados.get("transacoes", [])
            except json.JSONDecodeError:
                st.error("Erro ao interpretar a resposta da IA. Tente novamente.")
                st.stop()

        if not transacoes:
            st.warning("Nenhuma transação encontrada nesta fatura.")
            st.stop()

        st.success(f"{len(transacoes)} transações extraídas com sucesso!")
        st.dataframe(transacoes, use_container_width=True)
        
        with st.spinner("Formatando painel e enviando para a planilha..."):
            # Aqui enviamos o dicionário COMPLETO para o sheets_client
            update_google_sheet(dados_estruturados, sheet_url)
            
        st.balloons()
        st.success("Tudo pronto! Dashboard atualizado no Google Sheets.")