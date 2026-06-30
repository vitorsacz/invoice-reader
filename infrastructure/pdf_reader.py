import pdfplumber
import os

def extract_text_from_pdf(file_path: str) -> str:
    """
    Abre o arquivo PDF e extrai todo o texto contido nele.
    Retorna uma string com o conteúdo bruto.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"O arquivo não foi encontrado no caminho: {file_path}")

    extracted_text = ""
    
    # O context manager (with) garante que o arquivo será fechado corretamente
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
                
    return extracted_text