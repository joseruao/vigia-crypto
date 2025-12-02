# 🐛 Debug - Endpoint /alerts/ask Retorna "Sem resposta"

## Problema
Quando perguntas "Que tokens achas que vão ser listados?", retorna "⚠️ Sem resposta"

## ✅ Alterações Feitas

### 1. Frontend - Logging Melhorado
- Adicionado logging detalhado no console
- Tenta várias formas de obter a resposta
- Mostra dados completos da resposta

### 2. Backend - Resposta Melhorada
- Formata resposta mesmo quando não há resultados
- Mensagens mais informativas
- Logging detalhado

## 🔍 Como Debuggar

### Passo 1: Verificar Console do Browser

1. Abre o frontend
2. Abre Developer Tools (F12)
3. Vai ao tab **Console**
4. Faz a pergunta: "Que tokens achas que vão ser listados?"
5. Procura por:
   - `📥 Resposta completa recebida:`
   - `📥 data.answer:`
   - `📤 Resposta final a mostrar:`

### Passo 2: Testar Endpoint Diretamente

Abre no browser (ou usa curl):
```
http://localhost:8000/alerts/ask
```

Ou usa o script de teste:
```bash
python backend/test_ask_endpoint.py
```

### Passo 3: Verificar Logs do Backend

No terminal onde a API está a correr, deves ver:
```
INFO: Pergunta recebida: Que tokens achas que vão ser listados?
INFO: Buscando holdings com params: {...}
INFO: Recebidos X holdings do Supabase
INFO: Holdings filtrados: X
INFO: Resposta formatada: X caracteres
```

## 🔧 Possíveis Problemas

### Problema 1: Não há dados com score >= 50

**Sintoma:** Resposta diz "Não encontrei tokens com potencial de listing"

**Solução:** 
- Verifica no Supabase se há holdings com score >= 50
- Ou reduz o threshold temporariamente no código

### Problema 2: Resposta não está a chegar

**Sintoma:** Console mostra `data.answer: undefined`

**Verifica:**
- Se a API está a correr
- Se há erros CORS
- Se o endpoint está a retornar `answer` no JSON

### Problema 3: Erro silencioso no backend

**Sintoma:** Backend não mostra logs

**Verifica:**
- Se há exceções não capturadas
- Se o Supabase está a responder
- Se há timeout

## 📋 Checklist

- [ ] API está a correr em localhost:8000?
- [ ] Console do browser mostra logs?
- [ ] Backend mostra logs quando fazes a pergunta?
- [ ] Há dados no Supabase com score >= 50?
- [ ] Endpoint `/alerts/ask` retorna JSON válido?

## 🎯 Próximos Passos

1. **Abre o console do browser** e partilha os logs
2. **Verifica os logs do backend** quando fazes a pergunta
3. **Testa o endpoint diretamente** com o script `test_ask_endpoint.py`
