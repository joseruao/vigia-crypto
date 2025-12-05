# 🚨 RESOLVER AGORA: "Supabase não configurado"

## Problema
- ✅ `SUPABASE_URL` está a funcionar
- ❌ `SUPABASE_SERVICE_ROLE_KEY` NÃO está a ser carregado
- ❌ API não está a correr

## 🔧 Solução Rápida

### 1. Abre o ficheiro `.env`

O ficheiro está em:
```
backend\.env
```

### 2. Verifica se tem esta linha EXATA:

```
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
```

**⚠️ PROBLEMAS COMUNS:**

#### Problema A: Nome errado
Se tiveres:
```
SUPABASE_KEY=...
```
ou
```
SUPABASE_API_KEY=...
```

**SOLUÇÃO:** Muda para:
```
SUPABASE_SERVICE_ROLE_KEY=...
```

#### Problema B: Espaços
Se tiveres:
```
SUPABASE_SERVICE_ROLE_KEY = ...
```
ou
```
SUPABASE_SERVICE_ROLE_KEY= ...
```

**SOLUÇÃO:** Remove os espaços:
```
SUPABASE_SERVICE_ROLE_KEY=...
```

#### Problema C: Valor vazio
Se tiveres:
```
SUPABASE_SERVICE_ROLE_KEY=
```

**SOLUÇÃO:** Adiciona o valor completo da Service Role Key do Supabase Dashboard

#### Problema D: Aspas
Se tiveres:
```
SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIs..."
```

**SOLUÇÃO:** Remove as aspas:
```
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
```

### 3. Onde encontrar a Service Role Key

1. Vai a https://supabase.com/dashboard
2. Seleciona o teu projeto
3. Vai a **Settings** > **API**
4. Copia a **Service Role Key** (secret) - NÃO a anon key!
5. Cola no `.env`:
   ```
   SUPABASE_SERVICE_ROLE_KEY=<cole aqui>
   ```

### 4. Formato correto do .env

O ficheiro deve ter estas duas linhas (sem espaços extras):

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 5. Inicia a API

**Opção A: PowerShell (recomendado)**
```powershell
cd backend
.\start_api.ps1
```

**Opção B: Manualmente**
```bash
cd backend\Api
python -m uvicorn main:app --reload --port 8000
```

### 6. Verifica os logs

Quando a API inicia, deves ver:
```
✅ Carregado .env de: C:\Users\joser\vigia_crypto\backend\.env
   SUPABASE_URL: ✅ (XX chars)
   SUPABASE_SERVICE_ROLE_KEY: ✅ (XX chars)
```

Se aparecer `❌` no `SUPABASE_SERVICE_ROLE_KEY`, o problema está no `.env`.

### 7. Testa

Abre no browser:
```
http://localhost:8000/alerts/health
```

Deve retornar:
```json
{
  "ok": true,
  "supabase_url": true,
  "has_key": true,
  "supa_ok": true
}
```

## ✅ Checklist

- [ ] Ficheiro `.env` aberto
- [ ] Tem `SUPABASE_SERVICE_ROLE_KEY=...` (nome EXATO, sem espaços)
- [ ] Valor não está vazio
- [ ] Sem aspas em volta do valor
- [ ] Apenas UMA linha com esta variável
- [ ] API reiniciada
- [ ] Logs mostram `SUPABASE_SERVICE_ROLE_KEY: ✅`
- [ ] `/alerts/health` retorna `has_key: true`

## 🎯 Se Ainda Não Funcionar

1. **Executa este comando:**
   ```bash
   cd backend
   python verificar_env.py
   ```
   
   Isto vai mostrar exatamente o que está no `.env`

2. **Partilha:**
   - O output do `verificar_env.py`
   - Os logs da API quando inicia
   - O resultado do `/alerts/health`

Com esta informação consigo ajudar-te a resolver!
