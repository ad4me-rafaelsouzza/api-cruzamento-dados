"""
Configuração de redirecionamento para domain customizado
Adicione este código ao api.py para redirecionar rsouzza.co/api
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.get("/")
async def redirect_to_replit():
    """Redireciona para a API do Replit"""
    return RedirectResponse(url="https://api-cruzamento-dados.replit.dev")

# Adicione todas as rotas aqui...
