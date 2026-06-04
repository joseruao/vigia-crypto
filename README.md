# Exchange Wallet Radar

Live demo: [joseruao.com](https://joseruao.com)

Exchange Wallet Radar is a crypto intelligence dashboard that tracks exchange wallet activity, detects tokens that are not listed on that exchange yet, scores potential listing signals, and sends alerts for high-confidence candidates.

Contact: [jose@joseruao.com](mailto:jose@joseruao.com)

---

## What It Does

- Monitors exchange wallets across Solana and EVM chains.
- Filters for tokens that appear in an exchange wallet before being listed on that same exchange.
- Scores each candidate using wallet value, liquidity, volume, market data, and listing heuristics.
- Displays a live listing radar, top-100 technical setups, and an AI chat interface.
- Sends Telegram alerts for strong listing candidates.

---

## Live Product Areas

### Listing Radar

Shows tokens detected in monitored exchange wallets while still unlisted on that exchange. Each card includes:

- token, exchange, and chain
- listing score
- value held in the wallet
- liquidity and 24h volume
- DexScreener and CoinGecko links

### Top100 Technical Ranking

A scheduled worker analyzes top market-cap coins and stores daily technical rankings with:

- price
- technical score
- RSI
- support/resistance
- trend context
- risk and entry zone

### Coin Analysis

The chat supports prompts like `analisa BTC` and returns a technical breakdown with:

- current price
- RSI and trend
- support/resistance
- stop and targets
- risk context
- TradingView chart embed

### Telegram Alerts

High-confidence listing candidates can trigger Telegram alerts automatically. Telegram is used as an alerting channel, while the website remains the main dashboard.

---

## Why Entity-Level Data Matters

Better entity labels, historical balance changes, and wallet clustering would improve signal quality by:

- validating whether a wallet really belongs to an exchange
- detecting fresh balance increases instead of static holdings
- reducing false positives from wrappers, staked assets, and operational wallets
- separating listing-like accumulation from normal exchange inventory

---

## Tech Stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.13, Uvicorn |
| Database | Supabase PostgreSQL + REST |
| AI | OpenAI GPT-4o-mini, deterministic intent routing |
| On-chain | Helius RPC, Etherscan-compatible APIs |
| Market Data | CoinGecko, CoinPaprika, Coinbase, Gate.io, Binance fallbacks |
| Charts | TradingView embed |
| Alerts | Telegram Bot API |
| Deploy | Vercel frontend, Render backend and cron jobs |

---

## Architecture

```text
Browser
  |
  |-- Next.js dashboard
  |     |-- Listing Radar
  |     |-- Top100 panel
  |     |-- AI chat
  |
  |-- FastAPI backend
        |-- /alerts/predictions
        |-- /alerts/top100
        |-- /alerts/ask
        |-- /chat/stream
        |
        |-- Supabase
        |     |-- transacted_tokens
        |     |-- top100_technical_rankings
        |     |-- exchange_tokens
        |
        |-- Scheduled workers
              |-- top100 technical ranking
              |-- exchange wallet scanner
              |-- Telegram alerts
```

---

## Local Development

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn Api.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Useful environment variables:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
OPENAI_API_KEY
HELIUS_API_KEY
ETHERSCAN_API_KEY
TELEGRAM_BOT_TOKEN_SOL
TELEGRAM_CHAT_ID_SOL
NEXT_PUBLIC_API_URL
FRONTEND_URL
```

---

## Notes

The hosted backend may take a few seconds to wake up on the first request because it runs on Render.

This project is informational only and is not financial advice. Crypto markets are risky, and all signals should be independently verified.
