# 🔧 Solução: Problema com .env.local

## Problema Identificado

Há um ficheiro `.env.local` na raiz que pode estar a **sobrescrever** o `.env` correto!

Quando o `python-dotenv` carrega múltiplos ficheiros `.env*`, o último ficheiro carregado **sobrescreve** os valores anteriores. Se o `.env.local` tiver `SUPABASE_SERVICE_ROLE_KEY=` (vazio), vai sobrescrever o valor correto do `.env`.

## ✅ Solução

### Opção 1: Verificar e Corrigir .env.local (Recomendado)

1. **Abre o ficheiro `.env.local` na raiz**
2. **Verifica se tem `SUPABASE_SERVICE_ROLE_KEY`**
3. **Se tiver e estiver vazio ou incorreto:**
   - Adiciona o valor correto:
     ```
     SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
     ```
   - Ou remove a linha completamente

### Opção 2: Apagar .env.local

Se não precisares do `.env.local`, podes apagá-lo:

```powershell
cd c:\Users\joser\vigia_crypto
Remove-Item .env.local
```

### Opção 3: Garantir Ordem Correta

Já atualizei o código para **NÃO carregar `.env.local`** automaticamente. Agora só carrega:
1. `backend/.env`
2. `.env` (raiz)

## 🎯 Depois de Corrigir

1. **Reinicia a API:**
   ```powershell
   cd backend
   .\start_api_com_env.ps1
   ```

2. **Testa novamente:**
   - No frontend: "Que tokens achas que vão ser listados?"
   - Deve funcionar agora!

## 💡 Por Que Isto Acontece?

O `python-dotenv` carrega ficheiros nesta ordem (se existirem):
1. `.env`
2. `.env.local` ← **Sobrescreve** o `.env`!

Se `.env.local` tiver `SUPABASE_SERVICE_ROLE_KEY=` (vazio), vai sobrescrever o valor correto do `.env`.

## 🔍 Verificar

Executa:
```bash
cd backend
python verificar_todos_env.py
```

Isto vai mostrar todos os ficheiros `.env*` e o que cada um contém.
