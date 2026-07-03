import os
from google import genai
from google.genai import types

def extract_transactions_with_ai(raw_text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")

    client = genai.Client(api_key=api_key)

    prompt = """
    Você é um extrator de dados financeiros de alta precisão. 
    Analise o texto da fatura de cartão de crédito de qualquer banco e extraia as informações no formato JSON.
    
    Regras estritas:
    1. Ignore pagamentos da fatura anterior, créditos de estorno na listagem principal e taxas/impostos (ex: IOF).
    2. Identifique o nome do banco emissor de forma clara e limpa (ex: 'Bradesco', 'Nubank', 'Itaú', 'Inter'). Não inclua 'S.A.' ou complementos.
    3. Identifique o mês e o ano de referência da fatura com base no vencimento. O mês deve ser por extenso em português e minúsculo (ex: 'janeiro', 'junho') e o ano com 4 dígitos (ex: 2026).
    4. Identifique o valor total final da fatura.
    5. Para compras parceladas, extraia o nome do estabelecimento limpo e coloque a parcela no campo correspondente (ex: '01/02').
    
    Estrutura exata do JSON de saída:
    {
      "banco": "Nome do Banco",
      "mes_fatura": "junho",
      "ano_fatura": 2026,
      "valor_total": 0000.00,
      "transacoes": [
        {
          "data": "DD/MM",
          "estabelecimento": "NOME DO ESTABELECIMENTO",
          "valor": 00.00,
          "tipo": "Parcelado" ou "Normal",
          "parcela": "X/Y" ou "-"
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