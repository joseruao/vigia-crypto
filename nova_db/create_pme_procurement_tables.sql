-- AI Business Auditor / PME procurement MVP
-- Run in Supabase SQL editor when ready to persist catalogues and recommendations.

create extension if not exists pgcrypto;

create table if not exists pme_suppliers (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  reliability_score numeric(5,2),
  delivery_days numeric(6,2),
  payment_terms text,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists pme_catalog_uploads (
  id uuid primary key default gen_random_uuid(),
  supplier_id uuid references pme_suppliers(id) on delete set null,
  filename text not null,
  source_type text not null default 'manual_upload',
  uploaded_by uuid,
  uploaded_at timestamptz not null default now(),
  warnings jsonb not null default '[]'::jsonb
);

create table if not exists pme_catalog_items (
  id uuid primary key default gen_random_uuid(),
  upload_id uuid references pme_catalog_uploads(id) on delete cascade,
  supplier_id uuid references pme_suppliers(id) on delete set null,
  product text not null,
  description text,
  normalized_product text not null,
  quantity numeric(14,4) not null default 1,
  unit text not null default 'un',
  unit_price numeric(14,4) not null,
  total_price numeric(14,4),
  promotions text,
  notes text,
  commercial_value numeric(14,4) not null default 0,
  effective_unit_price numeric(14,4) not null,
  confidence text not null default 'medium',
  created_at timestamptz not null default now()
);

create index if not exists idx_pme_catalog_items_normalized_product
  on pme_catalog_items(normalized_product);

create index if not exists idx_pme_catalog_items_supplier
  on pme_catalog_items(supplier_id);

create table if not exists pme_commercial_terms (
  id uuid primary key default gen_random_uuid(),
  catalog_item_id uuid not null references pme_catalog_items(id) on delete cascade,
  type text not null,
  label text not null,
  quantity numeric(14,4) not null default 1,
  unit text,
  estimated_unit_value numeric(14,4) not null default 0,
  estimated_total_value numeric(14,4) not null default 0,
  confidence text not null default 'medium',
  raw_text text,
  created_at timestamptz not null default now()
);

create table if not exists pme_purchase_lists (
  id uuid primary key default gen_random_uuid(),
  label text not null default 'Compra semanal',
  raw_text text,
  created_by uuid,
  created_at timestamptz not null default now()
);

create table if not exists pme_purchase_needs (
  id uuid primary key default gen_random_uuid(),
  purchase_list_id uuid not null references pme_purchase_lists(id) on delete cascade,
  product text not null,
  normalized_product text not null,
  quantity numeric(14,4) not null default 1,
  unit text not null default 'un'
);

create table if not exists pme_recommendation_runs (
  id uuid primary key default gen_random_uuid(),
  purchase_list_id uuid references pme_purchase_lists(id) on delete set null,
  estimated_savings_week numeric(14,4) not null default 0,
  products_compared integer not null default 0,
  total_items integer not null default 0,
  warnings jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists pme_recommendations (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references pme_recommendation_runs(id) on delete cascade,
  normalized_product text not null,
  product text not null,
  recommended_supplier text not null,
  requested_quantity numeric(14,4) not null default 1,
  unit_price numeric(14,4) not null,
  estimated_total_cost numeric(14,4) not null default 0,
  baseline_total_cost numeric(14,4) not null default 0,
  estimated_savings numeric(14,4) not null default 0,
  reason text not null,
  alternatives jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
