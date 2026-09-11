import gspread
import os
from google.oauth2.service_account import Credentials
from gspread_formatting import (
    cellFormat, textFormat, color, numberFormat,
    format_cell_range, set_column_width,
    DataValidationRule, BooleanCondition, set_data_validation_for_cell_range
)

HEADER_DB_TRANSACOES = ["Banco", "Periodo", "Data", "Estabelecimento", "Tipo", "Parcela", "Valor"]


def update_google_sheet(dados_fatura: dict, sheet_url: str):
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(sheet_url)

    # 1. Metadados Padronizados
    banco = dados_fatura.get("banco", "Desconhecido").strip().capitalize()
    mes = dados_fatura.get("mes_fatura", "janeiro").strip().capitalize()
    ano = dados_fatura.get("ano_fatura", 2026)
    periodo = f"{mes}/{ano}"
    transacoes = dados_fatura.get("transacoes", [])

    # =========================================================================
    # FASE 1: O BANCO DE DADOS CENTRAL (DB_Transacoes)
    # =========================================================================
    try:
        db_sheet = spreadsheet.worksheet("DB_Transacoes")
    except gspread.exceptions.WorksheetNotFound:
        db_sheet = spreadsheet.add_worksheet(title="DB_Transacoes", rows="1000", cols="7")
        db_sheet.append_row(HEADER_DB_TRANSACOES)
        format_cell_range(db_sheet, "A1:G1", cellFormat(textFormat=textFormat(bold=True)))

    todos_registros = db_sheet.get_all_values()
    # O cabecalho e sempre reescrito com o valor canonico (nunca reaproveitado de
    # todos_registros[0]) para nao perpetuar um cabecalho vazio/corrompido indefinidamente.
    linhas_filtradas = [HEADER_DB_TRANSACOES]

    # Conjunto para rastrear quais meses esse banco já tem (para criarmos o Dropdown)
    periodos_deste_banco = set([periodo])

    for linha in todos_registros[1:]:
        if len(linha) >= 7:
            linha_banco = str(linha[0]).strip()
            linha_periodo = str(linha[1]).strip()
            
            if linha_banco.lower() == banco.lower() and linha_periodo.lower() == periodo.lower():
                continue 
            
            if linha_banco.lower() == banco.lower():
                periodos_deste_banco.add(linha_periodo)

            linha_modificada = linha.copy()
            linha_modificada[1] = f"'{linha_periodo}" if not linha_periodo.startswith("'") else linha_periodo
            linhas_filtradas.append(linha_modificada)

    # Adiciona as transações atuais
    for t in transacoes:
        parcela_raw = t.get("parcela", "-")
        # Prefixa com apóstrofo para forçar o Google Sheets a tratar como TEXTO.
        # Sem isso, valores como "01/02" são interpretados como DATA (USER_ENTERED)
        # e viram números seriais aleatórios (ex: 46058) em vez de "01/02".
        parcela_valor = f"'{parcela_raw}" if isinstance(parcela_raw, str) and not parcela_raw.startswith("'") else parcela_raw

        linhas_filtradas.append([
            banco,
            f"'{periodo}",
            t.get("data", ""), t.get("estabelecimento", ""),
            t.get("tipo", ""), parcela_valor,
            float(t.get("valor", 0.0))
        ])

    db_sheet.clear()
    db_sheet.append_rows(linhas_filtradas, value_input_option="USER_ENTERED")

    # =========================================================================
    # FASE 2: O DASHBOARD DINÂMICO DO BANCO
    # =========================================================================
    try:
        ws_banco = spreadsheet.worksheet(banco)
    except gspread.exceptions.WorksheetNotFound:
        ws_banco = spreadsheet.add_worksheet(title=banco, rows="100", cols="12")

    ws_banco.clear()

    layout_dashboard = [
        [f"💳 Dashboard Dinâmico - {banco}", "", "", "", "", "", "VALORES PARCELADOS", "", "", "", ""],
        ["Selecione o Período (Mês/Ano):", f"'{periodo}", "", "", "", "", "Valor Total:", f'=IFERROR(SUMIFS(DB_Transacoes!G:G; DB_Transacoes!A:A; "{banco}"; DB_Transacoes!B:B; B2; DB_Transacoes!E:E; "Parcelado"); 0)', "", "", ""],
        ["Valor Total Geral:", f'=IFERROR(SUMIFS(DB_Transacoes!G:G; DB_Transacoes!A:A; "{banco}"; DB_Transacoes!B:B; B2); 0)', "", "", "", "", "", "", "", "", ""],
        ["VALORES NORMAIS:", f'=IFERROR(SUMIFS(DB_Transacoes!G:G; DB_Transacoes!A:A; "{banco}"; DB_Transacoes!B:B; B2; DB_Transacoes!E:E; "Normal"); 0)', "", "", "", "", "", "", "", "", ""],
        ["Data", "Estabelecimento", "Tipo", "Parcela", "Valor", "", "Data", "Estabelecimento", "Tipo", "Parcela", "Valor"],
        [f'=IFERROR(FILTER(DB_Transacoes!C:G; DB_Transacoes!A:A="{banco}"; DB_Transacoes!B:B=B2); "")', "", "", "", "", "", f'=IFERROR(FILTER(DB_Transacoes!C:G; DB_Transacoes!A:A="{banco}"; DB_Transacoes!B:B=B2; DB_Transacoes!E:E="Parcelado"); "")', "", "", "", ""]
    ]
    
    ws_banco.append_rows(layout_dashboard, value_input_option="USER_ENTERED")

    # =========================================================================
    # FASE 3: ESTILIZAÇÃO E DROPDOWN (Menu Suspenso)
    # =========================================================================
    
    # Criando o Menu Suspenso na Célula B2 com base nos meses existentes
    lista_periodos_ordenada = sorted(list(periodos_deste_banco))
    regra_dropdown = DataValidationRule(
        BooleanCondition('ONE_OF_LIST', lista_periodos_ordenada),
        showCustomUi=True
    )
    set_data_validation_for_cell_range(ws_banco, "B2", regra_dropdown)

    # Estilização
    format_cell_range(ws_banco, "A1:E1", cellFormat(backgroundColor=color(0.1, 0.1, 0.5), textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=12)))
    format_cell_range(ws_banco, "A2:A4", cellFormat(textFormat=textFormat(bold=True)))
    
    # Formata a B2 explicitamente como TEXTO (com o pattern '@' exigido pela API)
    format_cell_range(ws_banco, "B2", cellFormat(backgroundColor=color(0.9, 0.9, 1.0), textFormat=textFormat(bold=True), numberFormat=numberFormat(type="TEXT", pattern="@"))) 
    
    moeda_bold_vermelha = cellFormat(numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00"), textFormat=textFormat(bold=True, foregroundColor=color(0.8, 0.2, 0.2)))
    format_cell_range(ws_banco, "B3:B4", moeda_bold_vermelha)
    format_cell_range(ws_banco, "G2:G3", cellFormat(textFormat=textFormat(bold=True)))
    format_cell_range(ws_banco, "H3", moeda_bold_vermelha)

    header_format = cellFormat(backgroundColor=color(0.2, 0.2, 0.2), textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1)))
    format_cell_range(ws_banco, "A5:E5", header_format)
    format_cell_range(ws_banco, "G5:K5", header_format)

    format_cell_range(ws_banco, "A6:A100", cellFormat(horizontalAlignment="CENTER"))
    format_cell_range(ws_banco, "C6:D100", cellFormat(horizontalAlignment="CENTER"))
    format_cell_range(ws_banco, "E6:E100", cellFormat(numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00")))
    
    format_cell_range(ws_banco, "G6:G100", cellFormat(horizontalAlignment="CENTER"))
    format_cell_range(ws_banco, "I6:J100", cellFormat(horizontalAlignment="CENTER"))
    format_cell_range(ws_banco, "K6:K100", cellFormat(numberFormat=numberFormat(type="CURRENCY", pattern="R$#,##0.00")))

    format_cell_range(ws_banco, "G6:K100", cellFormat(backgroundColor=color(1.0, 0.95, 0.85)))

    set_column_width(ws_banco, 'A', 80)
    set_column_width(ws_banco, 'B', 250)
    set_column_width(ws_banco, 'C', 100)
    set_column_width(ws_banco, 'D', 80)
    set_column_width(ws_banco, 'E', 100)
    set_column_width(ws_banco, 'F', 30) 
    set_column_width(ws_banco, 'G', 80)
    set_column_width(ws_banco, 'H', 250)
    set_column_width(ws_banco, 'I', 100)
    set_column_width(ws_banco, 'J', 80)
    set_column_width(ws_banco, 'K', 100)

    try:
        todas_abas = spreadsheet.worksheets()
        todas_abas.sort(key=lambda ws: "0_DB" if ws.title == "DB_Transacoes" else ws.title)
        spreadsheet.reorder_worksheets(todas_abas)
    except Exception as e:
        print(f"Aviso ao organizar abas: {e}")