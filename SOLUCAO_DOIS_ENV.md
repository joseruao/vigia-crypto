# 🔧 Solução: Dois Ficheiros .env

## Problema Identificado

Há **DOIS** ficheiros `.env`:
1. `.env` na raiz (correto, sem espaços) ✅
2. `backend\.env` (pode ter espaços ou estar incorreto) ❌

A API procura primeiro em `backend/.env` e depois na raiz. Se `backend/.env` existir, vai usar esse primeiro!

## ✅ Solução

### Opção 1: Apagar `backend/.env` (Recomendado)

Se o `.env` na raiz já está correto, apaga o `backend/.env`:

```powershell
cd backend
Remove-Item .env
```

Assim a API vai usar o `.env` da raiz que está correto.

### Opção 2: Corrigir `backend/.env`

Se quiseres manter dois ficheiros, corrige o `backend/.env`:

1. Abre `backend\.env`
2. Verifica se tem espaços antes do `=`
3. Remove os espaços:
   ```
   SUPABASE_URL=https://qynnajpvxnqcmkzrhpde.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
   ```

### Opção 3: Copiar da Raiz para Backend

Copia o `.env` correto da raiz para `backend/.env`:

```powershell
Copy-Item ..\.env backend\.env
```

## 🎯 Depois de Corrigir

**IMPORTANTE:** Reinicia a API:

1. **Para a API** (Ctrl+C)
2. **Reinicia:**
   ```powershell
   cd backend
   .\start_api.ps1
   ```

3. **Verifica os logs** - deve mostrar qual `.env` está a usar:
   ```
   ✅ Carregado .env de: C:\Users\joser\vigia_crypto\backend\.env
   ```

4. **Testa:**
   - `http://localhost:8000/alerts/health` → deve retornar `has_key: true`
   - No frontend: "Que tokens achas que vão ser listados?" → deve funcionar

## 💡 Recomendação

**Opção 1** é a mais simples: apaga `backend/.env` e usa apenas o da raiz.
