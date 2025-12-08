# 🔍 Teste: Local vs Render

## Problema
- ✅ Key está correta no `.env` local
- ✅ Key está correta no Render
- ❌ Mas ainda não funciona

## Possíveis Causas

### 1. API não está a correr localmente

**Testa:**
```bash
curl http://localhost:8000/alerts/health
```

Se não funcionar, a API não está a correr.

### 2. Variáveis não estão a ser carregadas

**Testa:**
```bash
cd backend
python verificar_env.py
```

Isto mostra se as variáveis estão no `.env` e se são carregadas.

### 3. Problema no Render

No Render, as variáveis de ambiente devem estar configuradas em:
- **Settings** > **Environment Variables**

Verifica se tem:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

**⚠️ IMPORTANTE:** No Render, as variáveis de ambiente são definidas na interface, NÃO no `.env` (o `.env` não é usado em produção).

### 4. Problema de CORS ou URL

Se estás a testar localmente mas o frontend está no Vercel, pode haver problema de CORS ou URL.

**Verifica:**
- Frontend está a chamar `localhost:8000` ou `https://vigia-crypto-1.onrender.com`?
- CORS está configurado para aceitar o domínio do Vercel?

## 🎯 Próximos Passos

1. **Executa:** `python verificar_env.py` e partilha o output
2. **Verifica:** Se a API está a correr (`http://localhost:8000/alerts/health`)
3. **Verifica:** No Render, se as variáveis de ambiente estão configuradas
4. **Partilha:** Os logs da API quando inicia (tanto local como Render)


