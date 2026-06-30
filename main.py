import os
import json
from dotenv import load_dotenv
from infrastructure.pdf_reader import extract_text_from_pdf
from infrastructure.ai_client import extract_transactions_with_ai
from infrastructure.sheets_client import update_google_sheet

load_dotenv()

def main():
    pdf_path = os.path.join(os.path.dirname(__file__), "data", "bradesco-fatura.pdf")
    sheet_url = os.getenv("SPREADSHEET_URL")
    
    try:
        print(f"1. Extraindo texto de: {pdf_path}...")
        texto_bruto = extract_text_from_pdf(pdf_path)
        
        print("2. Enviando texto para o Gemini estruturar os dados...")
        json_response = extract_transactions_with_ai(texto_bruto)
        
        dados_estruturados = json.loads(json_response)
        transacoes = dados_estruturados.get("transacoes", [])
        
        print(f"\n3. {len(transacoes)} transações extraídas. Enviando para o Google Sheets...")
        update_google_sheet(transacoes, sheet_url)
        
        print("\nProcesso concluído com sucesso! Pode verificar sua planilha.")
            
    except Exception as e:
        print(f"\nErro durante a execução: {e}")

if __name__ == "__main__":
    main()