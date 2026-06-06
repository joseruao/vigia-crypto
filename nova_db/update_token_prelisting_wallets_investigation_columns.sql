alter table public.token_prelisting_wallets
  add column if not exists pre_listing_retention_pct numeric default 0,
  add column if not exists post_listing_destinations jsonb default '[]'::jsonb,
  add column if not exists investigation_status text default 'candidate',
  add column if not exists investigation_note text;

create index if not exists idx_token_prelisting_wallets_retention_score
  on public.token_prelisting_wallets (token_id, pre_listing_retention_pct desc, score desc);

create index if not exists idx_token_prelisting_wallets_investigation_status
  on public.token_prelisting_wallets (investigation_status);
