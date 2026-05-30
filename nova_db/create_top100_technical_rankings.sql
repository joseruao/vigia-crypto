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
