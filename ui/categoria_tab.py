import altair as alt
import pandas as pd
import streamlit as st

from core import filters, metrics
from core.categorias import NAO_CATEGORIZADO, aplicar_categorias
from ui.shared import CATEGORICAL_HUES, GRIDLINE, carregar_categorias, carregar_dados, formatar_moeda

_HUE_NAO_CATEGORIZADO = "#898781"  # cinza neutro - nao e uma categoria real, e um sinalizador de dado incompleto
_HUE_OUTRAS = "#c3c2b7"
_MAX_CATEGORIAS_COLORIDAS = len(CATEGORICAL_HUES)  # acima disso, o excedente dobra para "Outras"
_OUTRAS = "Outras"


def render_categoria_tab(sheet_url: str) -> None:
    st.title("🥧 Por Categoria")
    st.caption("Participação dos gastos por área (Alimentação, Saúde, Transporte...). A categoria de cada estabelecimento vem da aba \"Categorias\" na planilha.")

    df_transacoes = carregar_dados(sheet_url)
    if df_transacoes.empty:
        st.info("Nenhuma transação encontrada na planilha ainda.")
        return

    df_categorias = carregar_categorias(sheet_url)
    df = aplicar_categorias(df_transacoes, df_categorias)

    todos_bancos = sorted(df["Banco"].unique())

    col_banco, col_periodo = st.columns([2, 3])
    with col_banco:
        bancos_sel = st.multiselect("Banco", todos_bancos, default=todos_bancos, key="cat_banco")
    with col_periodo:
        opcoes_periodo = _periodo_options(df)
        periodo_ini, periodo_fim = st.select_slider(
            "Período",
            options=opcoes_periodo,
            value=(opcoes_periodo[0], opcoes_periodo[-1]),
            key="cat_periodo",
        )

    mapa_periodo_data = dict(zip(df["Periodo"], df["PeriodoData"]))
    range_datas = (mapa_periodo_data[periodo_ini].date(), mapa_periodo_data[periodo_fim].date())

    df_banco = filters.filtrar_por_banco(df, bancos_sel)
    df_filtrado = filters.filtrar_por_periodo(df_banco, *range_datas)

    if df_filtrado.empty:
        st.warning("Nenhuma transação encontrada para os filtros selecionados.")
        return

    resumo_cat_bruto = metrics.resumo_por_categoria(df_filtrado)
    categorias_coloridas, escala = _escala_categorias(resumo_cat_bruto)
    resumo_cat = _fundir_cauda_resumo(resumo_cat_bruto, categorias_coloridas)

    _render_kpis(df_filtrado, resumo_cat)
    st.divider()

    col_donut, col_meter = st.columns([1, 1])
    with col_donut:
        st.markdown("**Participação por categoria**")
        st.altair_chart(_chart_donut(resumo_cat, escala), use_container_width=True)
    with col_meter:
        st.markdown("**% do total por categoria**")
        st.altair_chart(_chart_meter(resumo_cat, escala), use_container_width=True)

    st.markdown("**Gasto mensal por categoria**")
    df_mensal = _remapear_categoria_para_outras(df_filtrado, categorias_coloridas)
    st.altair_chart(_chart_mensal(df_mensal, escala), use_container_width=True)

    st.divider()
    _render_detalhamento(df_filtrado)

    st.divider()
    _render_nao_categorizados(df_filtrado)


def _periodo_options(df: pd.DataFrame) -> list[str]:
    return (
        df[["Periodo", "PeriodoData"]]
        .drop_duplicates()
        .sort_values("PeriodoData")["Periodo"]
        .tolist()
    )


def _escala_categorias(resumo_cat: pd.DataFrame) -> tuple[list[str], alt.Scale]:
    """Ordena categorias por valor (maior primeiro), reserva um slot fixo e
    neutro para 'Nao categorizado', e dobra o excedente alem do numero de
    cores validadas em 'Outras' - nunca gera uma cor nova."""
    reais = [c for c in resumo_cat["Categoria"] if c != NAO_CATEGORIZADO]
    coloridas = reais[:_MAX_CATEGORIAS_COLORIDAS]

    domain = list(coloridas)
    range_ = list(CATEGORICAL_HUES[: len(coloridas)])

    if len(reais) > len(coloridas):
        domain.append(_OUTRAS)
        range_.append(_HUE_OUTRAS)

    if NAO_CATEGORIZADO in resumo_cat["Categoria"].values:
        domain.append(NAO_CATEGORIZADO)
        range_.append(_HUE_NAO_CATEGORIZADO)

    return coloridas, alt.Scale(domain=domain, range=range_)


def _remapear_categoria_para_outras(df: pd.DataFrame, categorias_coloridas: list[str]) -> pd.DataFrame:
    """Para DataFrame em nivel de transacao: categorias fora do top colorido
    (e diferentes de Nao categorizado) viram 'Outras'."""
    ajustado = df.copy()
    mascara = (~ajustado["Categoria"].isin(categorias_coloridas)) & (ajustado["Categoria"] != NAO_CATEGORIZADO)
    ajustado.loc[mascara, "Categoria"] = _OUTRAS
    return ajustado


def _fundir_cauda_resumo(resumo_cat: pd.DataFrame, categorias_coloridas: list[str]) -> pd.DataFrame:
    """Para o resumo ja agregado (resumo_por_categoria): funde as linhas da
    cauda (fora do top colorido) numa unica linha 'Outras'."""
    mascara = (~resumo_cat["Categoria"].isin(categorias_coloridas)) & (resumo_cat["Categoria"] != NAO_CATEGORIZADO)
    if not mascara.any():
        return resumo_cat

    principais = resumo_cat[~mascara]
    cauda = resumo_cat[mascara]
    linha_outras = pd.DataFrame([{
        "Categoria": _OUTRAS,
        "valor_total": cauda["valor_total"].sum(),
        "contagem": cauda["contagem"].sum(),
        "percentual": cauda["percentual"].sum(),
    }])
    return pd.concat([principais, linha_outras], ignore_index=True).sort_values("valor_total", ascending=False)


def _render_kpis(df_filtrado: pd.DataFrame, resumo_cat: pd.DataFrame) -> None:
    total = metrics.total_gasto(df_filtrado)
    top = resumo_cat.iloc[0] if not resumo_cat.empty else None
    pendentes = df_filtrado[df_filtrado["Categoria"] == NAO_CATEGORIZADO]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total no período", formatar_moeda(total))
    if top is not None:
        col2.metric(f"Maior categoria: {top['Categoria']}", formatar_moeda(top["valor_total"]))
    col3.metric(
        "Não categorizados", f"{len(pendentes)} transações",
        formatar_moeda(pendentes["Valor"].sum()), delta_color="off",
    )


def _chart_donut(resumo_cat: pd.DataFrame, escala: alt.Scale) -> alt.Chart:
    return (
        alt.Chart(resumo_cat)
        .mark_arc(innerRadius=60, cornerRadius=3)
        .encode(
            theta=alt.Theta("valor_total:Q"),
            color=alt.Color("Categoria:N", scale=escala, legend=alt.Legend(title=None)),
            order=alt.Order("valor_total:Q", sort="descending"),
            tooltip=[
                alt.Tooltip("Categoria:N"),
                alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
                alt.Tooltip("percentual:Q", title="%", format=".1f"),
            ],
        )
        .properties(height=300, width="container")
    )


def _chart_meter(resumo_cat: pd.DataFrame, escala: alt.Scale) -> alt.Chart:
    dados = resumo_cat.assign(cem=100)
    base = alt.Chart(dados).encode(y=alt.Y("Categoria:N", sort="-x", title=None))

    trilho = base.mark_bar(cornerRadiusEnd=4, size=14, color=GRIDLINE).encode(
        x=alt.X("cem:Q", title=None, axis=None, scale=alt.Scale(domain=[0, 100])),
    )
    preenchido = base.mark_bar(cornerRadiusEnd=4, size=14).encode(
        x=alt.X("percentual:Q", title=None, axis=None, scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("Categoria:N", scale=escala, legend=None),
        tooltip=[
            alt.Tooltip("Categoria:N"),
            alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
            alt.Tooltip("percentual:Q", title="%", format=".1f"),
        ],
    )
    rotulo = base.transform_calculate(rotulo_texto="format(datum.percentual, '.0f') + '%'").mark_text(
        align="left", dx=6, color="#c3c2b7",
    ).encode(
        x=alt.X("percentual:Q"),
        text=alt.Text("rotulo_texto:N"),
    )

    return (trilho + preenchido + rotulo).properties(height=280, width="container")


def _chart_mensal(df: pd.DataFrame, escala: alt.Scale) -> alt.Chart:
    dados = metrics.gasto_por_periodo_categoria(df)
    ordem_periodos = (
        dados[["Periodo", "PeriodoData"]].drop_duplicates().sort_values("PeriodoData")["Periodo"].tolist()
    )
    return (
        alt.Chart(dados)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Periodo:N", sort=ordem_periodos, title=None, axis=alt.Axis(grid=False, labelAngle=-30)),
            y=alt.Y("valor_total:Q", title=None, axis=alt.Axis(gridColor=GRIDLINE)),
            color=alt.Color("Categoria:N", scale=escala, legend=alt.Legend(title=None)),
            order=alt.Order("valor_total:Q", sort="descending"),
            tooltip=[
                alt.Tooltip("Periodo:N", title="Período"),
                alt.Tooltip("Categoria:N"),
                alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
            ],
        )
        .properties(height=300, width="container")
    )


def _render_detalhamento(df_filtrado: pd.DataFrame) -> None:
    st.markdown("**Detalhamento por categoria**")
    categorias_disponiveis = sorted(df_filtrado["Categoria"].unique())
    if not categorias_disponiveis:
        return

    col_lista, col_grafico = st.columns([1, 3])
    with col_lista:
        categoria_sel = st.radio("Categoria", categorias_disponiveis, key="cat_detalhe")
    with col_grafico:
        df_categoria = df_filtrado[df_filtrado["Categoria"] == categoria_sel]
        top = metrics.top_estabelecimentos(df_categoria, n=10)
        if top.empty:
            st.caption("Sem transações nessa categoria para os filtros atuais.")
        else:
            chart = (
                alt.Chart(top)
                .mark_bar(cornerRadiusEnd=4, size=18, color=CATEGORICAL_HUES[0])
                .encode(
                    x=alt.X("valor_total:Q", title=None, axis=alt.Axis(gridColor=GRIDLINE)),
                    y=alt.Y("Estabelecimento:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
                    tooltip=[
                        alt.Tooltip("Estabelecimento:N"),
                        alt.Tooltip("valor_total:Q", title="Valor", format=",.2f"),
                    ],
                )
                .properties(height=320, width="container")
            )
            st.altair_chart(chart, use_container_width=True)


def _render_nao_categorizados(df_filtrado: pd.DataFrame) -> None:
    pendentes = metrics.nao_categorizados(df_filtrado)
    st.markdown(f"**⚠️ Não categorizados** ({len(pendentes)})")
    if pendentes.empty:
        st.caption("Tudo categorizado para os filtros atuais.")
        return

    st.caption("Adicione esses estabelecimentos na aba \"Categorias\" da planilha para refinar a análise.")
    st.dataframe(
        pendentes.rename(columns={"valor_total": "Valor total", "contagem": "Transações"}),
        use_container_width=True,
        hide_index=True,
        column_config={"Valor total": st.column_config.NumberColumn(format="R$ %.2f")},
    )
