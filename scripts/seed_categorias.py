"""
Popula/atualiza a aba "Categorias" (Estabelecimento -> Categoria) na
planilha com base nos estabelecimentos que ja existem em DB_Transacoes.

So ADICIONA estabelecimentos que ainda nao estao na aba Categorias -
nunca sobrescreve uma categoria ja preenchida manualmente. A categoria
sugerida usa a heuristica de palavras-chave em core/categorias.py; o
que ela nao reconhece vem marcado como "Nao categorizado" para revisao
manual direto na planilha.

Uso:
    python scripts/seed_categorias.py            # dry-run, so mostra o que mudaria
    python scripts/seed_categorias.py --apply    # aplica as novas linhas na planilha
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
import gspread
from gspread_formatting import cellFormat, textFormat, format_cell_range

from core.categorias import sugerir_categoria
from core.models import HEADER_CATEGORIAS
from infrastructure.sheets_client import get_gspread_client
from infrastructure.sheets_reader import fetch_categorias_df, fetch_transacoes_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Grava as novas linhas na planilha (sem essa flag, so mostra o que seria feito).")
    args = parser.parse_args()

    load_dotenv()
    sheet_url = os.getenv("SPREADSHEET_URL")
    if not sheet_url:
        print("SPREADSHEET_URL nao encontrado no .env")
        sys.exit(1)

    transacoes = fetch_transacoes_df(sheet_url)
    if transacoes.empty:
        print("DB_Transacoes vazia - nada para categorizar.")
        return

    categorias_existentes = fetch_categorias_df(sheet_url)
    ja_mapeados = set(categorias_existentes["Estabelecimento"])

    estabelecimentos = sorted(transacoes["Estabelecimento"].unique())
    novos = [e for e in estabelecimentos if e not in ja_mapeados]

    if not novos:
        print("Nenhum estabelecimento novo - a aba Categorias ja cobre tudo que existe em DB_Transacoes.")
        return

    linhas_novas = [(estab, sugerir_categoria(estab)) for estab in novos]

    print(f"{len(linhas_novas)} estabelecimento(s) novo(s) para adicionar na aba Categorias:\n")
    for estab, cat in linhas_novas:
        print(f"  {estab!r} -> {cat}")

    if not args.apply:
        print("\nDry-run: nada foi alterado. Rode com --apply para gravar na planilha.")
        return

    client = get_gspread_client()
    spreadsheet = client.open_by_url(sheet_url)

    try:
        cat_sheet = spreadsheet.worksheet("Categorias")
    except gspread.exceptions.WorksheetNotFound:
        cat_sheet = spreadsheet.add_worksheet(title="Categorias", rows="1000", cols="2")
        cat_sheet.append_row(HEADER_CATEGORIAS)
        format_cell_range(cat_sheet, "A1:B1", cellFormat(textFormat=textFormat(bold=True)))

    # RAW (nao USER_ENTERED): nomes de estabelecimento nao devem ser
    # interpretados como formula/data/numero - ja tivemos esse bug com a
    # coluna Parcela em DB_Transacoes (ver scripts/fix_parcelas.py).
    cat_sheet.append_rows([list(linha) for linha in linhas_novas], value_input_option="RAW")
    print(f"\n{len(linhas_novas)} linha(s) adicionada(s) na aba Categorias.")


if __name__ == "__main__":
    main()
