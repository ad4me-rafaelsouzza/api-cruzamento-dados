# 🚀 API de Cruzamento de Dados Multi-Banco

API que cruza dados de 4 bancos de dados SQLite (~139GB) e retorna informações consolidadas.

## 📊 Endpoints

- `GET /search/{value}` - Busca inteligente (CPF ou CONTATOS_ID)
- `GET /cpf/{cpf}` - Busca por CPF
- `GET /contatos/{id}` - Busca por CONTATOS_ID
- `GET /health` - Health check
- `GET /databases` - Lista bancos disponíveis
- `GET /docs` - Documentação Swagger

## 🚀 Deploy

### Railway (Recomendado)

1. Acesse: https://railway.app
2. Clique em "New Project"
3. Selecione "Deploy from GitHub"
4. Conecte este repositório
5. Railway fará o deploy automaticamente

### Replit

1. Acesse: https://replit.com
2. Clique em "+ Create"
3. Selecione "Import from GitHub"
4. Cole a URL deste repositório
5. Clique em "Run"

## 📝 Uso

```bash
curl https://seu-domain.com/search/37912834800
```

## ⚙️ Configuração

Edite `db_relationships.json` para configurar os bancos de dados.

---

**Versão**: 4.0.0  
**Status**: Produção
