# 🐛 Debug - PredictionsPanel e Análise de Moedas

## Problemas Reportados

1. **PredictionsPanel mostra "Sem holdings detetados"** mesmo com 219 holdings na tabela
2. **Análise de moedas não funciona** (ex: "analisa-me a moeda ADA")

## ✅ Alterações Feitas

### 1. PredictionsPanel - Logging Melhorado
- Adicionado `console.log` para debug no browser
- Verifica URL da API
- Mostra status da resposta
- Mostra quantidade de dados recebidos

### 2. Endpoint `/alerts/predictions` - Fallback para Debug
- Se não houver predictions com score >= 50, retorna top 10 por score (mesmo < 50)
- Melhor logging no backend

## 🔍 Como Debuggar

### Passo 1: Verificar Console do Browser

1. Abre o frontend no browser
2. Abre Developer Tools (F12)
3. Vai ao tab **Console**
4. Recarrega a página
5. Procura por mensagens:
   - `🌐 Fetching from: ...`
   - `📡 Response status: ...`
   - `✅ Data received: ...`
   - `📊 Predictions recebidas: X itens`

### Passo 2: Verificar se a API Está a Correr

Testa diretamente no browser:
```
http://localhost:8000/alerts/predictions
```

Ou se estiver em produção:
```
https://vigia-crypto-1.onrender.com/alerts/predictions
```

**O que esperar:**
- Se retornar `[]` (array vazio) → Não há predictions com score >= 50
- Se retornar dados → API está OK, problema pode ser no frontend

### Passo 3: Verificar Score dos Holdings

O endpoint filtra por `score >= 50`. Se não houver nenhum com score alto, não mostra nada.

**Solução temporária:** O código agora retorna top 10 mesmo com score < 50 se não houver nenhum >= 50.

### Passo 4: Verificar Análise de Moedas

Testa no browser console:
```javascript
fetch('http://localhost:8000/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: 'analisa-me a moeda ADA' })
})
.then(r => r.text())
.then(console.log)
```

**O que verificar:**
- Se retorna análise → Funciona
- Se retorna erro ou nada → Problema na detecção de moeda

## 🔧 Possíveis Problemas

### Problema 1: CORS
Se aparecer erro de CORS no console:
- Verifica se `FRONTEND_URL` está configurado no backend
- Verifica se o frontend está a chamar a URL correta

### Problema 2: Score Muito Baixo
Se todos os holdings têm score < 50:
- O endpoint retorna array vazio
- **Solução:** Reduzir threshold ou verificar porque os scores são baixos

### Problema 3: API Não Está a Correr
Se aparecer "Failed to fetch":
- Verifica se a API está a correr
- Verifica se a URL está correta (`NEXT_PUBLIC_API_URL`)

### Problema  ## 📋 Checklist de Debug

- [ ] Console do browser mostra logs?
- [ ] API está a correr?
- [ ] Endpoint `/alerts/predictions` retorna dados no browser?
- [ ] Há holdings com score >= 50?
- [ ] URL da API está correta no frontend?
- [ ] Não há erros de CORS?

## 🎯 Próximos Passos

1. **Abre o console do browser** e partilha os logs
2. **Testa o endpoint diretamente** no browser
3. **Verifica se há holdings com score >= 50** no Supabase Dashboard
