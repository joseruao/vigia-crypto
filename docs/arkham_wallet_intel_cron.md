# Arkham Wallet Intel Cron

Private Railway cron for candidate wallet discovery. This job writes to
`candidate_wallets` and should not be exposed directly in the public UI.

## Railway command

```bash
python backend/worker/arkham_wallet_intel_runner.py
```

## Required variables

- `ARKHAM_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE`

Use a real Supabase `service_role` key. The runner will fail fast if an anon key
is used for writes.

## Optional controls

Broad scan:

- `ARKHAM_INTEL_BROAD_ENTITIES=all`
- `ARKHAM_INTEL_BROAD_FLOW=out`
- `ARKHAM_INTEL_BROAD_TRANSFER_LIMIT=10`
- `ARKHAM_INTEL_BROAD_DEPTH=2`
- `ARKHAM_INTEL_BROAD_MAX_SECOND_HOP=3`

Deep scan:

- `ARKHAM_INTEL_RUN_DEEP=1`
- `ARKHAM_INTEL_DEEP_ENTITIES=galaxy-digital,multicoin-capital,a16z`
- `ARKHAM_INTEL_DEEP_FLOW=both`
- `ARKHAM_INTEL_DEEP_TRANSFER_LIMIT=20`
- `ARKHAM_INTEL_DEEP_DEPTH=3`
- `ARKHAM_INTEL_DEEP_MAX_SECOND_HOP=5`

Activity refresh:

- `ARKHAM_INTEL_ACTIVITY_LIMIT=50`
- `ARKHAM_INTEL_ACTIVITY_MIN_VALUE_USD=50000`
- `ARKHAM_INTEL_ACTIVITY_TRANSFER_LIMIT=25`

