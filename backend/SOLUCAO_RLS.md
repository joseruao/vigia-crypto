# 🔒 Solução: Row Level Security (RLS) no Supabase

## ❌ Problema Identificado

O erro `'new row violates row-level security policy for table "transacted_tokens"'` significa que:
- A tabela tem **Row Level Security (RLS) ativado**
- Não há uma política que permita inserção usando Service Role Key
- O worker também não consegue inserir dados por causa disto

## ✅ Solução: Desativar RLS ou Criar Política

Tens 2 opções:

### Opção 1: Desativar RLS (Mais Simples) ⚡

Se não precisas de RLS para esta tabela (já que usas Service Role Key):

1. Vai ao **Supabase Dashboard**
2. Seleciona o teu projeto
3. Vai a **Table Editor** > `transacted_tokens`
4. Clica no ícone de **"..."** (três pontos) no canto superior direito
5. Seleciona **"Disable RLS"** ou **"Disable Row Level Security"**

**Nota:** Se não vires esta opção, vai a **SQL Editor** e executa:

```sql
ALTER TABLE transacted_tokens DISABLE ROW LEVEL SECURITY;
```

### Opção 2: Criar Política RLS (Mais Seguro) 🔐

Se quiseres manter RLS ativado mas permitir inserção via Service Role:

1. Vai ao **Supabase Dashboard**
2. Vai a **SQL Editor**
3. Executa este SQL:

```sql
-- Criar política que permite inserção usando Service Role Key
CREATE POLICY "Allow service role inserts" ON transacted_tokens
FOR INSERT
TO service_role
WITH CHECK (true);

-- Criar política que permite leitura usando Service Role Key
CREATE POLICY "Allow service role selects" ON transacted_tokens
FOR SELECT
TO service_role
USING (true);
```

**Nota:** `service_role` é o role usado pela Service Role Key.

### Opção 3: Desativar RLS Apenas para Service Role (Recomendado) 🎯

A melhor solução é permitir que Service Role bypass RLS:

1. Vai ao **SQL Editor** no Supabase Dashboard
2. Executa:

```sql
-- Desativar RLS apenas para operações via Service Role
-- (Isto permite que o worker e a API funcionem normalmente)

-- Primeiro, verifica se RLS está ativo
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND tablename = 'transacted_tokens';

-- Se rowsecurity = true, cria políticas que permitem tudo para service_role
-- Ou simplesmente desativa RLS se não precisares de segurança por linha
ALTER TABLE transacted_tokens DISABLE ROW LEVEL SECURITY;
```

## 🔍 Verificar Estado Atual

Para verificar se RLS está ativo:

```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND tablename = 'transacted_tokens';
```

Se `rowsecurity = true`, RLS está ativo.

## 📋 Depois de Corrigir

1. **Testa novamente a inserção:**
   ```bash
   python backend/test_insert_data.py
   ```

2. **Se funcionar, verifica o worker:**
   - O worker também deve conseguir inserir dados agora
   - Executa o worker manualmente para testar

3. **Verifica no Supabase Dashboard:**
   - Table Editor > `transacted_tokens`
   - Deve aparecer o registo de teste

## ⚠️ Importante

- **Service Role Key** tem acesso total ao Supabase e bypass RLS normalmente
- Se mesmo assim está a falhar, pode ser que RLS esteja configurado de forma muito restritiva
- A solução mais simples é desativar RLS se não precisares de segurança por linha nesta tabela
