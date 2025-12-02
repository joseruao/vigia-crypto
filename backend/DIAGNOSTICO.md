# 🔍 Diagnóstico - Tabela Vazia

## ✅ Resultado do Teste

O teste mostrou que:
- ✅ Conexão com Supabase funciona (200 OK)
- ✅ Variáveis de ambiente configuradas
- ❌ **Tabela `transacted_tokens` está VAZIA** (0 holdings)

## 🎯 Problema Identificado

A tabela está vazia porque o **worker não está a inserir dados**. Isso explica:
- Porque o PredictionsPanel não mostra nada
- Porque a API pode parecer "travada" (na verdade retorna lista vazia rapidamente)

## 🔧 Soluções

### Opção 1: Testar Inserção Manual

Testa se consegues inserir dados manualmente:

```bash
cd backend
python test_insert_data.py
```

Ou via API (se estiver a correr):
```bash
curl -X POST http://localhost:8000/alerts/test-insert
```

### Opção 2: Verificar se o Worker Está a Correr

O worker precisa estar a correr para inserir dados. Verifica:

```bash
cd backend/worker
python vigia_solana_pro_supabase.py
```

**Nota:** O worker precisa de:
- `HELIUS_API_KEY` configurado
- `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` configurados
- Conexão à internet para aceder ao Helius e DexScreener

### Opção 3: Verificar Logs do Worker

Se o worker estiver a correr mas não inserir dados, verifica os logs:
- Procura por mensagens como "✅ Alert salvo"
- Procura por erros como "❌ Erro ao salvar alert"

### Opção 4: Verificar no Render

Se o worker está no Render como Cron Job:
1. Vai ao Render Dashboard
2. Verifica os logs do worker
3. Verifica se está configurado para correr periodicamente
4. Verifica se as variáveis de ambiente estão configuradas

## 📊 Próximos Passos

1. **Executa `test_insert_data.py`** para verificar se a inserção funciona
2. **Verifica se o worker está a correr** (localmente ou no Render)
3. **Verifica os logs do worker** para ver se há erros
4. **Se necessário, executa o worker manualmente** para gerar dados de teste

## 🐛 Se a Inserção Falhar

Se `test_insert_data.py` falhar, pode ser:
- Tabela não existe ou tem estrutura diferente
- Permissões incorretas (Service Role Key sem permissões de escrita)
- Schema da tabela não corresponde aos dados

Verifica no Supabase Dashboard:
- Table Editor > `transacted_tokens` > ver estrutura
- Settings > API > verificar Service Role Key
