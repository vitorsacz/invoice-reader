import re

import pandas as pd

_PARCELA_RE = re.compile(r"^(\d+)/(\d+)$")


def total_gasto(df: pd.DataFrame) -> float:
    return float(df["Valor"].sum())


def ticket_medio(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(df["Valor"].mean())


def resumo_por_tipo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Tipo", "valor_total", "contagem", "percentual"])

    resumo = df.groupby("Tipo", as_index=False).agg(
        valor_total=("Valor", "sum"), contagem=("Valor", "count")
    )
    total = resumo["valor_total"].sum()
    resumo["percentual"] = (resumo["valor_total"] / total * 100) if total else 0.0
    return resumo


def gasto_por_periodo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Banco", "Periodo", "PeriodoData", "valor_total"])

    return df.groupby(["Banco", "Periodo", "PeriodoData"], as_index=False).agg(
        valor_total=("Valor", "sum")
    ).sort_values("PeriodoData")


def top_estabelecimentos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Estabelecimento", "valor_total"])

    resumo = df.groupby("Estabelecimento", as_index=False).agg(valor_total=("Valor", "sum"))
    return resumo.sort_values("valor_total", ascending=False).head(n)


def resumo_por_banco(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Banco", "valor_total", "contagem", "percentual_parcelado"])

    resumo = df.groupby("Banco", as_index=False).agg(
        valor_total=("Valor", "sum"), contagem=("Valor", "count")
    )
    parcelado = df[df["Tipo"] == "Parcelado"].groupby("Banco")["Valor"].sum()
    resumo["percentual_parcelado"] = resumo["Banco"].map(
        lambda b: (parcelado.get(b, 0.0) / resumo.loc[resumo["Banco"] == b, "valor_total"].iloc[0] * 100)
        if resumo.loc[resumo["Banco"] == b, "valor_total"].iloc[0] else 0.0
    )
    return resumo


def delta_periodo_anterior(
    df_sem_filtro_periodo: pd.DataFrame, periodo_range: tuple
) -> tuple[float, float | None]:
    """Retorna (total_atual, total_anterior | None).

    Compara o total do intervalo selecionado contra a janela imediatamente
    anterior de mesmo tamanho. Se nao houver historico suficiente antes da
    janela, o anterior vem como None (o KPI e exibido sem delta).
    """
    inicio, fim = periodo_range
    atual = df_sem_filtro_periodo[
        (df_sem_filtro_periodo["PeriodoData"] >= pd.Timestamp(inicio))
        & (df_sem_filtro_periodo["PeriodoData"] <= pd.Timestamp(fim))
    ]
    total_atual = float(atual["Valor"].sum())

    duracao = pd.Timestamp(fim) - pd.Timestamp(inicio)
    fim_anterior = pd.Timestamp(inicio) - pd.DateOffset(months=1)
    inicio_anterior = fim_anterior - duracao

    anterior = df_sem_filtro_periodo[
        (df_sem_filtro_periodo["PeriodoData"] >= inicio_anterior)
        & (df_sem_filtro_periodo["PeriodoData"] <= fim_anterior)
    ]
    if anterior.empty:
        return total_atual, None

    return total_atual, float(anterior["Valor"].sum())


def resumo_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Categoria", "valor_total", "contagem", "percentual"])

    resumo = df.groupby("Categoria", as_index=False).agg(
        valor_total=("Valor", "sum"), contagem=("Valor", "count")
    )
    total = resumo["valor_total"].sum()
    resumo["percentual"] = (resumo["valor_total"] / total * 100) if total else 0.0
    return resumo.sort_values("valor_total", ascending=False)


def gasto_por_periodo_categoria(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Periodo", "PeriodoData", "Categoria", "valor_total"])

    return df.groupby(["Periodo", "PeriodoData", "Categoria"], as_index=False).agg(
        valor_total=("Valor", "sum")
    ).sort_values("PeriodoData")


def nao_categorizados(df: pd.DataFrame) -> pd.DataFrame:
    pendentes = df[df["Categoria"] == "Não categorizado"]
    if pendentes.empty:
        return pd.DataFrame(columns=["Estabelecimento", "valor_total", "contagem"])

    resumo = pendentes.groupby("Estabelecimento", as_index=False).agg(
        valor_total=("Valor", "sum"), contagem=("Valor", "count")
    )
    return resumo.sort_values("valor_total", ascending=False)


def parcelas_em_aberto(df: pd.DataFrame) -> pd.DataFrame:
    """Estima o compromisso futuro de compras parceladas ainda nao quitadas.

    Cada linha registra a parcela vigente na epoca daquela fatura - parcelas
    futuras (X+1 ate Y) so aparecem quando a fatura daquele mes for
    processada. Agrupamos por (Banco, Estabelecimento, Valor, total Y) como
    identificador aproximado da mesma compra parcelada (nao ha ID de compra
    na fonte de dados), pegamos a maior parcela ja vista (X) e projetamos o
    valor restante. Limitacao conhecida: duas compras diferentes do mesmo
    estabelecimento, com o mesmo valor e total de parcelas, seriam fundidas
    num unico grupo.
    """
    colunas = ["Banco", "Estabelecimento", "Valor", "parcela_atual", "parcelas_totais",
               "parcelas_restantes", "valor_restante", "ultima_parcela_vista"]
    parcelados = df[df["Tipo"] == "Parcelado"].copy()
    if parcelados.empty:
        return pd.DataFrame(columns=colunas)

    extraido = parcelados["Parcela"].str.extract(_PARCELA_RE)
    parcelados = parcelados[extraido[0].notna()].copy()
    if parcelados.empty:
        return pd.DataFrame(columns=colunas)

    parcelados["parcela_atual"] = extraido.loc[parcelados.index, 0].astype(int)
    parcelados["parcelas_totais"] = extraido.loc[parcelados.index, 1].astype(int)

    grupos = parcelados.groupby(
        ["Banco", "Estabelecimento", "Valor", "parcelas_totais"], as_index=False
    ).agg(parcela_atual=("parcela_atual", "max"))

    grupos["parcelas_restantes"] = grupos["parcelas_totais"] - grupos["parcela_atual"]
    grupos = grupos[grupos["parcelas_restantes"] > 0].copy()
    grupos["valor_restante"] = grupos["parcelas_restantes"] * grupos["Valor"]
    grupos["ultima_parcela_vista"] = grupos["parcela_atual"].astype(str) + "/" + grupos["parcelas_totais"].astype(str)

    return grupos.sort_values("valor_restante", ascending=False)[colunas]
