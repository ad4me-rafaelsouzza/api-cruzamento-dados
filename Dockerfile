FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da API
COPY api_v4.py .
COPY db_relationships.json .

# Expor porta
EXPOSE 8000

# Comando para iniciar
CMD ["python", "api_v4.py"]
