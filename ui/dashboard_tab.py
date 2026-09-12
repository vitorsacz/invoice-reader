from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from core import filters, metrics
from ui.shared import CATEGORICAL_HUES, GRIDLINE, carregar_dados, formatar_moeda

# Cor segue a ENTIDADE (o nome do banco), nao a posicao apos um filtro.
_HUE_NORMAL, _HUE_PARCELADO = CATEGORICAL_HUES[0], CATEGORICAL_HUES[1]
_GRIDLINE = GRIDLINE

_TIPO_SCALE = alt.Scale(domain=["Normal", "Parcelado"], range=[_HUE_NORMAL, _HUE_PARCELADO])


def _banco_scale(todos_bancos: list[str]) -> alt.Scale:
    bancos_ordenados = sorted(todos_bancos)
    return alt.Scale(domain=bancos_ordenados, range=CATEGORICAL_HUES[: len(bancos_ordenados)])


def render_dashboard_tab(sheet_url: str) -> None:
    col_titulo, col_refresh = st.columns([5, 1])
    with col_titulo:
        st.title("📊 Dashboard de Gastos")
    with col_refresh:
        st.write("")
        if st.button("🔄 Atualizar dados", use_container_width=True):
            carregar_dados.clear()
            st.rerun()

    df = carregar_dados(sheet_url)
    if df.empty:
        st.info("Nenhuma transação encontrada na planilha ainda. Processe uma fatura na aba ao lado.")
        return

    todos_bancos = sorted(df["Banco"].unique())
    banco_scale = _banco_scale(todos_bancos)

    aba_banco, aba_comparacao = st.tabs(["🏦 Por Banco", "⚖️ Comparação entre Bancos"])
    with aba_banco:
        _render_visao_por_banco(df, todos_bancos, banco_scale)
    with aba_comparacao:
        _render_comparacao_bancos(df, todos_bancos, banco_scale)


def _periodo_options(df: pd.DataFrame) -> list[str]:
    return (
        df[["Periodo", "PeriodoData"]]
        .drop_duplicates()
        .sort_values("PeriodoData")["Periodo"]
        .tolist()
    )


def _ordem_periodos(dados: pd.DataFrame) -> list[str]:
    """Ordem cronologica explicita de Periodo. Necessaria porque alt.SortField
    nao aceita um op de agregacao nesta versao do Altair - sem isso, categorias
    com mais de uma linha (uma por banco) ordenam incorretamente."""
    return _periodo_options(dados)


def _render_visao_por_banco(df: pd.DataFrame, todos_bancos: list[str], banco_scale: alt.Scale) -> None:
    col_banco, col_periodo, col_tipo = st.columns([2, 3, 2])
    with col_banco:
        bancos_sel = st.multiselect("Banco", todos_bancos, default=todos_bancos, key="banco_filtro")
    with col_periodo:
        opcoes_periodo = _periodo_options(df)
        periodo_ini, periodo_fim = st.select_slider(
            "Período",
            options=opcoes_periodo,
            value=(opcoes_periodo[0], opcoes_periodo[-1]),
            key="periodo_filtro",
        )
    with col_tipo:
        tipos_sel = st.multiselect("Tipo", ["Normal", "Parcelado"], default=["Normal", "Parcelado"], key="tipo_filtro")

    mapa_periodo_data = dict(zip(df["Periodo"], df["PeriodoData"]))
    range_datas = (mapa_periodo_data[periodo_ini].date(), mapa_periodo_data[periodo_fim].date())

    df_sem_periodo = filters.aplicar_filtros(df, bancos=bancos_sel, tipos=tipos_sel)
    df_filtrado = filters.filtrar_por_periodo(df_sem_periodo, *range_datas)

    if df_filtrado.empty:
        st.warning("Nenhuma transação encontrada para os filtros selecionados.")
        return

    _render_kpis(df_filtrado, df_sem_periodo, range_datas)
    st.divider()

    col_tendencia, col_breakdown = st.columns([2, 1])
    with col_tendencia:
        st.markdown("**Gasto por período**")
        st.altair_chart(_chart_tendencia(df_filtrado, banco_scale), use_container_width=True)
    with col_breakdown:
        st.markdown("**Parcelado vs. Normal**")
        st.altair_chart(_chart_breakdown_tipo(df_filtrado), use_container_width=True)

    st.markdown("**Top 10 estabelecimentos**")
    st.altair_chart(_chart_top_estabelecimentos(df_filtrado), use_container_width=True)

    st.divider()
    _render_parcelas_em_aberto(filters.filtrar_por_banco(df, bancos_sel))

    st.divider()
    _render_tabela_detalhada(df_filtrado)


def _render_kpis(df_filtrado: pd.DataFrame, df_sem_periodo: pd.DataFrame, range_datas: tuple) -> None:
    total_atual, total_anterior = metrics.delta_periodo_anterior(df_sem_periodo, range_datas)
    delta = None if total_anterior is None else total_atual - total_anterior

    resumo_tipo = metrics.resumo_por_tipo(df_filtrado)
    valor_parcelado = resumo_tipo.loc[resumo_tipo["Tipo"] == "Parcelado", "valor_total"].sum()
    pct_parcelado = (valor_parcelado / total_atual * 100) if total_atual else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Gasto", formatar_moeda(total_atual), None if delta is None else formatar_moeda(delta))
    col2.metric("Nº Transações", f"{len(df_filtrado)}")
    col3.metric("Ticket Médio", formatar_moeda(metrics.ticket_medio(df_filtrado)))
    col4.metric("% Parcelado", f"{pct_parcelado:.1f}%")


def _chart_tendencia(df: pd.DataFrame, banco_scale: alt.Scale) -> alt.Chart:
    dados = metrics.gasto_por_periodo(df)
    return (
        alt.Chart(dados)
        .mark_line(point={"size": 64}, strokeWidth=2)
        .encode(
            x=alt.X("Periodo:N", sort=_ordem_periodos(dados), title=None, axis=alt.Axis(grid=False, labelAngle=-30)),
            y=alt.Y("valor_total:Q", title=None, axis=alt.Axis(gridColor=_GRIDLINE)),
            color=alt.Color("Banco:N", scale=banco_scale, legend=alt.Legend(title=None) if dados["Banco"].nunique() > 1 else None),
            tooltip=[
                alt.Tooltip("Banco:N"),
                alt.Tooltip("Periodo:N", title="Período"),
                alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
            ],
        )
        .properties(height=280, width="container")
    )


def _chart_breakdown_tipo(df: pd.DataFrame) -> alt.Chart:
    dados = metrics.resumo_por_tipo(df)
    dados = dados.assign(categoria="Total")

    base = alt.Chart(dados).encode(
        x=alt.X("valor_total:Q", stack="normalize", title=None, axis=None),
        y=alt.Y("categoria:N", title=None, axis=None),
        order=alt.Order("Tipo:N"),
        tooltip=[
            alt.Tooltip("Tipo:N"),
            alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
            alt.Tooltip("percentual:Q", title="%", format=".1f"),
        ],
    )
    barras = base.mark_bar(cornerRadiusEnd=4, size=40).encode(
        color=alt.Color("Tipo:N", scale=_TIPO_SCALE, legend=alt.Legend(title=None, orient="bottom")),
    )
    rotulos = (
        base.transform_calculate(percentual_label="format(datum.percentual, '.0f') + '%'")
        .mark_text(color="white", fontWeight="bold")
        .encode(text=alt.Text("percentual_label:N"))
    )

    return (barras + rotulos).properties(height=100, width="container")


def _chart_top_estabelecimentos(df: pd.DataFrame) -> alt.Chart:
    dados = metrics.top_estabelecimentos(df, n=10)
    return (
        alt.Chart(dados)
        .mark_bar(cornerRadiusEnd=4, size=18, color=_HUE_NORMAL)
        .encode(
            x=alt.X("valor_total:Q", title=None, axis=alt.Axis(gridColor=_GRIDLINE)),
            y=alt.Y("Estabelecimento:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            tooltip=[
                alt.Tooltip("Estabelecimento:N"),
                alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
            ],
        )
        .properties(height=320, width="container")
    )


def _render_parcelas_em_aberto(df_banco: pd.DataFrame) -> None:
    st.markdown("**📌 Parcelas em aberto** — compromisso estimado com compras parceladas ainda não quitadas")
    aberto = metrics.parcelas_em_aberto(df_banco)
    if aberto.empty:
        st.caption("Nenhuma parcela em aberto para o(s) banco(s) selecionado(s).")
        return

    st.metric("Valor total comprometido", formatar_moeda(aberto["valor_restante"].sum()))
    st.dataframe(
        aberto.rename(columns={
            "Estabelecimento": "Estabelecimento", "Banco": "Banco",
            "parcelas_restantes": "Parcelas restantes", "valor_restante": "Valor restante",
            "ultima_parcela_vista": "Última parcela vista",
        })[["Banco", "Estabelecimento", "Última parcela vista", "Parcelas restantes", "Valor restante"]],
        use_container_width=True,
        hide_index=True,
        column_config={"Valor restante": st.column_config.NumberColumn(format="R$ %.2f")},
    )


def _render_tabela_detalhada(df: pd.DataFrame) -> None:
    st.markdown("**Transações detalhadas**")
    busca = st.text_input("🔎 Buscar estabelecimento", key="busca_estabelecimento")
    tabela = df
    if busca:
        tabela = tabela[tabela["Estabelecimento"].str.contains(busca, case=False, na=False)]

    tabela = tabela.sort_values("PeriodoData", ascending=False)[
        ["Banco", "Periodo", "Data", "Estabelecimento", "Tipo", "Parcela", "Valor"]
    ]
    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
        column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")},
    )


def _render_comparacao_bancos(df: pd.DataFrame, todos_bancos: list[str], banco_scale: alt.Scale) -> None:
    if len(todos_bancos) < 2:
        st.info("Só há dados de um banco na planilha — a comparação fica disponível quando houver mais de um.")
        return

    resumo = metrics.resumo_por_banco(df)
    colunas = st.columns(len(todos_bancos))
    for col, (_, linha) in zip(colunas, resumo.iterrows()):
        with col:
            st.markdown(f"**{linha['Banco']}**")
            st.metric("Total Gasto", formatar_moeda(linha["valor_total"]))
            st.metric("Nº Transações", f"{int(linha['contagem'])}")
            st.metric("% Parcelado", f"{linha['percentual_parcelado']:.1f}%")

    st.divider()
    st.markdown("**Gasto por período — Bradesco vs. Nubank**")
    st.altair_chart(_chart_comparacao_periodo(df, banco_scale), use_container_width=True)

    st.markdown("**Parcelado vs. Normal por banco**")
    st.altair_chart(_chart_comparacao_tipo(df, banco_scale), use_container_width=True)

    st.markdown("**Compromisso em parcelas abertas por banco**")
    aberto = metrics.parcelas_em_aberto(df)
    if aberto.empty:
        st.caption("Nenhuma parcela em aberto no momento.")
    else:
        resumo_aberto = aberto.groupby("Banco", as_index=False)["valor_restante"].sum()
        st.altair_chart(_chart_barras_por_banco(resumo_aberto, "valor_restante", banco_scale), use_container_width=True)


def _chart_comparacao_periodo(df: pd.DataFrame, banco_scale: alt.Scale) -> alt.Chart:
    dados = metrics.gasto_por_periodo(df)
    return (
        alt.Chart(dados)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Periodo:N", sort=_ordem_periodos(dados), title=None, axis=alt.Axis(grid=False, labelAngle=-30)),
            y=alt.Y("valor_total:Q", title=None, axis=alt.Axis(gridColor=_GRIDLINE)),
            color=alt.Color("Banco:N", scale=banco_scale, legend=alt.Legend(title=None)),
            xOffset="Banco:N",
            tooltip=[
                alt.Tooltip("Banco:N"), alt.Tooltip("Periodo:N", title="Período"),
                alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
            ],
        )
        .properties(height=280, width="container")
    )


def _chart_comparacao_tipo(df: pd.DataFrame, banco_scale: alt.Scale) -> alt.Chart:
    dados = df.groupby(["Banco", "Tipo"], as_index=False).agg(valor_total=("Valor", "sum"))
    return (
        alt.Chart(dados)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Banco:N", title=None),
            y=alt.Y("valor_total:Q", title=None, axis=alt.Axis(gridColor=_GRIDLINE)),
            color=alt.Color("Tipo:N", scale=_TIPO_SCALE, legend=alt.Legend(title=None)),
            xOffset="Tipo:N",
            tooltip=[
                alt.Tooltip("Banco:N"), alt.Tooltip("Tipo:N"),
                alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
            ],
        )
        .properties(height=280, width="container")
    )


def _chart_barras_por_banco(dados: pd.DataFrame, campo_valor: str, banco_scale: alt.Scale) -> alt.Chart:
    return (
        alt.Chart(dados)
        .mark_bar(cornerRadiusEnd=4, size=40)
        .encode(
            x=alt.X("Banco:N", title=None),
            y=alt.Y(f"{campo_valor}:Q", title=None, axis=alt.Axis(gridColor=_GRIDLINE)),
            color=alt.Color("Banco:N", scale=banco_scale, legend=None),
            tooltip=[alt.Tooltip("Banco:N"), alt.Tooltip(f"{campo_valor}:Q", title="Valor", format=",.2f")],
        )
        .properties(height=220, width="container")
    )
