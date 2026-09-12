from datetime import date

import pandas as pd


def filtrar_por_banco(df: pd.DataFrame, bancos: list[str] | None) -> pd.DataFrame:
    if not bancos:
        return df
    return df[df["Banco"].isin(bancos)]


def filtrar_por_periodo(df: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    if inicio is None or fim is None:
        return df
    return df[(df["PeriodoData"] >= pd.Timestamp(inicio)) & (df["PeriodoData"] <= pd.Timestamp(fim))]


def filtrar_por_tipo(df: pd.DataFrame, tipos: list[str] | None) -> pd.DataFrame:
    if not tipos:
        return df
    return df[df["Tipo"].isin(tipos)]


def aplicar_filtros(
    df: pd.DataFrame,
    bancos: list[str] | None = None,
    periodo_range: tuple[date, date] | None = None,
    tipos: list[str] | None = None,
) -> pd.DataFrame:
    resultado = filtrar_por_banco(df, bancos)
    if periodo_range:
        resultado = filtrar_por_periodo(resultado, periodo_range[0], periodo_range[1])
    resultado = filtrar_por_tipo(resultado, tipos)
    return resultado
