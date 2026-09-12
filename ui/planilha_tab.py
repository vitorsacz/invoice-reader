import pandas as pd
import streamlit as st

from core import metrics
from core.categorias import aplicar_categorias
from ui.shared import carregar_categorias, carregar_dados, formatar_moeda

_COLUNAS_TABELA = ["Data", "Estabelecimento", "Tipo", "Categoria", "Parcela", "Valor"]


def render_planilha_tab(sheet_url: str) -> None:
    st.title("🗂️ Visão da Planilha")
    st.caption("Mesmo recorte do dashboard dinâmico de cada banco na planilha do Google Sheets: escolha o banco, o período e a categoria.")

    df = carregar_dados(sheet_url)
    if df.empty:
        st.info("Nenhuma transação encontrada na planilha ainda. Processe uma fatura na aba \"Nova Fatura\".")
        return

    df = aplicar_categorias(df, carregar_categorias(sheet_url))
    todos_bancos = sorted(df["Banco"].unique())

    col_banco, col_periodo = st.columns([1, 2])
    with col_banco:
        banco_sel = st.selectbox("Banco", todos_bancos, key="planilha_banco")

    df_banco = df[df["Banco"] == banco_sel]
    periodos = _periodo_options(df_banco)

    with col_periodo:
        periodo_sel = st.selectbox(
            "Selecione o Período (Mês/Ano):",
            periodos,
            index=len(periodos) - 1,
            key="planilha_periodo",
        )

    df_periodo = df_banco[df_banco["Periodo"] == periodo_sel].sort_values("Data")

    categorias_disponiveis = sorted(df_periodo["Categoria"].unique())
    categorias_sel = st.multiselect(
        "Categoria",
        categorias_disponiveis,
        default=categorias_disponiveis,
        key="planilha_categoria",
    )
    df_periodo = df_periodo[df_periodo["Categoria"].isin(categorias_sel)]
    df_parcelado = df_periodo[df_periodo["Tipo"] == "Parcelado"]

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Total Geral", formatar_moeda(metrics.total_gasto(df_periodo)))
    col2.metric("Valores Normais", formatar_moeda(metrics.total_gasto(df_periodo[df_periodo["Tipo"] == "Normal"])))
    col3.metric("Valores Parcelados", formatar_moeda(metrics.total_gasto(df_parcelado)))

    st.divider()

    col_todos, col_parcelados = st.columns(2)
    with col_todos:
        st.markdown(f"**Todos os gastos** ({len(df_periodo)})")
        _render_tabela(df_periodo)
    with col_parcelados:
        st.markdown(f"**Só parcelados** ({len(df_parcelado)})")
        _render_tabela(df_parcelado)


def _periodo_options(df_banco: pd.DataFrame) -> list[str]:
    return (
        df_banco[["Periodo", "PeriodoData"]]
        .drop_duplicates()
        .sort_values("PeriodoData")["Periodo"]
        .tolist()
    )


def _render_tabela(df: pd.DataFrame) -> None:
    st.dataframe(
        df[_COLUNAS_TABELA],
        use_container_width=True,
        hide_index=True,
        column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")},
    )
