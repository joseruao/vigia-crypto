create table if not exists public.token_prelisting_wallets (
  id bigserial primary key,
  token text not null,
  token_id text not null,
  listing_exchange text,
  listing_ts timestamptz,
  window_start timestamptz,
  window_end timestamptz,
  address text not null,
  chains text[] default '{}',
  first_seen timestamptz,
  last_seen timestamptz,
  total_in_usd numeric default 0,
  max_transfer_usd numeric default 0,
  pre_listing_out_usd numeric default 0,
  post_listing_out_usd numeric default 0,
  balance_usd numeric default 0,
  tx_count integer default 0,
  score integer default 0,
  classification text,
  source_entities text[] default '{}',
  labels text[] default '{}',
  raw jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (token_id, address)
);

create index if not exists idx_token_prelisting_wallets_token_score
  on public.token_prelisting_wallets (token_id, score desc, total_in_usd desc);

create index if not exists idx_token_prelisting_wallets_listing_ts
  on public.token_prelisting_wallets (listing_ts desc);

create index if not exists idx_token_prelisting_wallets_address
  on public.token_prelisting_wallets (address);

alter table public.token_prelisting_wallets enable row level security;

drop policy if exists "service_role_manage_token_prelisting_wallets" on public.token_prelisting_wallets;
create policy "service_role_manage_token_prelisting_wallets"
  on public.token_prelisting_wallets
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "authenticated_read_token_prelisting_wallets" on public.token_prelisting_wallets;
create policy "authenticated_read_token_prelisting_wallets"
  on public.token_prelisting_wallets
  for select
  to authenticated
  using (true);

grant all on table public.token_prelisting_wallets to service_role;
grant usage, select on sequence public.token_prelisting_wallets_id_seq to service_role;
grant select on table public.token_prelisting_wallets to authenticated;
