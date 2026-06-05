alter table public.candidate_wallets
  add column if not exists last_activity_ts timestamptz,
  add column if not exists last_activity_value_usd numeric default 0,
  add column if not exists last_activity_flow text,
  add column if not exists last_activity_token text,
  add column if not exists last_activity_chain text,
  add column if not exists last_activity_counterparty text,
  add column if not exists last_activity_counterparty_label text,
  add column if not exists last_activity_tx text,
  add column if not exists activity_checked_at timestamptz;

create index if not exists idx_candidate_wallets_last_activity_ts
  on public.candidate_wallets (last_activity_ts desc);

create index if not exists idx_candidate_wallets_last_activity_value
  on public.candidate_wallets (last_activity_value_usd desc);
