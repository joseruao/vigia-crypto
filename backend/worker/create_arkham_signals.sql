create table if not exists public.arkham_signals (
  id bigserial primary key,
  signal_key text not null unique,
  entity text not null,
  entity_type text not null check (entity_type in ('exchange', 'smart_money')),
  exchange text,
  token text not null,
  token_address text,
  chain text,
  amount numeric,
  value_usd numeric,
  previous_value_usd numeric,
  value_delta_usd numeric,
  value_delta_pct numeric,
  previous_amount numeric,
  amount_delta numeric,
  signal_direction text,
  market_cap_usd numeric,
  liquidity_usd numeric,
  position_pct numeric,
  liquidity_pct numeric,
  score numeric,
  exchange_count integer default 1,
  type text,
  signature text,
  pair_url text,
  analysis_text text,
  ts timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.arkham_signals add column if not exists market_cap_usd numeric;
alter table public.arkham_signals add column if not exists liquidity_usd numeric;
alter table public.arkham_signals add column if not exists position_pct numeric;
alter table public.arkham_signals add column if not exists liquidity_pct numeric;
alter table public.arkham_signals add column if not exists exchange_count integer default 1;
alter table public.arkham_signals add column if not exists previous_value_usd numeric;
alter table public.arkham_signals add column if not exists value_delta_usd numeric;
alter table public.arkham_signals add column if not exists value_delta_pct numeric;
alter table public.arkham_signals add column if not exists previous_amount numeric;
alter table public.arkham_signals add column if not exists amount_delta numeric;
alter table public.arkham_signals add column if not exists signal_direction text;

create index if not exists arkham_signals_entity_type_score_idx
  on public.arkham_signals (entity_type, score desc, ts desc);

create index if not exists arkham_signals_position_pct_idx
  on public.arkham_signals (entity_type, position_pct desc);

create index if not exists arkham_signals_token_idx
  on public.arkham_signals (token);

create index if not exists arkham_signals_entity_idx
  on public.arkham_signals (entity);

create index if not exists arkham_signals_direction_idx
  on public.arkham_signals (entity_type, signal_direction, ts desc);

create index if not exists arkham_signals_value_delta_idx
  on public.arkham_signals (entity_type, value_delta_usd desc);

alter table public.arkham_signals enable row level security;

drop policy if exists "service_role_manage_arkham_signals" on public.arkham_signals;
create policy "service_role_manage_arkham_signals"
  on public.arkham_signals
  for all
  to service_role
  using (true)
  with check (true);

grant all on table public.arkham_signals to service_role;
grant usage, select on sequence public.arkham_signals_id_seq to service_role;
