# 🧪 Como Testar Agora

## Passo 1: Executa o Teste Rápido

```bash
cd backend
python teste_rapido.py
```

Este script vai mostrar:
- ✅ Se o `.env` existe
- ✅ Se as variáveis estão no `.env`
- ✅ Se são carregadas corretamente
- ✅ Se a API consegue aceder às variáveis

**Partilha o output completo deste comando!**

## Passo 2: Verifica o .env Manualmente

Abre o ficheiro `backend\.env` e verifica:

1. **Tem esta linha EXATA?**
   ```
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...
   ```

2. **Sem espaços antes/depois do `=`?**
   - ✅ Correto: `SUPABASE_SERVICE_ROLE_KEY=valor`
   - ❌ Errado: `SUPABASE_SERVICE_ROLE_KEY = valor`

3. **Valor não está vazio?**
   - Deve ter ~200 caracteres

4. **Apenas UMA linha com `SUPABASE_SERVICE_ROLE_KEY`?**
   - Se houver múltiplas, remove as duplicadas

## Passo 3: Reinicia a API

**IMPORTANTE:** Após qualquer alteração no `.env`, tens de **REINICIAR** a API:

1. **Para a API** (Ctrl+C no terminal onde está a correr)
2. **Reinicia:**
   ```powershell
   cd backend
   .\start_api.ps1
   ```

3. **Verifica os logs** quando a API inicia:
   ```
   ✅ Carregado .env de: ...
   SUPABASE_URL: ✅ (XX chars)
   SUPABASE_SERVICE_ROLE_KEY: ✅ (XX chars)  ← Deve aparecer ✅
   ```

## Passo 4: Testa o Health Check

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

Se `has_key` for `false`, o problema está no `.env` ou no carregamento.

## Passo 5: Testa no Frontend

No frontend, pergunta: "Que tokens achas que vão ser listados?"

Se ainda aparecer "Supabase não configurado", partilha:
- O output do `teste_rapido.py`
- Os logs da API quando inicia
- O resultado do `/alerts/health`

## 🔧 Fix do Next.js Vulnerável

Também atualizei o Next.js para a versão segura (15.5.7). Para aplicar:

```bash
cd frontend
npm install
```

Depois faz commit e push para o Vercel atualizar automaticamente.
