from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json
import os

app = FastAPI()

# Carregar configuração dos bancos
try:
    with open('db_relationships.json', 'r') as f:
        db_config = json.load(f)
except:
    db_config = {}

@app.get("/")
async def root():
    return {
        "name": "API de Cruzamento de Dados",
        "message": "Use /api/* para acessar os endpoints",
        "status": "online"
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "API Cruzamento de Dados",
        "version": "4.0.0"
    }

@app.get("/api/search/{value}")
async def search(value: str):
    return {
        "search_type": "CPF" if len(value) >= 11 else "CONTATOS_ID",
        "search_value": value,
        "message": "API funcionando em Vercel (permanente)",
        "status": "online"
    }

@app.get("/api/databases")
async def databases():
    return {
        "databases": db_config,
        "status": "online"
    }
