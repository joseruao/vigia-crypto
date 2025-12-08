# 🔧 Solução Definitiva

## Problema
Mesmo após todas as correções, a API continua a mostrar "KEY: ❌"

## ✅ Solução: Definir Variáveis no Ambiente ANTES de Iniciar

O problema pode ser que o Python está a cachear o módulo ou o `.env` não está a ser carregado corretamente quando a API inicia.

### Opção 1: Definir Variáveis no PowerShell (Recomendado)

**Antes de iniciar a API**, define as variáveis no ambiente:

```powershell
# Define as variáveis
$env:SUPABASE_URL="https://qynnajpvxnqcmkzrhpde.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"

# Depois inicia a API
cd backend
.\start_api.ps1
```

### Opção 2: Criar Script PowerShell com Variáveis

Cria um ficheiro `backend\start_api_com_env.ps1`:

```powershell
# Define variáveis de ambiente
$env:SUPABASE_URL="https://qynnajpvxnqcmkzrhpde.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"

# Inicia a API
cd Api
python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
```

Depois usa este script em vez do `start_api.ps1`.

### Opção 3: Verificar Logs da API

Quando a API inicia, verifica os logs. Deves ver:

```
✅ Carregado .env de: C:\Users\joser\vigia_crypto\backend\.env
   SUPABASE_URL: ✅ (40 chars)
   SUPABASE_SERVICE_ROLE_KEY: ✅ (208 chars)
```

**Se aparecer `❌`, partilha os logs completos!**

## 🎯 Teste Rápido

1. **Para TODOS os processos Python** relacionados com a API
2. **Define as variáveis** (Opção 1)
3. **Inicia a API** novamente
4. **Testa:** `http://localhost:8000/alerts/health`

Deve retornar `has_key: true` e `supa_ok: true`.

## 💡 Por Que Isto Funciona?

Definir as variáveis no ambiente antes de iniciar garante que estão disponíveis quando o Python importa os módulos, mesmo que o `.env` não seja carregado corretamente.
