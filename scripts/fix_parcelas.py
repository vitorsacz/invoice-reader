"""
Corrige a coluna "Parcela" na aba DB_Transacoes.

Diagnostico: ao gravar com value_input_option="USER_ENTERED", o Google
Sheets interpretou valores como "07/12" como DATA em vez de texto. O
valor por tras da celula virou um numero serial de data (ex: 46215),
mas o Sheets aplicou automaticamente um formato de data numa celula que
reproduz visualmente o texto original ("07/12") na propria aba
DB_Transacoes - por isso lá parece correto.

O problema aparece no dashboard de cada banco, porque a formula FILTER()
copia o VALOR (o numero serial da data), e a celula de destino nao tem
esse mesmo formato de data aplicado, entao o Google Sheets exibe o
numero serial cru (ex: 46058) em vez de "07/12".

Este script varre DB_Transacoes, identifica celulas de Parcela cujo
valor bruto (unformatted) e numerico (ou seja, viraram data), usa o
proprio valor formatado pelo Sheets (que ja e igual ao "X/Y" original)
para reescrever a celula como TEXTO literal via value_input_option=RAW,
eliminando o problema definitivamente.

Uso:
    python scripts/fix_parcelas.py            # dry-run, so mostra o que mudaria
    python scripts/fix_parcelas.py --apply    # aplica as correcoes na planilha
"""
import os
import re
import sys
import argparse
from datetime import date, timedelta

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

SHEETS_EPOCH = date(1899, 12, 30)
PARCELA_OK_RE = re.compile(r"^\d{1,2}/\d{1,2}$")
COL_PARCELA_PADRAO = 5  # indice 0-based da coluna "Parcela" no schema de DB_Transacoes


def serial_para_parcela_fallback(serial: float):
    """Reconstroi 'X/Y' a partir do serial de data, usado só como conferência
    quando o valor formatado pelo Sheets não vier no padrão esperado."""
    d = SHEETS_EPOCH + timedelta(days=int(serial))
    return f"{d.month:02d}/{d.day:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Grava as correcoes na planilha (sem essa flag, so mostra o que seria feito).")
    args = parser.parse_args()

    load_dotenv()
    sheet_url = os.getenv("SPREADSHEET_URL")
    if not sheet_url:
        print("SPREADSHEET_URL nao encontrado no .env")
        sys.exit(1)

    credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(sheet_url)

    db_sheet = spreadsheet.worksheet("DB_Transacoes")

    raw_values = db_sheet.get_values(value_render_option="UNFORMATTED_VALUE")
    fmt_values = db_sheet.get_values(value_render_option="FORMATTED_VALUE")

    if not raw_values:
        print("Planilha DB_Transacoes vazia.")
        return

    header = fmt_values[0]
    col_parcela = header.index("Parcela") if "Parcela" in header else COL_PARCELA_PADRAO
    if "Parcela" not in header:
        print(f"[AVISO] Cabecalho da planilha esta vazio/invalido. Usando coluna F (indice {COL_PARCELA_PADRAO}) pelo schema padrao.")

    correcoes = []  # (linha_1based, valor_antigo_raw, valor_novo)

    for i in range(1, len(raw_values)):
        raw_row = raw_values[i]
        fmt_row = fmt_values[i] if i < len(fmt_values) else []

        if col_parcela >= len(raw_row):
            continue

        raw_valor = raw_row[col_parcela]
        fmt_valor = fmt_row[col_parcela].strip() if col_parcela < len(fmt_row) else ""

        # Ja e texto (string) -> nao foi interpretado como data, esta ok
        if isinstance(raw_valor, str):
            valor_str = raw_valor.strip()
            if valor_str == "" or valor_str == "-" or PARCELA_OK_RE.match(valor_str):
                continue
            print(f"[AVISO] Linha {i + 1}: valor de texto '{valor_str}' fora do padrao 'X/Y'. Ignorado.")
            continue

        # Valor bruto numerico -> foi convertido em data pelo Sheets
        if isinstance(raw_valor, (int, float)):
            if PARCELA_OK_RE.match(fmt_valor):
                novo_valor = fmt_valor
            else:
                novo_valor = serial_para_parcela_fallback(raw_valor)
                print(f"[AVISO] Linha {i + 1}: valor formatado '{fmt_valor}' fora do padrao esperado; usando reconstrucao por serial: '{novo_valor}'.")
            correcoes.append((i + 1, raw_valor, novo_valor))

    if not correcoes:
        print("Nenhuma parcela corrompida encontrada.")
        return

    print(f"{len(correcoes)} parcela(s) corrompida(s) encontrada(s):\n")
    for linha_idx, antigo, novo in correcoes:
        print(f"  Linha {linha_idx}: {antigo!r} -> '{novo}'")

    if not args.apply:
        print("\nDry-run: nada foi alterado. Rode com --apply para gravar as correcoes.")
        return

    col_letra = gspread.utils.rowcol_to_a1(1, col_parcela + 1)[:-1]  # letra da coluna
    updates = [
        {"range": f"{col_letra}{linha_idx}", "values": [[novo]]}
        for linha_idx, _, novo in correcoes
    ]
    db_sheet.batch_update(updates, value_input_option="RAW")
    print(f"\n{len(correcoes)} celula(s) corrigida(s) na planilha.")


if __name__ == "__main__":
    main()
