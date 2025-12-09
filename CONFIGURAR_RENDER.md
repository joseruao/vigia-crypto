# 🔧 Como Configurar Variáveis de Ambiente no Render

## Problema
O backend no Render está a retornar "Supabase não configurado" porque faltam as variáveis de ambiente.

## ✅ Solução

### Passo 1: Aceder ao Dashboard do Render

1. Vai a: https://dashboard.render.com
2. Faz login na tua conta
3. Seleciona o serviço do backend (provavelmente `vigia-crypto-1` ou similar)

### Passo 2: Adicionar Variáveis de Ambiente

1. **Clica em "Environment"** (no menu lateral)
2. **Adiciona estas variáveis:**

#### Variável 1: `SUPABASE_URL`
- **Key:** `SUPABASE_URL`
- **Value:** `https://qynnajpvxnqcmkzrhpde.supabase.co`

#### Variável 2: `SUPABASE_SERVICE_ROLE_KEY` (ou `SUPABASE_SERVICE_ROLE`)
- **Key:** `SUPABASE_SERVICE_ROLE_KEY` (recomendado) ou `SUPABASE_SERVICE_ROLE` (também funciona)
- **Value:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A`

⚠️ **NOTA:** Se já tens `SUPABASE_SERVICE_ROLE` configurado no Render, o código agora aceita ambos os nomes. Mas é melhor usar `SUPABASE_SERVICE_ROLE_KEY` para consistência.

⚠️ **IMPORTANTE:** 
- Não adiciones espaços antes ou depois do `=`
- Copia o valor completo (208 caracteres)
- A `SERVICE_ROLE_KEY` é diferente da `ANON_KEY`!

### Passo 3: Reiniciar o Serviço

1. Depois de adicionar as variáveis, **clica em "Manual Deploy"** ou **"Restart"**
2. Aguarda o deploy terminar
3. Testa novamente no website

## 🔍 Verificar se Está Correto

Depois de configurar, testa:
```
https://vigia-crypto-1.onrender.com/alerts/health
```

Deves ver:
```json
{
  "ok": true,
  "has_key": true,
  "supabase_key_length": 208,
  "supa_ok": true
}
```

Se `has_key: false` ou `supabase_key_length: 0`, as variáveis não foram configuradas corretamente.

## 📋 Checklist

- [ ] `SUPABASE_URL` adicionada no Render
- [ ] `SUPABASE_SERVICE_ROLE_KEY` adicionada no Render (208 chars)
- [ ] Serviço reiniciado após adicionar variáveis
- [ ] Health check retorna `has_key: true`
- [ ] Website funciona corretamente

## ⚠️ Diferença entre ANON_KEY e SERVICE_ROLE_KEY

- **`NEXT_PUBLIC_SUPABASE_ANON_KEY`** → Para o **frontend** (Vercel)
  - Usada no browser
  - Respeita Row Level Security (RLS)
  - Já está configurada corretamente no Vercel ✅

- **`SUPABASE_SERVICE_ROLE_KEY`** → Para o **backend** (Render)
  - Usada no servidor
  - Bypassa RLS (para operações administrativas)
  - **Precisa estar configurada no Render** ❌ (atualmente falta)

## 🎯 Resumo

**Vercel (Frontend):**
- ✅ `NEXT_PUBLIC_API_URL` = `https://vigia-crypto-1.onrender.com`
- ✅ `NEXT_PUBLIC_SUPABASE_URL` = `https://qynnajpvxnqcmkzrhpde.supabase.co`
- ✅ `NEXT_PUBLIC_SUPABASE_ANON_KEY` = (a que já tens)

**Render (Backend):**
- ✅ `SUPABASE_URL` = `https://qynnajpvxnqcmkzrhpde.supabase.co` (já configurado)
- ⚠️ `SUPABASE_SERVICE_ROLE` = (já configurado, mas o código procura `SUPABASE_SERVICE_ROLE_KEY`)

**Solução:** O código agora aceita ambos os nomes (`SUPABASE_SERVICE_ROLE` e `SUPABASE_SERVICE_ROLE_KEY`), mas para consistência, renomeia no Render de `SUPABASE_SERVICE_ROLE` para `SUPABASE_SERVICE_ROLE_KEY`.
