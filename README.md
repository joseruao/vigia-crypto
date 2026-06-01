# Crypto Intelligence Platform

AI-powered web application for cryptocurrency analysis, on-chain market intelligence, and automated alerts.

**Live:** [joseruao.com](https://joseruao.com)

---

## What it does

The platform combines three data sources into a single conversational interface — no dashboards, no menus. You ask a question, it routes it to the right engine and answers.

### 🏦 On-chain token discovery
Monitors hot wallets of major exchanges (Binance, Coinbase, Kraken, OKX, Gate.io, Bybit, Bitfinex, Gemini) on both Solana and Ethereum. When an exchange accumulates a token it hasn't listed yet, that's a potential early signal. Each holding is scored by liquidity, volume, and an ML model, and high-score finds trigger a Telegram alert automatically.

### 📊 Daily top-100 technical ranking
Every day, a scheduled job fetches the top 100 coins by market cap and runs full technical analysis: Wilder RSI, MACD(12,26,9), Bollinger Bands, SMA20/50/200, and pivot-based support/resistance levels. Results are queryable through the chat ("best opportunities today", "what's near support?", "what's cheap right now?").

### 🔍 Coin analysis on demand
Ask "analisa BTC" and get a full technical breakdown — support/resistance zones, RSI interpretation, trend direction, Fibonacci levels, stop loss and targets — plus an embedded TradingView chart automatically.

### 💬 AI chat assistant
General crypto questions go to GPT-4o-mini with a custom system prompt tuned for technical analysis, risk management, and on-chain market context. The intent routing is deterministic (no LLM decides where a question goes), which keeps latency low and costs predictable.

---

## Tech stack

| Layer | Stack |
|---|---|
| **Frontend** | Next.js 15 (App Router), React 19, Tailwind CSS 4, TypeScript |
| **Backend** | FastAPI, Python 3.13, Uvicorn |
| **Database** | Supabase (PostgreSQL + REST API) |
| **AI** | OpenAI GPT-4o-mini (streaming), scikit-learn Random Forest (token scoring) |
| **On-chain** | Helius RPC (Solana), Etherscan (Ethereum) |
| **Market data** | CoinGecko, CoinPaprika, Binance, Coinbase, Gate.io (public APIs) |
| **Charts** | TradingView embed widget |
| **Alerts** | Telegram Bot API |
| **Auth** | Supabase Auth (Google OAuth + email) |
| **Deploy** | Vercel (frontend) · Render (backend + cron jobs) |

---

## Architecture

```
User (browser)
    │
    ▼
Next.js Frontend  ──── intent routing in the client ────►  /alerts/ask
    │                                                       (listings, top100)
    │
    ▼  /chat/stream
FastAPI Backend
    │
    ├── Coin analysis  →  AdvancedCoinAnalyzer
    │                     (RSI · MACD · Fibonacci · S/R)
    │
    ├── Top-100 query  →  top100_technical_rankings (Supabase)
    │
    ├── Listing query  →  transacted_tokens (Supabase)
    │
    └── General chat   →  OpenAI GPT-4o-mini (streaming)

Supabase (PostgreSQL)
    ├── transacted_tokens           on-chain holdings + ML scores
    ├── top100_technical_rankings   daily technical rankings
    └── exchange_tokens             known listed tokens per exchange

Render cron jobs (daily)
    ├── top100 cron      fetch + analyze top-100 coins
    └── holders cron     scan exchange wallets (Solana + ETH)
                         → save to Supabase
                         → Telegram alert if score ≥ 80
```

---

## Key technical details

- **Streaming end-to-end** — FastAPI yields chunks, Next.js reads with `ReadableStream`; the UI updates in real time
- **Wilder RSI** — same smoothing method as TradingView (not the simpler naive average)
- **Pivot-based S/R** — swing high/low detection over 210-day history, not just 30-day min/max ±2%
- **ML scorer** — Random Forest trained on liquidity, volume, holder concentration, wallet value; outputs a 0–100 listing probability score
- **Multi-source candle cascade** — Coinbase → Gate.io → Binance → CoinGecko; if one is rate-limited, the next takes over automatically
- **Context-aware followups** — "is it good to buy?" after an analysis reuses the last result; "I bought at $5.5, should I sell?" extracts entry price and calculates P&L

---

## Running locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
# add your keys to .env (see below)
uvicorn Api.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
# set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
npm run dev
```

**Required environment variables**
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
OPENAI_API_KEY
HELIUS_API_KEY          # Solana RPC
ETHERSCAN_API_KEY       # Ethereum
TELEGRAM_BOT_TOKEN_SOL  # optional — for alerts
TELEGRAM_CHAT_ID_SOL    # optional — for alerts
FRONTEND_URL            # for CORS
```

---

## Project background

Started as a Telegram bot that sent alerts when exchange wallets accumulated tokens. No frontend, no database, no deploy — just a Python script running locally.

Grew into this over several months: learned Supabase, Vercel, and Render from scratch (deployment took the longest to get right), added the web interface, and integrated AI throughout. Heavy use of AI coding tools (Claude Code) for implementation — the product decisions, domain logic, and iteration were mine.

---

## Disclaimer

Informational only. Not financial advice.
