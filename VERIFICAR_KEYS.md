# 🔑 Como Verificar Qual Key Estás a Usar

## Decodificar o JWT

As keys do Supabase são JWTs (JSON Web Tokens). Podes decodificar para ver qual é qual.

### Opção 1: Online (Mais Fácil)

1. Vai a: https://jwt.io
2. Cola a key no campo "Encoded"
3. Vê o "Payload" (parte do meio)
4. Procura por `"role"`:
   - Se for `"role":"anon"` → É **ANON_KEY**
   - Se for `"role":"service_role"` → É **SERVICE_ROLE_KEY**

### Opção 2: Python (Local)

```python
import base64
import json

# Cola a tua key aqui
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"

# Decodifica o payload (parte do meio)
parts = key.split('.')
payload = parts[1]

# Adiciona padding se necessário
padding = len(payload) % 4
if padding:
    payload += '=' * (4 - padding)

# Decodifica
decoded = base64.urlsafe_b64decode(payload)
data = json.loads(decoded)

print(f"Role: {data.get('role')}")
if data.get('role') == 'anon':
    print("✅ Esta é a ANON_KEY (para frontend)")
elif data.get('role') == 'service_role':
    print("✅ Esta é a SERVICE_ROLE_KEY (para backend)")
```

## 📋 Resumo das Keys

### ANON_KEY (Frontend - Vercel)
- **Nome no Vercel:** `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- **Role no JWT:** `"role":"anon"`
- **Uso:** Browser/frontend
- **Segurança:** Respeita RLS

### SERVICE_ROLE_KEY (Backend - Render)
- **Nome no Render:** `SUPABASE_SERVICE_ROLE` ou `SUPABASE_SERVICE_ROLE_KEY`
- **Role no JWT:** `"role":"service_role"`
- **Uso:** Servidor/backend
- **Segurança:** Bypassa RLS (cuidado!)

## ✅ Configuração Correta

### Vercel (Frontend)
```
NEXT_PUBLIC_SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc0Mzg4NjMsImV4cCI6MjA3MzAxNDg2M30.M30wZ79mQz2i3verO9JtyMn7JVE3yW1FjtcFJlnTvaw
```

### Render (Backend)
```
SUPABASE_SERVICE_ROLE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A
```

## ⚠️ Importante

- **NUNCA** uses `SERVICE_ROLE_KEY` no frontend (é inseguro!)
- **NUNCA** uses `ANON_KEY` no backend (não tem permissões suficientes)
- Cada uma tem o seu propósito específico
