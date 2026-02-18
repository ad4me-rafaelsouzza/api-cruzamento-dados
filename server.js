const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Endpoint raiz
app.get('/', (req, res) => {
  res.json({
    name: "API de Cruzamento de Dados",
    message: "Use /api/* para acessar os endpoints",
    endpoints: {
      search: "/api/search/{cpf_ou_contatos_id}",
      health: "/api/health",
      databases: "/api/databases",
      docs: "/api/docs"
    }
  });
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: "healthy",
    service: "API Cruzamento de Dados",
    timestamp: new Date().toISOString()
  });
});

// Proxy para a API Python
app.get('/api/*', async (req, res) => {
  try {
    const path = req.params[0];
    const query = req.url.includes('?') ? '?' + req.url.split('?')[1] : '';
    
    // URL da API Python hospedada em Replit
    const apiUrl = `https://api-cruzamento-dados.username.repl.co/${path}${query}`;
    
    const response = await fetch(apiUrl);
    const data = await response.json();
    
    res.status(response.status).json(data);
  } catch (error) {
    res.status(500).json({
      error: "Erro ao processar requisição",
      message: error.message
    });
  }
});

// 404
app.use((req, res) => {
  res.status(404).json({ error: "Endpoint não encontrado" });
});

app.listen(PORT, () => {
  console.log(`🚀 API rodando em http://localhost:${PORT}`);
});
