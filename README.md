# Crypto Intelligence Platform — joseruao.com

A personal project I built to monitor crypto markets — started as a simple Telegram bot and grew into a full web app with a conversational AI interface.

**Live:** [joseruao.com](https://joseruao.com)

---

## The idea

I wanted to know when major exchanges were quietly accumulating tokens before listing them. The theory: if Binance's wallet starts holding a token it doesn't list yet, that's a possible early signal.

Started with a Python script that sent Telegram alerts. Over time it grew into something with a proper frontend, a database, daily scheduled jobs, and a chat interface where you can ask questions in plain language.

---

## What it does

**Exchange wallet monitoring**
Tracks known on-chain wallets of Binance, Coinbase, Kraken, OKX, Gate.io, Bybit, and others on Solana and Ethereum. Flags tokens accumulating in those wallets that aren't listed there yet.

**Daily technical analysis of top 100 coins**
Every day a scheduled job fetches the top 100 coins and runs technical analysis: RSI, MACD, Bollinger Bands, moving averages, support and resistance. Results are queryable through the chat ("best setups today", "what's near support?").

**Chat interface**
Instead of dashboards and menus, everything is a question. The app figures out what you're asking and routes it to the right data source — on-chain holdings, the daily rankings, or a coin-specific analysis.

---

## Tech stack

| | |
|---|---|
| **Frontend** | Next.js 15, React 19, Tailwind CSS |
| **Backend** | FastAPI (Python), deployed on Render |
| **Database** | Supabase (PostgreSQL) |
| **AI** | OpenAI GPT-4o-mini for general chat |
| **On-chain data** | Helius (Solana RPC), Etherscan (Ethereum) |
| **Market data** | CoinGecko, Binance, Coinbase public APIs |
| **Auth** | Supabase Auth (Google + email) |
| **Deployment** | Vercel (frontend) + Render (backend + cron jobs) |

---

## How it's structured

```
frontend/   → Next.js chat interface
backend/
  Api/          → FastAPI endpoints
  dailyworker/  → scheduled jobs (top100 + wallet monitoring)
  analisegrafica/ → technical analysis (RSI, MACD, support/resistance)
  utils/        → Supabase client
```

---

## Running locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn Api.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install && npm run dev
```

**Env vars needed**
```
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
OPENAI_API_KEY
HELIUS_API_KEY        # Solana
ETHERSCAN_API_KEY     # Ethereum
FRONTEND_URL          # for CORS
```

---

## Honest notes

This project was built with heavy use of AI coding tools (Claude Code). I came in knowing Python basics and an idea — the technical implementation grew through a lot of iteration, debugging, and learning on the go.

What I genuinely contributed: the product decisions (what signals matter, what thresholds make sense, how the conversation should feel), the domain knowledge about how crypto listings work, and the persistence to keep iterating until it worked.

What I learned along the way: how APIs and databases talk to each other, how to deploy and keep a web app running, how streaming responses work, and a lot about on-chain data and technical analysis.
