# 🔧 Corrigir Keys do Supabase

## ❌ Problema Identificado

### Vercel (Frontend) - ERRADO
- **Variável:** `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Valor atual:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A`
- **Problema:** Esta é a `service_role` key (ERRADO para frontend!)

### Render (Backend) - CORRETO ✅
- **Variável:** `SUPABASE_SERVICE_ROLE`
- **Valor:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A`
- **Status:** ✅ CORRETO (é `service_role`)

## ✅ Solução

### Passo 1: Corrigir Vercel

1. Vai ao **Vercel Dashboard**
2. Seleciona o teu projeto
3. Vai a **Settings → Environment Variables**
4. Encontra `NEXT_PUBLIC_SUPABASE_ANON_KEY`
5. **Edita** e substitui pelo valor correto:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc0Mzg4NjMsImV4cCI6MjA3MzAxNDg2M30.M30wZ79mQz2i3verO9JtyMn7JVE3yW1FjtcFJlnTvaw
```

6. **Guarda** e faz **redeploy**

### Passo 2: Verificar Render (Já está correto ✅)

O Render já tem a `service_role` key correta, não precisas alterar nada.

## 📋 Resumo das Keys Corretas

### Vercel (Frontend)
- **Variável:** `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Valor:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc0Mzg4NjMsImV4cCI6MjA3MzAxNDg2M30.M30wZ79mQz2i3verO9JtyMn7JVE3yW1FjtcFJlnTvaw`
- **Role:** `anon` ✅

### Render (Backend)
- **Variável:** `SUPABASE_SERVICE_ROLE` (ou `SUPABASE_SERVICE_ROLE_KEY`)
- **Valor:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A`
- **Role:** `service_role` ✅

## ⚠️ Por Que É Importante?

- **ANON_KEY no frontend:** Respeita Row Level Security (RLS), mais seguro
- **SERVICE_ROLE_KEY no frontend:** Bypassa RLS, **INSEGURO** - qualquer pessoa pode aceder a tudo!

## 🎯 Depois de Corrigir

1. Faz redeploy no Vercel
2. Testa o website
3. Verifica se funciona corretamente
