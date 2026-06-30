readme_content = """# Fatura Bradesco Extractor 🧾🤖

Uma aplicação em Python estruturada com princípios de Clean Architecture para extrair automaticamente lançamentos de faturas de cartão de crédito (PDF) e enviá-los para o Google Sheets de forma estruturada, utilizando a API gratuita do Google Gemini.

## 🏗️ Arquitetura do Projeto

O projeto foi dividido separando a regra de negócio da infraestrutura externa:

* **`core/`**: (Opcional para expansão) Destinado a validações, tipagens (Pydantic) e filtros de domínio.
* **`infrastructure/`**: Camada de comunicação com o mundo externo.
    * `pdf_reader.py`: Abre e extrai o texto bruto do arquivo PDF.
    * `ai_client.py`: Envia o texto ao Gemini (LLM) com as regras de extração e retorna um JSON estruturado.
    * `sheets_client.py`: Autentica no Google Cloud e faz o *append* dos dados na planilha.
* **`main.py`**: O orquestrador que conecta a entrada (PDF), o processamento (IA) e a saída (Sheets).

## 🚀 Pré-requisitos

1.  **Python 3.11+**
2.  **Google AI Studio (Gemini API)**:
    * Crie uma chave gratuita no [Google AI Studio](https://aistudio.google.com/).
3.  **Google Cloud Console (Sheets & Drive API)**:
    * Crie um projeto no Google Cloud.
    * Ative a **Google Sheets API** e **Google Drive API**.
    * Crie uma **Conta de Serviço** (Service Account) e baixe a chave em formato JSON (salve como `credentials.json`).
    * Compartilhe sua planilha de finanças com o e-mail gerado pela Conta de Serviço, dando permissão de "Editor".

## ⚙️ Instalação e Configuração (Ambiente Local)

1. **Clone o repositório e crie o ambiente virtual:**


2. **Instale as dependencias**

````
pip install -r requirements.txt`
````

3. **Configuração das Variáveis de Ambiente:**

Crie um arquivo .env na raiz do projeto com o seguinte conteúdo:

````
GEMINI_API_KEY=sua_chave_do_gemini_aqui

SPREADSHEET_URL=[https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit](https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit)
````

4. **Configuração dos Arquivos Sensíveis:**

- Coloque o arquivo credentials.json na raiz do projeto.

- Coloque o seu PDF da fatura dentro da pasta data/ com o nome configurado no main.py (ex: bradesco-fatura.pdf).

5. **▶ Como Executar**

Com o ambiente ativado e as variáveis configuradas, basta rodar o orquestrador:

````
python main.py
````