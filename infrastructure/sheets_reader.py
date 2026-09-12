import gspread
import pandas as pd

from core.models import HEADER_CATEGORIAS, HEADER_DB_TRANSACOES, parse_valor_brl, periodo_para_data
from infrastructure.sheets_client import get_gspread_client


def fetch_transacoes_df(sheet_url: str) -> pd.DataFrame:
    """Le a aba DB_Transacoes e devolve um DataFrame tratado.

    O header vivo da planilha e ignorado (ja foi corrompido/zerado no
    passado - ver sheets_client.py) - as colunas sao sempre remontadas
    a partir do schema canonico em core.models.
    """
    client = get_gspread_client()
    spreadsheet = client.open_by_url(sheet_url)

    try:
        db_sheet = spreadsheet.worksheet("DB_Transacoes")
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame(columns=HEADER_DB_TRANSACOES + ["PeriodoData"])

    linhas = db_sheet.get_all_values()
    dados = linhas[1:] if len(linhas) > 1 else []
    df = pd.DataFrame(dados, columns=HEADER_DB_TRANSACOES)

    df["Valor"] = df["Valor"].apply(parse_valor_brl)
    df["PeriodoData"] = pd.to_datetime(df["Periodo"].apply(periodo_para_data))
    df = df.dropna(subset=["PeriodoData"])

    return df.sort_values("PeriodoData").reset_index(drop=True)


def fetch_categorias_df(sheet_url: str) -> pd.DataFrame:
    """Le a aba Categorias (Estabelecimento -> Categoria). Vazia/ausente
    a aba -> DataFrame vazio, tratado como 'tudo Nao categorizado' por
    core.categorias.aplicar_categorias."""
    client = get_gspread_client()
    spreadsheet = client.open_by_url(sheet_url)

    try:
        cat_sheet = spreadsheet.worksheet("Categorias")
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame(columns=HEADER_CATEGORIAS)

    linhas = cat_sheet.get_all_values()
    dados = linhas[1:] if len(linhas) > 1 else []
    return pd.DataFrame(dados, columns=HEADER_CATEGORIAS)
