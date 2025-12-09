# ✅ Solução: Render Usa Nome Diferente da Variável

## Problema Identificado

No Render está configurado:
- `SUPABASE_SERVICE_ROLE` ✅ (tem valor)

Mas o código procura:
- `SUPABASE_SERVICE_ROLE_KEY` ❌ (não encontra)

## Solução Aplicada

Atualizei o código para aceitar **ambos os nomes**:
- `SUPABASE_SERVICE_ROLE_KEY` (preferido)
- `SUPABASE_SERVICE_ROLE` (fallback para compatibilidade com Render)

## O Que Foi Alterado

1. **`backend/utils/supa.py`** - Função `_get_key()` agora tenta ambos os nomes
2. **`backend/Api/main.py`** - Carregamento inicial aceita ambos
3. **`backend/Api/routes/alerts.py`** - Todos os `os.getenv()` aceitam ambos

## Próximos Passos

### Opção 1: Manter Como Está (Recomendado)
- O código já funciona com `SUPABASE_SERVICE_ROLE` no Render
- Não precisas fazer nada!
- Faz deploy e testa

### Opção 2: Renomear no Render (Para Consistência)
1. Vai ao Render Dashboard
2. Edita a variável `SUPABASE_SERVICE_ROLE`
3. Renomeia para `SUPABASE_SERVICE_ROLE_KEY`
4. Reinicia o serviço

## Teste

Depois do deploy, testa:
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

## Status

✅ **Código atualizado para aceitar ambos os nomes**
✅ **Compatível com configuração atual do Render**
✅ **Pronto para deploy**
