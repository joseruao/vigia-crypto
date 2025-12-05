# 🚀 Solução Rápida: "Supabase não configurado"

## Problema Identificado
- ✅ `SUPABASE_URL` está a ser carregado
- ❌ `SUPABASE_SERVICE_ROLE_KEY` NÃO está a ser carregado
- ❌ API não está a correr (connection refused)

## 🔧 Solução Passo a Passo

### Passo 1: Verifica o ficheiro .env

Abre o ficheiro `.env` que está em:
- `backend/.env` OU
- `.env` (raiz do projeto)

**Verifica se tem esta linha EXATA:**
```
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
```

**⚠️ PROBLEMAS COMUNS:**
1. **Nome errado:** 
   - ❌ `SUPABASE_KEY=...`
   - ❌ `SUPABASE_API_KEY=...`
   - ✅ `SUPABASE_SERVICE_ROLE_KEY=...`

2. **Espaços em volta do `=`:**
   - ❌ `SUPABASE_SERVICE_ROLE_KEY = ...`
   - ❌ `SUPABASE_SERVICE_ROLE_KEY= ...`
   - ✅ `SUPABASE_SERVICE_ROLE_KEY=...`

3. **Valor vazio ou placeholder:**
   - ❌ `SUPABASE_SERVICE_ROLE_KEY=`
   - ❌ `SUPABASE_SERVICE_ROLE_KEY=missing`
   - ✅ `SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...` (valor completo)

4. **Aspas desnecessárias:**
   - ❌ `SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIs..."`
   - ✅ `SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...`

### Passo 2: Executa o script de verificação

```bash
cd backend
python check_env_file.py
```

Isto vai mostrar:
- Se o ficheiro existe
- Se as variáveis estão corretas
- Se há problemas de formatação

### Passo 3: Inicia a API

**Opção A: Usar o script PowerShell (recomendado)**
```powershell
cd backend
.\start_api.ps1
```

**Opção B: Manualmente**
```bash
cd backend/Api
python -m uvicorn main:app --reload --port 8000
```

**Opção C: Usar o script BAT**
```cmd
cd backend
start_api.bat
```

### Passo 4: Verifica se a API está a correr

Quando a API inicia, deves ver nos logs:
```
✅ Carregado .env de: C:\Users\joser\vigia_crypto\backend\.env
   SUPABASE_URL: ✅ (XX chars)
   SUPABASE_SERVICE_ROLE_KEY: ✅ (XX chars)
```

Se aparecer `❌` no `SUPABASE_SERVICE_ROLE_KEY`, o problema está no `.env`.

### Passo 5: Testa o health check

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

Se `has_key` for `false`, o problema está no `.env`.

## 🐛 Se Ainda Não Funcionar

### Verifica o nome exato da variável

No Supabase Dashboard:
1. Vai a **Settings** > **API**
2. Copia a **Service Role Key** (não a anon key!)
3. No `.env`, usa exatamente:
   ```
   SUPABASE_SERVICE_ROLE_KEY=<cole aqui a chave>
   ```

### Verifica se há múltiplas definições

No `.env`, deve haver apenas UMA linha com `SUPABASE_SERVICE_ROLE_KEY`.

Se houver múltiplas, remove as duplicadas e deixa apenas uma.

### Verifica espaços e caracteres especiais

A linha deve ser:
```
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Sem espaços antes/depois do `=`, sem aspas, sem quebras de linha no meio do valor.

## ✅ Checklist Final

- [ ] Ficheiro `.env` existe em `backend/.env`
- [ ] Tem a linha `SUPABASE_SERVICE_ROLE_KEY=...` (nome EXATO)
- [ ] Sem espaços antes/depois do `=`
- [ ] Valor não está vazio
- [ ] Apenas UMA linha com `SUPABASE_SERVICE_ROLE_KEY`
- [ ] API foi REINICIADA após alterar o `.env`
- [ ] Logs da API mostram `SUPABASE_SERVICE_ROLE_KEY: ✅`
- [ ] `/alerts/health` retorna `has_key: true`

## 🎯 Próximos Passos

1. **Executa:** `python check_env_file.py` e partilha o output
2. **Inicia a API** usando um dos scripts acima
3. **Partilha os logs** da API quando inicia
4. **Testa** `/alerts/health` e partilha o resultado

Com esta informação consigo ajudar-te a resolver!
