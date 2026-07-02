import pdfplumber

def extract_text_from_pdf(file_obj) -> str:
    """
    Lê o PDF diretamente da memória (upload do front-end) 
    e extrai todo o texto contido nele.
    """
    extracted_text = ""
    
    # pdfplumber consegue ler o objeto em memória nativamente
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
                
    return extracted_text