# Crypto Intelligence Platform — joseruao.com

A full-stack crypto market intelligence tool that monitors exchange wallets on-chain, ranks the top 100 coins with daily technical analysis, and lets users query everything through a conversational AI interface.

**Live:** [joseruao.com](https://joseruao.com)

---

## What it does

**On-chain listing prediction**
Monitors known hot wallets of major exchanges (Binance, Coinbase, Kraken, OKX, Gate.io, Bybit, Bitfinex, Gemini) on both Solana and Ethereum. When an exchange accumulates a token it hasn't listed yet, that's a potential early signal. The platform scores each holding by liquidity, volume, and ML features, and surfaces the top candidates through the chat interface.

**Daily top-100 technical ranking**
Every day, a cron job fetches the top 100 coins by market cap and runs full technical analysis on each: Wilder RSI, MACD(12,26,9), Bollinger Bands(20,2), SMA20/50/200, and pivot-based support/resistance. Coins are scored, sorted, and queryable ("best opportunities today", "what's cheap now?", "near support").

**Conversational AI interface**
Users interact entirely through chat. The assistant auto-routes questions — coin analysis requests go to a technical analysis engine, listing questions hit the on-chain database, top-100 questions return the daily ranking. General questions about crypto concepts go to GPT-4o-mini. No menus, no dashboards — just questions and answers.

---

## Tech stack

| Layer | Stack |
|---|---|
| **Frontend** | Next.js 15 (App Router), React 19, Tailwind CSS 4 |
| **Backend** | FastAPI (Python 3.13), Uvicorn, Pydantic |
| **Database** | Supabase (PostgreSQL + REST API) |
| **AI** | OpenAI GPT-4o-mini (streaming chat), custom ML classifier (scikit-learn Random Forest) |
| **On-chain data** | Helius RPC (Solana), Etherscan (Ethereum) |
| **Market data** | CoinGecko, CoinPaprika, Binance, Coinbase, Gate.io public APIs |
| **Auth** | Supabase Auth (Google OAuth + email) |
| **Deployment** | Vercel (frontend) · Render (backend + cron jobs) |

---

## Architecture

```
User (browser)
    │
    ▼
Next.js Frontend (Vercel)
    │  POST /chat/stream    POST /alerts/ask
    ▼                       ▼
FastAPI Backend (Render)
    │
    ├── Intent classifier
    │     ├── Coin analysis   → AdvancedCoinAnalyzer (RSI, MACD, Fib, S/R)
    │     ├── Top100 query    → top100_technical_rankings (Supabase)
    │     ├── Listing query   → transacted_tokens (Supabase)
    │     └── General chat    → OpenAI GPT-4o-mini (streaming)
    │
Supabase (PostgreSQL)
    ├── transacted_tokens          — on-chain holdings with ML scores
    ├── top100_technical_rankings  — daily technical rankings
    └── exchange_tokens            — known listed tokens per exchange

Render Cron Jobs (daily)
    ├── vigia-solana-pro-cron   — top100 daily rankings
    └── holders-cron            — exchange wallet monitoring (Solana + ETH)
```

---

## Key features

- **Streaming chat** — responses stream token by token; no waiting for the full answer
- **Multi-source candle data** — fetches from Coinbase → Gate.io → Binance → CoinGecko in cascade; handles rate limits and downtime gracefully
- **Wilder RSI** — proper smoothing (same as TradingView), not the naive simple-average version
- **MACD(12,26,9)** — EMA-based, with bullish/bearish signal classification and histogram momentum
- **Pivot-based support/resistance** — finds actual swing highs/lows over 210 days, not just 30-day min/max ±2%
- **ML listing scorer** — Random Forest trained on on-chain features (liquidity, volume, holder concentration, wallet value) to estimate listing probability
- **Context-aware followups** — "is it good to buy?" after an analysis uses the last analysis result; "comprei a 5.5, devo vender?" extracts entry price and calculates P&L automatically
- **Deduplication** — on-chain signals are deduplicated by token+exchange+time window to avoid noise

---

## Project structure

```
vigia-crypto/
├── backend/
│   ├── Api/
│   │   ├── main.py                   # FastAPI app, chat endpoint, intent routing
│   │   ├── routes/
│   │   │   ├── alerts.py             # /alerts/ask — top100, listings, holdings
│   │   │   └── coin_analysis.py      # /coin/analyze
│   │   └── services/
│   │       ├── chat_helpers.py       # Intent classifiers, formatters, response generators
│   │       └── crypto_tools.py       # Coin analysis wrapper
│   ├── analisegrafica/
│   │   └── coin_analysis.py          # AdvancedCoinAnalyzer (RSI, MACD, Fibonacci, S/R)
│   ├── dailyworker/
│   │   ├── top100_rankings_worker.py # Daily technical analysis of top 100 coins
│   │   └── daily_holdings_worker.py  # Exchange wallet monitoring (Solana + Ethereum)
│   └── utils/
│       └── supa.py                   # Supabase REST client with retry logic
├── frontend/
│   └── src/
│       ├── app/                      # Next.js App Router pages + API routes
│       ├── components/
│       │   ├── ChatWindow.tsx        # Main chat UI with streaming + intent routing
│       │   ├── Sidebar.tsx           # Conversation history (localStorage)
│       │   └── Suggestions.tsx       # Context-aware quick-action buttons
│       └── lib/
│           ├── useChatHistory.ts     # Conversation state management
│           └── supabaseClient.ts     # Auth client
└── render.yaml                       # Render deployment config
```

---

## Running locally

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create .env with the vars listed below
uvicorn Api.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
# create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

**Required environment variables**
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
OPENAI_API_KEY=
HELIUS_API_KEY=        # Solana RPC via Helius
ETHERSCAN_API_KEY=     # Ethereum wallet monitoring
FRONTEND_URL=          # for CORS allow-list
```

---

## Challenges worth mentioning

**On-chain data is noisy.** Exchange wallets hold thousands of tokens. Getting a useful signal required combining ML scoring, liquidity/volume thresholds per exchange, deduplication by time window, and filtering against a database of tokens already listed on each exchange.

**Streaming across the stack.** FastAPI yields chunks, Next.js reads with `ReadableStream`, and both sides need to handle connection aborts, Render cold starts, and partial responses without breaking the UI state.

**Technical indicators without heavy dependencies.** Implementing Wilder RSI, EMA-based MACD, Bollinger Bands, and pivot swing detection in pure Python (no pandas in the cron worker) forced a thorough understanding of the underlying maths, not just library calls.

**Multi-source data resilience.** Any single market data API can be rate-limited or go down. The cascade (Coinbase → Gate.io → Binance → CoinGecko) with per-source error handling keeps analysis running continuously.

**Intent routing at the application layer.** There's no LLM deciding where each question goes — a deterministic classifier in the frontend sends requests to the right endpoint before they even hit the backend. This keeps latency low and costs predictable.
