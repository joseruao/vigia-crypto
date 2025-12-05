# 🔍 Diagnóstico: "Supabase não configurado"

## Problema
Mesmo após as correções, ainda aparece "Supabase não configurado".

## ✅ Passos para Diagnosticar

### Passo 1: Verifica se a API está a correr

Abre um novo terminal e testa:
```bash
curl http://localhost:8000/alerts/health
```

Ou no browser:
```
http://localhost:8000/alerts/health
```

**Se não funcionar:** A API não está a correr. Inicia com:
```bash
cd backend/Api
python -m uvicorn main:app --reload --port 8000
```

### Passo 2: Verifica o endpoint de health

Quando a API estiver a correr, o `/alerts/health` deve retornar:
```json
{
  "ok": true,
  "supabase_url": true,
  "has_key": true,
  "supa_ok": true
}
```

**Se `supabase_url` ou `has_key` forem `false`:**
- O `.env` não está a ser carregado
- As variáveis não estão definidas

### Passo 3: Verifica o ficheiro .env

O ficheiro deve estar em:
- `backend/.env` OU
- `.env` (raiz do projeto)

**Formato correto:**
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
```

**⚠️ IMPORTANTE:**
- Sem espaços antes/depois do `=`
- Sem aspas (a menos que façam parte do valor)
- Uma variável por linha

### Passo 4: Verifica se python-dotenv está instalado

```bash
cd backend
python -c "import dotenv; print('✅ Instalado')"
```

Se der erro:
```bash
pip install python-dotenv
```

### Passo 5: REINICIA a API

**CRÍTICO:** Após qualquer alteração no `.env` ou no código, tens de **REINICIAR** a API:

1. **Para a API** (Ctrl+C)
2. **Reinicia:**
   ```bash
   cd backend/Api
   python -m uvicorn main:app --reload --port 8000
   ```

3. **Verifica os logs:** Quando a API inicia, deve aparecer:
   ```
   ✅ Carregado .env de: C:\Users\joser\vigia_crypto\backend\.env
   ```

### Passo 6: Testa diretamente

Executa:
```bash
cd backend
python test_supabase_config.py
```

Isto vai testar:
- Se a API está a correr
- Se as variáveis estão carregadas
- Se o endpoint `/alerts/ask` funciona

## 🐛 Problemas Comuns

### Problema 1: API não foi reiniciada
**Sintoma:** Alterações não têm efeito

**Solução:** Para e reinicia a API

### Problema 2: .env no local errado
**Sintoma:** `supabase_url: false` no health check

**Solução:** Move o `.env` para `backend/.env`

### Problema 3: Variáveis com espaços
**Sintoma:** Variáveis não são reconhecidas

**Solução:** Remove espaços antes/depois do `=`

### Problema 4: python-dotenv não instalado
**Sintoma:** `.env` não é carregado

**Solução:** `pip install python-dotenv`

## 📋 Checklist Final

- [ ] API está a correr (`http://localhost:8000` responde)
- [ ] `/alerts/health` retorna `supabase_url: true` e `has_key: true`
- [ ] Ficheiro `.env` existe em `backend/.env`
- [ ] `.env` tem `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` (sem espaços)
- [ ] `python-dotenv` está instalado
- [ ] API foi **REINICIADA** após alterações
- [ ] Logs da API mostram "✅ Carregado .env"

## 🎯 Próximos Passos

1. **Reinicia a API** (se ainda não o fizeste)
2. **Testa `/alerts/health`** no browser
3. **Partilha o resultado** do health check
4. **Partilha os logs** da API quando inicia

Com esta informação consigo identificar exatamente onde está o problema!

