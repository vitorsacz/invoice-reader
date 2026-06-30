import os
from google import genai
from google.genai import types

def extract_transactions_with_ai(raw_text: str) -> str:
    """
    Envia o texto bruto para o Gemini e solicita a extração estruturada
    dos lançamentos da fatura em formato JSON.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")

    # Inicializa o cliente do Gemini
    client = genai.Client(api_key=api_key)

    # O prompt define exatamente a regra de negócio da extração
    prompt = """
    Você é um extrator de dados financeiros. 
    Analise o texto bruto de uma fatura de cartão de crédito e extraia apenas as transações de compra.
    
    Regras de extração:
    1. Ignore pagamentos da fatura anterior (ex: "PAGTO. POR DEB EM C/C").
    2. Ignore cobranças de impostos ou taxas (ex: "IOF S/TRANS INTER REAIS").
    3. Retorne APENAS um objeto JSON contendo uma chave "transacoes", que deve ser uma lista de objetos.
    4. Cada objeto da lista deve ter exatamente as seguintes chaves:
       - "data": A data da transação no formato "DD/MM".
       - "estabelecimento": O nome do local, limpo, sem a cidade e em letras MAIÚSCULAS.
       - "valor": O valor da transação como um número float (ex: 150.80). Cuidado com a formatação brasileira (use ponto para decimais).

    Texto bruto da fatura:
    """

    # Chamada à API forçando o retorno no mimetype JSON
    response = client.models.generate_content(
        model='gemini-flash-lite-latest',        
        contents=prompt + "\n" + raw_text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1, # Temperatura baixa para respostas mais determinísticas e factuais
        ),
    )
    
    return response.text