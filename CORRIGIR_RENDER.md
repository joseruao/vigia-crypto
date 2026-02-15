# 🔧 Corrigir Render - Trocar ANON_KEY por SERVICE_ROLE_KEY

## ❌ Problema Identificado

### Render (Backend) - ERRADO
- **Variável:** `SUPABASE_SERVICE_ROLE` (ou similar)
- **Valor atual:** Tem `anon` key ❌
- **Problema:** Deveria ter `service_role` key!

### Vercel (Frontend) - CORRETO ✅
- **Variável:** `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Valor:** Tem `anon` key ✅
- **Status:** Já está correto!

## ✅ Solução

### Passo 1: Corrigir Render

1. Vai ao **Render Dashboard**: https://dashboard.render.com
2. Seleciona o teu serviço backend (`vigia-crypto-1` ou similar)
3. Vai a **Environment** (no menu lateral)
4. Encontra a variável que tem a ANON_KEY (provavelmente `SUPABASE_SERVICE_ROLE` ou `SUPABASE_SERVICE_ROLE_KEY`)
5. **Edita** e substitui pelo valor correto da SERVICE_ROLE_KEY:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A
```

6. **Guarda** e faz **redeploy/restart** do serviço

### Passo 2: Verificar Vercel (Já está correto ✅)

O Vercel já tem a `anon` key correta, não precisas alterar nada.

## 📋 Resumo das Keys Corretas

### Vercel (Frontend) ✅
- **Variável:** `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Valor:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc0Mzg4NjMsImV4cCI6MjA3MzAxNDg2M30.M30wZ79mQz2i3verO9JtyMn7JVE3yW1FjtcFJlnTvaw`
- **Role:** `anon` ✅

### Render (Backend) ❌ → ✅
- **Variável:** `SUPABASE_SERVICE_ROLE` ou `SUPABASE_SERVICE_ROLE_KEY`
- **Valor correto:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A`
- **Role:** `service_role` (precisa corrigir!)

## 🔍 Como Verificar Qual Key Está no Render

1. Vai ao Render Dashboard
2. Seleciona o serviço
3. Vai a **Environment**
4. Copia o valor da variável `SUPABASE_SERVICE_ROLE` (ou similar)
5. Vai a https://jwt.io
6. Cola a key e vê o payload
7. Se tiver `"role":"anon"` → Está ERRADO, precisa trocar
8. Se tiver `"role":"service_role"` → Está CORRETO ✅

## ⚠️ Por Que É Importante?

- **ANON_KEY no backend:** Não tem permissões suficientes para operações administrativas
- **SERVICE_ROLE_KEY no backend:** Tem todas as permissões necessárias para o backend funcionar

## 🎯 Depois de Corrigir

1. Faz restart/redeploy no Render
2. Testa: `https://vigia-crypto-1.onrender.com/alerts/health`
3. Deves ver `"has_key": true` e `"supabase_key_length": 208`
4. Testa no website: "Que tokens achas que vão ser listados?"
