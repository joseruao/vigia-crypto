create table if not exists public.top100_technical_rankings (
  date date not null,
  rank integer not null,
  coin_id text,
  symbol text not null,
  name text,
  price double precision,
  market_cap double precision,
  volume_24h double precision,
  change_24h double precision,
  change_7d double precision,
  change_30d double precision,
  volume_ratio double precision,
  score double precision,
  risk text,
  signal text,
  rationale text,
  ts timestamptz default now(),
  primary key (date, symbol)
);

create index if not exists top100_technical_rankings_score_idx
  on public.top100_technical_rankings (score desc);

create index if not exists top100_technical_rankings_ts_idx
  on public.top100_technical_rankings (ts desc);

alter table public.top100_technical_rankings
  add column if not exists rsi double precision,
  add column if not exists trend text,
  add column if not exists trend_strength double precision,
  add column if not exists volatility double precision,
  add column if not exists volume_ratio_20d double precision,
  add column if not exists support double precision,
  add column if not exists resistance double precision,
  add column if not exists current_position double precision,
  add column if not exists entry_zone text,
  add column if not exists stop_loss text,
  add column if not exists targets jsonb,
  add column if not exists technical_action text,
  add column if not exists technical_confidence text;
