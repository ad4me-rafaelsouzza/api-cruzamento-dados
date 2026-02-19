# Configuração de Domain Customizado (rsouzza.co/api)

## Opção 1: Usando Cloudflare (Recomendado)

### Passo 1: Adicionar CNAME no Cloudflare
1. Acesse: https://dash.cloudflare.com
2. Selecione seu domain: **rsouzza.co**
3. Vá para **DNS** → **Records**
4. Clique em **+ Add record**
5. Configure:
   - **Type**: CNAME
   - **Name**: api
   - **Target**: api-cruzamento-dados.replit.dev
   - **TTL**: Auto
   - **Proxy status**: Proxied (nuvem laranja)
6. Clique em **Save**

### Passo 2: Aguardar Propagação
- Propagação: 5-30 minutos
- Teste em: https://rsouzza.co/api/health

---

## Opção 2: Usando Manus (Seu Provider Atual)

1. Acesse: https://app.manus.im
2. Vá para **Settings** → **Domains**
3. Procure por **rsouzza.co**
4. Configure um novo registro:
   - **Type**: CNAME
   - **Name**: api
   - **Value**: api-cruzamento-dados.replit.dev
5. Salve e aguarde propagação

---

## Opção 3: Usando Netlify (Alternativa)

1. Acesse: https://netlify.com
2. Crie um novo site
3. Configure redirecionamento em `netlify.toml`:
```toml
[[redirects]]
from = "/api/*"
to = "https://api-cruzamento-dados.replit.dev/:splat"
status = 200
```

---

## Teste Após Configuração

```bash
# Testar health check
curl https://rsouzza.co/api/health

# Testar busca por CPF
curl https://rsouzza.co/api/search/37912834800
```

---

## Troubleshooting

**Erro 404?**
- Aguarde 30 minutos para propagação DNS
- Limpe cache do navegador (Ctrl+Shift+Del)

**Erro 502 Bad Gateway?**
- Verifique se a API do Replit está rodando
- Acesse: https://api-cruzamento-dados.replit.dev/health

**Erro de SSL?**
- Use HTTPS (não HTTP)
- Cloudflare gera certificado automaticamente
