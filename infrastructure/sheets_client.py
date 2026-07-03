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

    # Cria uma lista separada apenas com os itens parcelados
    parcelados = [t for t in transacoes if t.get("tipo") == "Parcelado"]

    # Calcula os sub-totais automaticamente
    total_normal = sum(float(t.get("valor", 0)) for t in transacoes if t.get("tipo") == "Normal")
    total_parcelado = sum(float(t.get("valor", 0)) for t in parcelados)

    # 1. Montando o cabeçalho estático (Linhas 1 a 5, cobrindo as colunas de A até K)
    linhas_para_inserir = [
        ["💳 Resumo da Fatura", "", "", "", "", "", "", "", "", "", ""],
        ["Banco:", banco, "", "", "", "", "VALORES PARCELADOS", "", "", "", ""],
        ["Valor Total:", total, "", "", "", "", "Valor Total:", total_parcelado, "", "", ""],
        ["VALORES NORMAIS", total_normal, "", "", "", "", "", "", "", "", ""],
        ["Data", "Estabelecimento", "Tipo", "Parcela", "Valor", "", "Data", "Estabelecimento", "Tipo", "Parcela", "Valor"]
    ]

    start_row = 6
    # Descobre qual lista é maior para garantir que o loop não corte dados
    max_len = max(len(transacoes), len(parcelados))
    
    # Montando as linhas de transação (lado a lado)
    for i in range(max_len):
        row = []
        
        # Construindo a Tabela da Esquerda (Geral)
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
            row.extend(["", "", "", "", ""]) # Preenchimento vazio se a lista acabar
        
        # Coluna F (Divisória em branco)
        row.append("")
        
        # Construindo a Tabela da Direita (Apenas Parcelados)
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
            row.extend(["", "", "", "", ""]) # Preenchimento vazio se a lista acabar
            
        linhas_para_inserir.append(row)

    # Dispara tudo de uma vez para a planilha (extremamente rápido e à prova de pulo de linhas)
    sheet.append_rows(linhas_para_inserir)
    end_row = len(linhas_para_inserir)

    # 2. Aplicando a formatação do Dashboard Duplo
    
    # Formatação do Resumo Principal (Esquerda)
    format_cell_range(sheet, "A1:E1", cellFormat(
        backgroundColor=color(0.1, 0.1, 0.5), # Azul Escuro
        textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=12)
    ))
    format_cell_range(sheet, "A2:A3", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(sheet, "B3", cellFormat(
        numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"),
        textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2)) # Vermelho
    ))
    
    format_cell_range(sheet, "A4:A4", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(sheet, "B4:B4", cellFormat(
        numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"),
        textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2))
    ))

    # Formatação do Resumo Secundário (Direita)
    format_cell_range(sheet, "G2:G3", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(sheet, "H3:H3", cellFormat(
        numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"),
        textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2))
    ))

    # Cabeçalhos das duas tabelas (Linha 5)
    header_format = cellFormat(
        backgroundColor=color(0.2, 0.2, 0.2), # Preto
        textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1))
    )
    format_cell_range(sheet, "A5:E5", header_format)
    format_cell_range(sheet, "G5:K5", header_format)

    # Formatação das linhas de dados
    if max_len > 0:
        # Alinhamentos da Tabela Principal
        format_cell_range(sheet, f"A{start_row}:A{end_row}", cellFormat(horizontalAlignment="CENTER"))
        format_cell_range(sheet, f"C{start_row}:D{end_row}", cellFormat(horizontalAlignment="CENTER"))
        format_cell_range(sheet, f"E{start_row}:E{end_row}", cellFormat(
            numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00")
        ))

        # Alinhamentos da Tabela de Parcelados
        if len(parcelados) > 0:
            fim_direita = start_row + len(parcelados) - 1
            format_cell_range(sheet, f"G{start_row}:G{fim_direita}", cellFormat(horizontalAlignment="CENTER"))
            format_cell_range(sheet, f"I{start_row}:J{fim_direita}", cellFormat(horizontalAlignment="CENTER"))
            format_cell_range(sheet, f"K{start_row}:K{fim_direita}", cellFormat(
                numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00")
            ))

        # Destacando de amarelo: Os parcelados da tabela principal...
        for i, t in enumerate(transacoes):
            current_row = start_row + i
            if t.get("tipo") == "Parcelado":
                format_cell_range(sheet, f"A{current_row}:E{current_row}", cellFormat(
                    backgroundColor=color(1.0, 0.95, 0.85)
                ))

        # ... e TODOS os itens da tabela da direita (já que todos lá são parcelados)
        if len(parcelados) > 0:
            format_cell_range(sheet, f"G{start_row}:K{fim_direita}", cellFormat(
                backgroundColor=color(1.0, 0.95, 0.85)
            ))

    # Definindo a largura correta das colunas
    # Esquerda
    set_column_width(sheet, 'A', 80)
    set_column_width(sheet, 'B', 250)
    set_column_width(sheet, 'C', 100)
    set_column_width(sheet, 'D', 80)
    set_column_width(sheet, 'E', 100)
    # Corredor
    set_column_width(sheet, 'F', 30)
    # Direita
    set_column_width(sheet, 'G', 80)
    set_column_width(sheet, 'H', 250)
    set_column_width(sheet, 'I', 100)
    set_column_width(sheet, 'J', 80)
    set_column_width(sheet, 'K', 100)

    print(f"Sucesso: Dashboard duplo atualizado com sucesso.")