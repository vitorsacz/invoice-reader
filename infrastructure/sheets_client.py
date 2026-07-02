import gspread
import os
from google.oauth2.service_account import Credentials

def update_google_sheet(transactions: list, sheet_url: str):
    """
    Abre a primeira aba da planilha e insere as transações.
    """
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(credentials)
    
    # Abre a planilha pela URL e seleciona a primeira aba padrão (Sheet1)
    sheet = client.open_by_url(sheet_url).sheet1

    # Preparação e inserção dos dados
    rows_to_insert = []
    for t in transactions:
        rows_to_insert.append([t["data"], t["estabelecimento"], t["valor"]])

    # Faz o append dos dados na primeira linha vazia disponível
    if rows_to_insert:
        sheet.append_rows(rows_to_insert)
        print(f"Sucesso: {len(rows_to_insert)} transações inseridas na planilha!")
    else:
        print("Nenhuma transação para inserir.")