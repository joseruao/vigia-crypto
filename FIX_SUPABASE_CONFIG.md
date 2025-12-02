# 🔧 Fix: "Supabase não configurado"

## Problema
Quando perguntas "Que tokens achas que vão ser listados?", aparece:
```
Supabase não configurado
```

## Causa
O código não estava a carregar o ficheiro `.env` com as variáveis `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.

## ✅ Solução Aplicada

### 1. Adicionado carregamento de .env no `main.py`
- Agora carrega automaticamente o `.env` quando a API inicia
- Procura em `backend/.env` e na raiz do projeto

### 2. Adicionado carregamento de .env no `supa.py`
- Garante que as variáveis estão disponíveis mesmo se importado antes do `main.py`

### 3. Adicionado carregamento de .env no `alerts.py`
- Garante que as rotas têm acesso às variáveis

## 📋 Próximos Passos

### Passo 1: Instalar python-dotenv (se necessário)

```bash
cd backend
pip install python-dotenv
```

Ou adiciona ao `requirements.txt`:
```
python-dotenv
```

### Passo 2: Verificar se o .env existe

O ficheiro deve estar em:
- `backend/.env` OU
- `.env` (na raiz do projeto)

E deve conter:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
```

### Passo 3: Reiniciar a API

**IMPORTANTE:** Para as alterações terem efeito, tens de **reiniciar a API**:

1. **Para a API** (Ctrl+C no terminal onde está a correr)
2. **Reinicia:**
   ```bash
   cd backend/Api
   python -m uvicorn main:app --reload --port 8000
   ```

### Passo 4: Testar

1. **Testa o endpoint de health:**
   ```
   http://localhost:8000/alerts/health
   ```
   
   Deve retornar:
   ```json
   {
     "ok": true,
     "supabase_url": true,
     "has_key": true
   }
   ```

2. **Testa a pergunta:**
   - No frontend, pergunta: "Que tokens achas que vão ser listados?"
   - Deve retornar uma lista de tokens em vez de "Supabase não configurado"

## 🐛 Debug

Se ainda não funcionar:

1. **Executa o teste:**
   ```bash
   cd backend
   python test_env_loading.py
   ```
   
   Deve mostrar:
   ```
   ✅ SUPABASE_URL: Definido
   ✅ SUPABASE_SERVICE_ROLE_KEY: Definido
   ✅ Supabase configurado corretamente!
   ```

2. **Verifica os logs da API:**
   Quando a API inicia, deve aparecer:
   ```
   ✅ Carregado .env de: C:\Users\joser\vigia_crypto\backend\.env
   ```

3. **Verifica se o .env está correto:**
   - Sem espaços antes/depois do `=`
   - Sem aspas desnecessárias
   - Valores completos (não truncados)

## ✅ Checklist

- [ ] `python-dotenv` instalado (`pip install python-dotenv`)
- [ ] Ficheiro `.env` existe em `backend/.env` ou raiz
- [ ] `.env` tem `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`
- [ ] API reiniciada após as alterações
- [ ] `/alerts/health` retorna `supabase_url: true` e `has_key: true`
- [ ] Pergunta "Que tokens achas que vão ser listados?" funciona
