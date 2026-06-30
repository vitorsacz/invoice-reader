# Usando uma imagem oficial leve do Python
FROM python:3.11-slim

# Definindo o diretório de trabalho dentro do container
WORKDIR /app

# Copiando apenas o arquivo de requisitos primeiro (aproveita o cache do Docker)
COPY requirements.txt .

# Instalando as dependências sem armazenar cache desnecessário
RUN pip install --no-cache-dir -r requirements.txt

# Copiando o restante do código da aplicação
COPY . .

# Comando padrão para rodar a aplicação
CMD ["python", "main.py"]