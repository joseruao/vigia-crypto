# Local Solana Scan

Run this when you are on the PC and want to refresh Supabase predictions outside Render.

```powershell
python run_local_solana_scan.py
```

It uses the same logic as the Render cron job:

- loads `.env` from the project root and `backend/.env`
- updates `exchange_tokens`
- scans Solana exchange wallets
- saves detected candidates into `transacted_tokens`

Required env vars:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `HELIUS_API_KEY` or `HELIUS_KEYS`

Notes:

- This can take a while because some wallets have thousands of transactions.
- Helius usage/rate limits still apply.
- Keep the PC awake while it runs.
