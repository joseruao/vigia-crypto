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

create index if not exists arkham_signals_entity_type_score_idx
  on public.arkham_signals (entity_type, score desc, ts desc);

create index if not exists arkham_signals_token_idx
  on public.arkham_signals (token);

create index if not exists arkham_signals_entity_idx
  on public.arkham_signals (entity);
