import json

import streamlit as st

from infrastructure.pdf_reader import extract_text_from_pdf
from infrastructure.ai_client import extract_transactions_with_ai
from infrastructure.sheets_client import update_google_sheet


def render_upload_tab(sheet_url: str) -> None:
    st.title("🧾 Leitor de Fatura")
    st.write("Faça o upload do seu PDF. A IA irá extrair os gastos e organizar na aba do mês correspondente.")

    uploaded_file = st.file_uploader("Arraste sua fatura aqui", type="pdf")

    if uploaded_file is None:
        return

    if not st.button("Processar Fatura e Enviar para o Sheets"):
        return

    with st.spinner("Lendo o arquivo PDF..."):
        texto_bruto = extract_text_from_pdf(uploaded_file)

    with st.spinner("Analisando transações e detectando o mês..."):
        json_response = extract_transactions_with_ai(texto_bruto)

        try:
            dados_estruturados = json.loads(json_response)
        except json.JSONDecodeError:
            st.error("Erro ao interpretar a resposta da IA. Tente novamente.")
            st.stop()

        transacoes = dados_estruturados.get("transacoes", [])
        banco_detectado = dados_estruturados.get("banco", "Banco")
        mes_detectado = dados_estruturados.get("mes_fatura", "").capitalize()
        ano_detectado = dados_estruturados.get("ano_fatura", "")
        periodo_detectado = f"{mes_detectado}/{ano_detectado}"

    if not transacoes:
        st.warning("Nenhuma transação encontrada nesta fatura.")
        st.stop()

    st.success(f"Fatura {banco_detectado} ({periodo_detectado}) detectada! {len(transacoes)} transações extraídas.")
    st.dataframe(transacoes, use_container_width=True)

    with st.spinner(f"Criando/Atualizando a aba '{mes_detectado}' no Google Sheets..."):
        update_google_sheet(dados_estruturados, sheet_url)

    st.balloons()
    st.success(f"Tudo pronto! Dashboard atualizado na aba {mes_detectado}.")
