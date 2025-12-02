# 🔍 Guia de Teste - Supabase

## Problema: API fica "a pensar" e não retorna dados

Este guia ajuda a diagnosticar problemas com o Supabase.

## 📋 Passo 1: Testar Conexão Direta com Supabase

Execute o script de teste:

```bash
cd backend
python test_supabase.py
```

Este script vai:
- ✅ Verificar se as variáveis de ambiente estão configuradas
- ✅ Testar conexão básica com Supabase
- ✅ Contar registos na tabela `transacted_tokens`
- ✅ Verificar predictions (score >= 50)
- ✅ Testar estrutura dos dados
- ✅ Verificar timeouts

### O que procurar:

1. **Se aparecer "❌ SUPABASE_URL: NÃO DEFINIDO"**
   - Verifica se tens um ficheiro `.env` no diretório `backend/` ou na raiz
   - Verifica se tem `SUPABASE_URL=...` e `SUPABASE_SERVICE_ROLE_KEY=...`

2. **Se aparecer "❌ ERRO 401: Chave de autenticação inválida"**
   - A `SUPABASE_SERVICE_ROLE_KEY` está incorreta
   - Vai ao Supabase Dashboard > Settings > API > Service Role Key

3. **Se aparecer "⚠️ ERRO 404: Tabela não encontrada"**
   - A tabela `transacted_tokens` não existe
   - Verifica no Supabase Dashboard > Table Editor

4. **Se demorar muito (>5s)**
   - Pode haver muitos registos na tabela
   - Considera adicionar índices ou limitar a query

## 📋 Passo 2: Testar Endpoints da API

Primeiro, inicia a API:

```bash
cd backend/Api
uvicorn main:app --reload --port 8000
```

Depois, noutro terminal:

```bash
cd backend
python test_api_endpoints.py
```

Ou testa manualmente no browser:
- http://localhost:8000/alerts/predictions
- http://localhost:8000/alerts/holdings
- http://localhost:8000/alerts/health

## 📋 Passo 3: Verificar Logs

Se a API estiver a correr, verifica os logs no terminal. Agora os endpoints têm logging melhorado:

```
INFO: Buscando predictions do Supabase...
INFO: Recebidos 150 registos do Supabase
INFO: Predictions filtradas (score >= 50): 23
```

Se aparecerem erros:
```
ERROR: Erro ao buscar predictions: HTTP 401 - ...
ERROR: Timeout ao buscar transacted_tokens (>8s)
```

## 🔧 Soluções Comuns

### Problema: Timeout (>8 segundos)

**Solução 1:** Adicionar limite na query
```python
params = {
    "type": "eq.holding",
    "select": "...",
    "limit": "100"  # Limitar resultados
}
```

**Solução 2:** Adicionar índices no Supabase
- Vai ao Supabase Dashboard > Table Editor > `transacted_tokens`
- Cria índice em `type` e `score`

### Problema: Tabela vazia

Verifica se o worker está a correr e a inserir dados:
```bash
cd backend/worker
python vigia_solana_pro_supabase.py
```

### Problema: Variáveis de ambiente não carregadas

No Render/Vercel, verifica se as variáveis estão configuradas:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## 📊 Verificar Dados no Supabase Dashboard

1. Vai a https://supabase.com/dashboard
2. Seleciona o teu projeto
3. Vai a **Table Editor** > `transacted_tokens`
4. Verifica se há dados com `type = 'holding'`
5. Verifica se há registos com `score >= 50`

## 🐛 Debug Avançado

Se ainda não funcionar, adiciona mais logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Isto vai mostrar todas as requests HTTP ao Supabase.

