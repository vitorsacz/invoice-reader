import gspread
import os
from google.oauth2.service_account import Credentials

def update_google_sheet(transactions: list, sheet_url: str):
    """
    Autentica no Google Sheets usando o credentials.json e 
    adiciona os novos lançamentos na primeira aba da planilha.
    """
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError("O arquivo credentials.json não foi encontrado na raiz do projeto.")

    # Escopos necessários para acessar o Drive e o Sheets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(credentials)

    # Abre a planilha pela URL
    sheet = client.open_by_url(sheet_url).sheet1

    # Prepara a lista de listas (linhas) para inserção em lote (mais rápido)
    rows_to_insert = []
    for t in transactions:
        rows_to_insert.append([t["data"], t["estabelecimento"], t["valor"]])

    # Faz o append dos dados na primeira linha vazia disponível
    if rows_to_insert:
        sheet.append_rows(rows_to_insert)
        print(f"{len(rows_to_insert)} transações inseridas com sucesso na planilha!")
    else:
        print("Nenhuma transação para inserir.")