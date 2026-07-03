import os
from google import genai
from google.genai import types

def extract_transactions_with_ai(raw_text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")

    client = genai.Client(api_key=api_key)

    prompt = """
    Você é um extrator de dados financeiros. 
    Analise o texto da fatura de cartão de crédito e extraia as informações no formato JSON.
    
    Regras:
    1. Ignore pagamentos da fatura anterior e taxas (ex: IOF).
    2. Identifique o nome do banco emissor da fatura.
    3. Identifique o valor total da fatura.
    4. Para cada transação, verifique se há um indicador de parcela (ex: 01/10, 08/12, 2/03) no nome do estabelecimento.
    
    Estrutura exata do JSON de saída:
    {
      "banco": "Nome do Banco",
      "valor_total": 0000.00,
      "transacoes": [
        {
          "data": "DD/MM",
          "estabelecimento": "NOME LIMPO (sem a parcela)",
          "valor": 00.00,
          "tipo": "Parcelado" (se houver parcela) ou "Normal",
          "parcela": "X/Y" (ex: "08/12") ou nulo (se for normal)
        }
      ]
    }

    Texto bruto da fatura:
    """

    response = client.models.generate_content(
        model='gemini-flash-lite-latest',
        contents=prompt + "\n" + raw_text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    return response.text