# 🐛 Debug - Frontend Não Comunica com Backend

## Problema
- Há dados no Supabase (muitos com score >= 50)
- PredictionsPanel não mostra nada
- Não responde quando carrega na suggestion
- Não responde quando pergunta para analisar moeda

## ✅ Alterações Feitas

### 1. CORS Melhorado
- Adicionado suporte para `localhost:3001` e `127.0.0.1`
- Regex atualizado para aceitar qualquer porta localhost

### 2. Frontend - Logging Detalhado
- Console mostra URL que está a chamar
- Mostra status da resposta
- Mostra dados recebidos

## 🔍 Como Debuggar

### Passo 1: Verificar Console do Browser (CRÍTICO!)

1. **Abre o frontend no browser**
2. **Pressiona F12** (Developer Tools)
3. **Vai ao tab Console**
4. **Recarrega a página** (Ctrl+F5)
5. **Procura por:**
   - `🌐 Fetching from: http://localhost:8000/alerts/predictions`
   - `📡 Response status: 200` (ou outro número)
   - `✅ Data received: Array with X items`

**Se aparecer erro de CORS:**
```
Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**Se aparecer erro de conexão:**
```
Failed to fetch
ERR_CONNECTION_REFUSED
```

### Passo 2: Verificar Network Tab

1. **F12 > Network tab**
2. **Recarrega a página**
3. **Procura por requests para `localhost:8000`**
4. **Clica num request e verifica:**
   - Status code (deve ser 200)
   - Response (deve ter dados JSON)
   - Headers (verifica se há CORS headers)

### Passo 3: Testar Endpoint Diretamente

Abre no browser:
```
http://localhost:8000/alerts/predictions
```

**Deves ver:** Uma lista JSON com predictions

Se não aparecer nada ou erro, a API não está a correr ou há problema.

### Passo 4: Verificar Logs do Backend

No terminal onde a API está a correr, quando recarregares o frontend, deves ver:
```
INFO: GET /alerts/predictions
INFO: Buscando predictions do Supabase...
INFO: Recebidos X registos do Supabase
```

**Se não aparecer nada:** O frontend não está a chamar a API

## 🔧 Possíveis Problemas

### Problema 1: API Não Está a Correr
**Sintoma:** Console mostra "Failed to fetch" ou "ERR_CONNECTION_REFUSED"

**Solução:** 
```bash
cd backend/Api
python -m uvicorn main:app --reload --port 8000
```

### Problema 2: CORS Bloqueando
**Sintoma:** Console mostra erro de CORS

**Solução:** Já corrigido no código, mas verifica se a API está a usar o código atualizado

### Problema 3: Frontend Usa URL Errada
**Sintoma:** Console mostra URL de produção em vez de localhost

**Solução:** 
- Verifica se estás em `localhost` no browser
- O código detecta automaticamente localhost
- Se não funcionar, força no `.env.local`:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```

### Problema 4: Next.js Cache
**Sintoma:** Mudanças não aparecem

**Solução:**
```bash
# Para o servidor Next.js
# Limpa cache e reinicia
rm -rf .next
npm run dev
```

## 📋 Checklist de Debug

- [ ] API está a correr em localhost:8000?
- [ ] Frontend está a correr (localhost:3000)?
- [ ] Console do browser mostra logs?
- [ ] Network tab mostra requests para localhost:8000?
- [ ] Requests têm status 200?
- [ ] Não há erros de CORS no console?
- [ ] Backend mostra logs quando frontend faz request?

## 🎯 Próximos Passos

1. **Abre o console do browser (F12)** e partilha:
   - Todos os erros que aparecem
   - O que aparece quando carregas na página
   - O que aparece quando clicas na suggestion

2. **Abre o Network tab (F12 > Network)** e partilha:
   - Se há requests para localhost:8000
   - Qual o status code
   - Qual a resposta

3. **Verifica os logs do backend** e partilha:
   - Se aparecem requests quando recarregares o frontend
   - Se há erros

Com esta informação consigo identificar exatamente onde está o problema!
