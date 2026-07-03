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
    spreadsheet = client.open_by_url(sheet_url)

    # Identifica o mês detectado pela IA e padroniza a primeira letra em maiúscula
    mes_fatura = dados_fatura.get("mes_fatura", "Fatura").capitalize()

    # Tenta abrir a aba do mês. Se não existir, cria uma nova.
    try:
        worksheet = spreadsheet.worksheet(mes_fatura)
        worksheet.clear() # Limpa se já existir para não duplicar dados
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=mes_fatura, rows="100", cols="15")

    banco = dados_fatura.get("banco", "Desconhecido")
    total = dados_fatura.get("valor_total", 0.0)
    transacoes = dados_fatura.get("transacoes", [])

    parcelados = [t for t in transacoes if t.get("tipo") == "Parcelado"]
    total_normal = sum(float(t.get("valor", 0)) for t in transacoes if t.get("tipo") == "Normal")
    total_parcelado = sum(float(t.get("valor", 0)) for t in parcelados)

    # 1. Montando o cabeçalho estático
    linhas_para_inserir = [
        ["💳 Resumo da Fatura", "", "", "", "", "", "", "", "", "", ""],
        ["Banco:", banco, "", "", "", "", "VALORES PARCELADOS", "", "", "", ""],
        ["Valor Total:", total, "", "", "", "", "Valor Total:", total_parcelado, "", "", ""],
        ["VALORES NORMAIS", total_normal, "", "", "", "", "", "", "", "", ""],
        ["Data", "Estabelecimento", "Tipo", "Parcela", "Valor", "", "Data", "Estabelecimento", "Tipo", "Parcela", "Valor"]
    ]

    start_row = 6
    max_len = max(len(transacoes), len(parcelados))
    
    # Montando as linhas de transação (lado a lado)
    for i in range(max_len):
        row = []
        
        if i < len(transacoes):
            t = transacoes[i]
            row.extend([
                t.get("data", ""), 
                t.get("estabelecimento", ""), 
                t.get("tipo", ""), 
                t.get("parcela", "-"), 
                float(t.get("valor", 0.0))
            ])
        else:
            row.extend(["", "", "", "", ""]) 
        
        row.append("") # Divisória
        
        if i < len(parcelados):
            p = parcelados[i]
            row.extend([
                p.get("data", ""), 
                p.get("estabelecimento", ""), 
                p.get("tipo", ""), 
                p.get("parcela", "-"), 
                float(p.get("valor", 0.0))
            ])
        else:
            row.extend(["", "", "", "", ""]) 
            
        linhas_para_inserir.append(row)

    worksheet.append_rows(linhas_para_inserir)
    end_row = len(linhas_para_inserir)

    # 2. Aplicando a formatação visual
    format_cell_range(worksheet, "A1:E1", cellFormat(
        backgroundColor=color(0.1, 0.1, 0.5), 
        textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=12)
    ))
    format_cell_range(worksheet, "A2:A3", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(worksheet, "B3", cellFormat(
        numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"),
        textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2)) 
    ))
    
    format_cell_range(worksheet, "A4:A4", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(worksheet, "B4:B4", cellFormat(
        numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"),
        textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2))
    ))

    format_cell_range(worksheet, "G2:G3", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(worksheet, "H3:H3", cellFormat(
        numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"),
        textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2))
    ))

    header_format = cellFormat(
        backgroundColor=color(0.2, 0.2, 0.2), 
        textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1))
    )
    format_cell_range(worksheet, "A5:E5", header_format)
    format_cell_range(worksheet, "G5:K5", header_format)

    if max_len > 0:
        format_cell_range(worksheet, f"A{start_row}:A{end_row}", cellFormat(horizontalAlignment="CENTER"))
        format_cell_range(worksheet, f"C{start_row}:D{end_row}", cellFormat(horizontalAlignment="CENTER"))
        format_cell_range(worksheet, f"E{start_row}:E{end_row}", cellFormat(
            numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00")
        ))

        if len(parcelados) > 0:
            fim_direita = start_row + len(parcelados) - 1
            format_cell_range(worksheet, f"G{start_row}:G{fim_direita}", cellFormat(horizontalAlignment="CENTER"))
            format_cell_range(worksheet, f"I{start_row}:J{fim_direita}", cellFormat(horizontalAlignment="CENTER"))
            format_cell_range(worksheet, f"K{start_row}:K{fim_direita}", cellFormat(
                numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00")
            ))

        for i, t in enumerate(transacoes):
            current_row = start_row + i
            if t.get("tipo") == "Parcelado":
                format_cell_range(worksheet, f"A{current_row}:E{current_row}", cellFormat(
                    backgroundColor=color(1.0, 0.95, 0.85)
                ))

        if len(parcelados) > 0:
            format_cell_range(worksheet, f"G{start_row}:K{fim_direita}", cellFormat(
                backgroundColor=color(1.0, 0.95, 0.85)
            ))

    set_column_width(worksheet, 'A', 80)
    set_column_width(worksheet, 'B', 250)
    set_column_width(worksheet, 'C', 100)
    set_column_width(worksheet, 'D', 80)
    set_column_width(worksheet, 'E', 100)
    set_column_width(worksheet, 'F', 30)
    set_column_width(worksheet, 'G', 80)
    set_column_width(worksheet, 'H', 250)
    set_column_width(worksheet, 'I', 100)
    set_column_width(worksheet, 'J', 80)
    set_column_width(worksheet, 'K', 100)

    # =========================================================================
    # 3. ORDENAÇÃO CRONOLÓGICA DAS ABAS
    # =========================================================================
    mapa_meses = {
        "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Marco": 3, "Abril": 4,
        "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
        "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
    }

    try:
        todas_abas = spreadsheet.worksheets()
        
        # A função key verifica se a aba atual está no nosso dicionário.
        # Se for um mês reconhecido, recebe o número correspondente (1 a 12).
        # Se for um nome desconhecido (como "Sheet1"), recebe peso 99 e vai pro final.
        todas_abas.sort(key=lambda ws: mapa_meses.get(ws.title.capitalize(), 99))
        
        # Dispara o comando para o Google Sheets rearranjar a barra inferior
        spreadsheet.reorder_worksheets(todas_abas)
        print("Abas organizadas cronologicamente com sucesso!")
    except Exception as e:
        print(f"Aviso: Não foi possível reordenar as abas: {e}")