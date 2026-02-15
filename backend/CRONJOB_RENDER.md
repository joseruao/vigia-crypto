# ⏰ Como Configurar Cronjob no Render para vigia_solana_pro_supabase.py

## 📋 Visão Geral

O `vigia_solana_pro_supabase.py` é um worker que precisa de correr periodicamente para processar transações Solana e atualizar o Supabase.

## ✅ Solução: Render Cron Job

O Render suporta **Cron Jobs** que podem executar scripts periodicamente.

## 🔧 Passo a Passo

### Passo 1: Criar Novo Cron Job no Render

1. Vai ao **Render Dashboard**: https://dashboard.render.com
2. Clica em **New +** → **Cron Job**
3. Configura:

#### Configurações Básicas
- **Name:** `vigia-solana-worker` (ou nome à tua escolha)
- **Schedule:** `0 */6 * * *` (a cada 6 horas) ou `0 * * * *` (a cada hora)
- **Timezone:** `UTC`

#### Build & Start Commands
- **Root Directory:** `backend/worker` (ou `backend` se o script estiver na raiz)
- **Build Command:** 
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  python vigia_solana_pro_supabase.py
  ```

### Passo 2: Configurar Variáveis de Ambiente

No Cron Job, adiciona as mesmas variáveis que tens no Web Service:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE` (ou `SUPABASE_SERVICE_ROLE_KEY`)
- `HELIUS_API_KEY` (ou `HELIUS_KEYS`)
- `OPENAI_API_KEY` (se necessário)

### Passo 3: Schedule (Horários)

Exemplos de schedules:

- **A cada hora:** `0 * * * *`
- **A cada 6 horas:** `0 */6 * * *`
- **A cada 12 horas:** `0 */12 * * *`
- **Diariamente às 00:00:** `0 0 * * *`
- **A cada 30 minutos:** `*/30 * * * *`

**Formato Cron:** `minuto hora dia mês dia-da-semana`

### Passo 4: Verificar Logs

Depois de criar o Cron Job:

1. Vai ao **Logs** do Cron Job
2. Aguarda pela primeira execução
3. Verifica se está a funcionar corretamente

## 📝 Notas Importantes

### Diferença entre Web Service e Cron Job

- **Web Service:** Fica sempre a correr, responde a requests HTTP
- **Cron Job:** Executa periodicamente, termina após completar

### Requisitos do Script

O `vigia_solana_pro_supabase.py` deve:
- ✅ Ser executável como script standalone
- ✅ Não depender de servidor HTTP
- ✅ Terminar após completar o trabalho
- ✅ Ter tratamento de erros adequado

### Verificar se o Script Está Pronto

Testa localmente primeiro:
```bash
cd backend/worker
python vigia_solana_pro_supabase.py
```

Se funcionar localmente, deve funcionar no Render também.

## 🔍 Troubleshooting

### Problema: Cron Job não executa
- Verifica o schedule (formato cron)
- Verifica os logs para erros
- Verifica se as variáveis de ambiente estão configuradas

### Problema: Script falha
- Verifica os logs do Cron Job
- Verifica se todas as dependências estão no `requirements.txt`
- Verifica se as variáveis de ambiente estão corretas

### Problema: Timeout
- O Render tem um timeout padrão para Cron Jobs
- Se o script demorar muito, considera dividir em partes menores
- Ou aumenta o timeout nas configurações avançadas

## 🎯 Exemplo Completo

**Cron Job Name:** `vigia-solana-worker`

**Schedule:** `0 */6 * * *` (a cada 6 horas)

**Root Directory:** `backend/worker`

**Build Command:**
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command:**
```bash
python vigia_solana_pro_supabase.py
```

**Environment Variables:**
- `SUPABASE_URL=...`
- `SUPABASE_SERVICE_ROLE=...`
- `HELIUS_API_KEY=...`
- `OPENAI_API_KEY=...` (se necessário)

## ✅ Checklist

- [ ] Cron Job criado no Render
- [ ] Schedule configurado corretamente
- [ ] Variáveis de ambiente adicionadas
- [ ] Build command configurado
- [ ] Start command configurado
- [ ] Script testado localmente
- [ ] Logs verificados após primeira execução

