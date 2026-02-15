# ⏱️ Solução: Timeout no Deploy do Render

## Problema

O build foi bem-sucedido mas o deploy deu timeout:
```
==> Build successful 🎉
==> Deploying...
==> Timed Out
```

## Possíveis Causas

1. **Serviço demora muito a iniciar** - O Render espera que o serviço responda em X segundos
2. **Health check falha** - O Render verifica se o serviço está saudável
3. **Problema temporário do Render** - Pode ser um problema do lado deles

## ✅ Soluções

### Solução 1: Verificar Health Check (Recomendado)

O Render precisa de um endpoint de health check que responda rapidamente.

1. **Verifica se o endpoint `/alerts/health` existe e responde rápido:**
   ```
   https://vigia-crypto-1.onrender.com/alerts/health
   ```

2. **Se não existir ou demorar muito, adiciona um endpoint simples na raiz:**
   - O endpoint `/` já existe e retorna `{"ok":true,"service":"vigia-backend"}`
   - Isto deve ser suficiente

### Solução 2: Configurar Health Check no Render

1. Vai ao **Render Dashboard**
2. Seleciona o teu serviço
3. Vai a **Settings → Health Check**
4. Configura:
   - **Path:** `/` ou `/alerts/health`
   - **Interval:** 10 segundos
   - **Timeout:** 5 segundos
   - **Grace Period:** 30 segundos

### Solução 3: Aumentar Timeout de Deploy

1. Vai ao **Render Dashboard**
2. Seleciona o teu serviço
3. Vai a **Settings → Advanced**
4. Aumenta o **Deploy Timeout** para 180 segundos (ou mais)

### Solução 4: Verificar Logs

1. Vai ao **Render Dashboard**
2. Seleciona o teu serviço
3. Vai a **Logs**
4. Verifica se há erros durante o startup
5. Procura por:
   - Erros de importação
   - Erros de conexão ao Supabase
   - Erros de inicialização

### Solução 5: Simplificar Startup

Se o serviço demora muito a iniciar, pode ser porque está a fazer muitas operações no startup. Verifica:

1. **Não fazer operações pesadas no startup**
2. **Carregar variáveis de ambiente de forma assíncrona**
3. **Não fazer conexões de base de dados no startup**

## 🔍 Diagnóstico

### Passo 1: Verificar se o Serviço Está a Correr

Mesmo com timeout, o serviço pode estar a correr. Testa:

```
https://vigia-crypto-1.onrender.com/
https://vigia-crypto-1.onrender.com/alerts/health
```

Se responderem, o serviço está a correr apesar do timeout!

### Passo 2: Verificar Logs do Render

Os logs podem mostrar o que está a acontecer durante o startup.

### Passo 3: Tentar Deploy Manual

1. Vai ao **Render Dashboard**
2. Seleciona o teu serviço
3. Clica em **Manual Deploy**
4. Aguarda e verifica os logs

## 🎯 Solução Rápida

**Tenta isto primeiro:**

1. Vai ao **Render Dashboard**
2. Seleciona o serviço
3. Clica em **Manual Deploy** → **Deploy latest commit**
4. Aguarda e verifica os logs

Se o serviço já estava a correr antes, pode ser apenas um problema temporário. O timeout não significa que o serviço não está a funcionar!

## 📝 Nota

Se o serviço responder aos endpoints mesmo após o timeout, significa que está a funcionar. O timeout pode ser apenas um problema de comunicação entre o Render e o serviço durante o deploy.
