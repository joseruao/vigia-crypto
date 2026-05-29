# Local Solana Scan

Run this when you are on the PC and want to refresh Supabase predictions outside Render.

```powershell
python run_local_solana_scan.py
```

For a wider refresh, for example the last 7 days:

```powershell
python run_local_solana_scan.py --hours 168
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
- Start with `--hours 48` or `--hours 72` if you want a lighter run; use `--hours 168` when you want a wider refresh.
