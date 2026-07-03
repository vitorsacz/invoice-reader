import gspread
import os
from google.oauth2.service_account import Credentials
from gspread_formatting import (
    cellFormat, textFormat, color, numberFormat,
    format_cell_range, set_column_width
)

def update_google_sheet(dados_fatura: dict, sheet_url: str):
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(sheet_url).sheet1

    # Limpa a planilha para garantir que não haja restos de formatações antigas
    sheet.clear()

    banco = dados_fatura.get("banco", "Desconhecido")
    total = dados_fatura.get("valor_total", 0.0)
    transacoes = dados_fatura.get("transacoes", [])

    # 1. Montando TODO o payload na memória primeiro (Evita pular linhas)
    linhas_para_inserir = [
        ["💳 Resumo da Fatura", "", "", "", ""],      # Linha 1
        ["Banco:", banco, "", "", ""],               # Linha 2
        ["Valor Total:", total, "", "", ""],         # Linha 3
        [" ", " ", " ", " ", " "],                   # Linha 4 (Espaço em branco força a linha a existir)
        ["Data", "Estabelecimento", "Tipo", "Parcela", "Valor"] # Linha 5 (Cabeçalho)
    ]

    start_row = 6 # Garantimos que os dados sempre começarão na linha 6
    
    for t in transacoes:
        linhas_para_inserir.append([
            t.get("data", ""), 
            t.get("estabelecimento", ""), 
            t.get("tipo", ""), 
            t.get("parcela", "-"), 
            t.get("valor", 0.0)
        ])

    # Envia tudo de uma vez para o Google Sheets (mais performático)
    sheet.append_rows(linhas_para_inserir)
    end_row = len(linhas_para_inserir)

    # 2. Aplicando a formatação exata baseada nas linhas fixadas
    
    # Formatação do Resumo
    format_cell_range(sheet, "A1:E1", cellFormat(
        backgroundColor=color(0.1, 0.1, 0.5), # Azul escuro
        textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=12)
    ))
    format_cell_range(sheet, "A2:A3", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(sheet, "B3", cellFormat(
        numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"),
        textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2)) # Vermelho
    ))

    # Formatação do Cabeçalho da Tabela (Linha 5 garantida)
    format_cell_range(sheet, "A5:E5", cellFormat(
        backgroundColor=color(0.2, 0.2, 0.2), # Preto
        textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1))
    ))

    # Formatação dos Dados
    if len(transacoes) > 0:
        format_cell_range(sheet, f"A{start_row}:A{end_row}", cellFormat(horizontalAlignment="CENTER"))
        format_cell_range(sheet, f"C{start_row}:D{end_row}", cellFormat(horizontalAlignment="CENTER"))
        format_cell_range(sheet, f"E{start_row}:E{end_row}", cellFormat(
            numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00")
        ))

        # Destacando visualmente itens Parcelados com sincronia perfeita
        for i, t in enumerate(transacoes):
            current_row = start_row + i
            if t.get("tipo") == "Parcelado":
                format_cell_range(sheet, f"A{current_row}:E{current_row}", cellFormat(
                    backgroundColor=color(1.0, 0.95, 0.85) # Amarelo/Laranja claro
                ))

    # Ajuste das colunas
    set_column_width(sheet, 'A', 80)
    set_column_width(sheet, 'B', 250)
    set_column_width(sheet, 'C', 100)
    set_column_width(sheet, 'D', 80)
    set_column_width(sheet, 'E', 100)

    print(f"Sucesso: Planilha formatada com precisão.")