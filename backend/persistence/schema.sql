-- Supabase scaffold. Migrations and row-level security policies are added later.
create table if not exists projects (
  id uuid primary key,
  user_id uuid not null,
  name text not null,
  goal text,
  archetype text not null,
  deadline date,
  created_at timestamptz not null default now()
);

create table if not exists sessions (
  id uuid primary key,
  project_id uuid not null references projects(id) on delete cascade,
  task_id text unique not null,
  status text not null default 'queued',
  r2_key text,
  report jsonb,
  created_at timestamptz not null default now()
);
