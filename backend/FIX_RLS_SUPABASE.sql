-- ============================================================
-- FIX: Row Level Security (RLS) para tabela transacted_tokens
-- ============================================================
-- 
-- PROBLEMA: RLS está a bloquear inserções mesmo com Service Role Key
-- SOLUÇÃO: Desativar RLS ou criar políticas que permitam inserção
--
-- Executa este SQL no Supabase Dashboard > SQL Editor
-- ============================================================

-- Opção 1: DESATIVAR RLS (Mais Simples - Recomendado se não precisas de segurança por linha)
ALTER TABLE transacted_tokens DISABLE ROW LEVEL SECURITY;

-- ============================================================
-- OU
-- ============================================================

-- Opção 2: CRIAR POLÍTICAS RLS (Se quiseres manter RLS ativo)
-- Remove as políticas antigas se existirem
DROP POLICY IF EXISTS "Allow service role inserts" ON transacted_tokens;
DROP POLICY IF EXISTS "Allow service role selects" ON transacted_tokens;
DROP POLICY IF EXISTS "Allow service role updates" ON transacted_tokens;
DROP POLICY IF EXISTS "Allow service role deletes" ON transacted_tokens;

-- Criar políticas que permitem tudo para service_role
CREATE POLICY "Allow service role inserts" ON transacted_tokens
FOR INSERT
TO service_role
WITH CHECK (true);

CREATE POLICY "Allow service role selects" ON transacted_tokens
FOR SELECT
TO service_role
USING (true);

CREATE POLICY "Allow service role updates" ON transacted_tokens
FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow service role deletes" ON transacted_tokens
FOR DELETE
TO service_role
USING (true);

-- ============================================================
-- VERIFICAR ESTADO
-- ============================================================
-- Executa isto para verificar se RLS está ativo:
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND tablename = 'transacted_tokens';

-- Ver políticas existentes:
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'transacted_tokens';
