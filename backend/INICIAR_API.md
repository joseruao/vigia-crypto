# 🚀 Como Iniciar a API

## Erro -102: Connection Refused

O erro `-102` significa que a API não está a correr. Precisas iniciar a API primeiro.

## 📋 Passo a Passo

### Opção 1: Terminal (Recomendado)

```bash
cd backend/Api
python -m uvicorn main:app --reload --port 8000
```

Ou se tiveres uvicorn instalado globalmente:
```bash
cd backend/Api
uvicorn main:app --reload --port 8000
```

### Opção 2: Verificar se Está a Correr

Depois de iniciar, deves ver algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Opção 3: Testar

Abre no browser:
- http://localhost:8000/
- http://localhost:8000/alerts/predictions
- http://localhost:8000/alerts/health

## ⚠️ Problemas Comuns

### Porta 8000 já em uso

Se aparecer erro de porta ocupada:
```bash
# Usa outra porta
uvicorn main:app --reload --port 8001
```

Depois atualiza o frontend para usar `http://localhost:8001`

### Módulos não encontrados

Se aparecer erro de import:
```bash
pip install -r backend/requirements.txt
```

Ou:
```bash
pip install fastapi uvicorn python-dotenv requests supabase
```

## 🔍 Verificar se Está a Correr

Depois de iniciar, testa:
```bash
curl http://localhost:8000/
```

Ou abre no browser: http://localhost:8000/

Deves ver: `{"ok":true,"service":"vigia-backend"}`
