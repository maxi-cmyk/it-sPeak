-- it'sPEAK master schema for a new Supabase/Postgres database.
-- Consolidated through Supabase migration: 202607230001_recompress_posture_scoring_bands.
-- Upgrade an existing database with the timestamped files in supabase/migrations;
-- do not run this fresh-install snapshot over an already initialized database.
-- Ownership IDs are Clerk JWT `sub` strings, not auth.users UUIDs.

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.profiles (
  id text primary key check (length(id) between 1 and 255),
  display_name text check (display_name is null or length(display_name) <= 120),
  avatar_url text check (avatar_url is null or length(avatar_url) <= 2048),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.archetypes (
  key text primary key check (key ~ '^[a-z][a-z0-9_]*$'),
  label text not null,
  description text not null,
  status text not null check (status in ('enabled', 'planned', 'disabled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.archetype_configs (
  archetype_key text not null references public.archetypes(key) on delete cascade,
  version integer not null check (version > 0),
  scoring_config jsonb not null check (jsonb_typeof(scoring_config) = 'object'),
  created_at timestamptz not null default now(),
  primary key (archetype_key, version)
);

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null references public.profiles(id) on delete cascade,
  name text not null check (length(btrim(name)) between 1 and 120),
  goal text check (goal is null or length(goal) <= 1000),
  improvement_areas text[] not null default array['pacing', 'intonation', 'filler_words', 'eye_contact', 'facial_expression', 'posture', 'gestures']::text[] check (
    cardinality(improvement_areas) > 0
    and improvement_areas <@ array['pacing', 'intonation', 'filler_words', 'eye_contact', 'facial_expression', 'posture', 'gestures']::text[]
  ),
  default_archetype_key text not null references public.archetypes(key),
  default_archetype_version integer not null default 1 check (default_archetype_version > 0),
  deadline date,
  pinned boolean not null default false,
  reset_generation integer not null default 1 check (reset_generation > 0),
  next_sequence_number integer not null default 1 check (next_sequence_number > 0),
  baseline_session_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (default_archetype_key, default_archetype_version)
    references public.archetype_configs(archetype_key, version)
);

create table public.sessions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id text not null references public.profiles(id) on delete cascade,
  task_id text unique,
  status text not null default 'quality_check' check (
    status in ('quality_check', 'needs_confirmation', 'rejected', 'queued', 'processing', 'success', 'failure', 'replaced')
  ),
  stage text,
  error text,
  generation integer not null check (generation > 0),
  sequence_number integer check (sequence_number is null or sequence_number > 0),
  archetype_key text not null,
  archetype_version integer not null check (archetype_version > 0),
  audience_context text check (audience_context is null or length(audience_context) <= 300),
  replace_session_id uuid references public.sessions(id) on delete set null,
  quality_gate jsonb check (quality_gate is null or jsonb_typeof(quality_gate) = 'object'),
  video_object_path text,
  landmarks_object_path text,
  retained_at timestamptz,
  retired_at timestamptz,
  retired_reason text check (retired_reason is null or retired_reason in ('replaced', 'project_deleted', 'reset')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  foreign key (archetype_key, archetype_version)
    references public.archetype_configs(archetype_key, version),
  unique (project_id, generation, sequence_number),
  check (
    (status = 'success' and sequence_number is not null and retained_at is not null and retired_at is null)
    or (status = 'replaced' and sequence_number is not null and retained_at is not null and retired_at is not null)
    or (status not in ('success', 'replaced') and sequence_number is null and retained_at is null)
  )
);

alter table public.projects
  add constraint projects_baseline_session_fk
  foreign key (baseline_session_id) references public.sessions(id) on delete restrict
  deferrable initially deferred;

create table public.analysis_results (
  session_id uuid primary key references public.sessions(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id text not null references public.profiles(id) on delete cascade,
  report_version text not null default '1.0',
  overall_score numeric(5,2) check (overall_score between 0 and 100),
  vocal_score numeric(5,2) check (vocal_score between 0 and 100),
  face_score numeric(5,2) check (face_score between 0 and 100),
  body_score numeric(5,2) check (body_score between 0 and 100),
  normalized_scores jsonb not null check (jsonb_typeof(normalized_scores) = 'object'),
  metric_confidence jsonb not null default '{}'::jsonb check (jsonb_typeof(metric_confidence) = 'object'),
  report jsonb not null check (jsonb_typeof(report) = 'object'),
  created_at timestamptz not null default now()
);

create table public.coaching_cards (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id text not null references public.profiles(id) on delete cascade,
  module text not null check (module in ('face', 'body', 'audio')),
  source_metric text,
  problem text not null,
  importance text not null,
  actionable_fix text not null,
  fingerprint text not null,
  display_order integer not null default 0 check (display_order >= 0),
  created_at timestamptz not null default now(),
  unique (session_id, fingerprint)
);

create table public.session_events (
  id bigint generated by default as identity primary key,
  session_id uuid references public.sessions(id) on delete set null,
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id text not null references public.profiles(id) on delete cascade,
  event_type text not null check (
    event_type in ('created', 'baseline_assigned', 'committed', 'replaced', 'failed', 'artifact_cleanup_pending', 'artifact_cleanup_complete')
  ),
  payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  created_at timestamptz not null default now()
);

create index projects_owner_id_idx on public.projects(owner_id);
create index projects_owner_updated_idx on public.projects(owner_id, updated_at desc);
create index sessions_owner_id_idx on public.sessions(owner_id);
create index sessions_project_active_idx on public.sessions(project_id, generation, sequence_number)
  where retired_at is null and status = 'success';
create index sessions_replacement_idx on public.sessions(replace_session_id) where replace_session_id is not null;
create index analysis_results_owner_id_idx on public.analysis_results(owner_id);
create index coaching_cards_owner_session_idx on public.coaching_cards(owner_id, session_id, display_order);
create index session_events_project_created_idx on public.session_events(project_id, created_at desc);

create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();
create trigger archetypes_set_updated_at before update on public.archetypes
for each row execute function public.set_updated_at();
create trigger projects_set_updated_at before update on public.projects
for each row execute function public.set_updated_at();
create trigger sessions_set_updated_at before update on public.sessions
for each row execute function public.set_updated_at();

insert into public.archetypes (key, label, description, status) values
  ('corporate_board', 'Corporate / Board', 'Calm authority, sustained eye contact, controlled expression, upright posture, and deliberate gestures.', 'enabled'),
  ('motivational_keynote', 'Motivational / Keynote', 'High-energy delivery with expressive facial presence, expansive gestures, and purposeful movement.', 'enabled'),
  ('startup_pitch', 'Startup Pitch', 'Concise, credible and energetic investor or demo-day delivery.', 'planned'),
  ('academic_conference', 'Academic / Conference', 'Structured, evidence-led delivery for formal academic audiences.', 'planned'),
  ('informal_team', 'Informal / Team', 'Conversational delivery for internal updates and collaborative settings.', 'planned'),
  ('job_interview', 'Job Interview', 'Focused, personable delivery for interview answers and professional introductions.', 'planned')
on conflict (key) do update set
  label = excluded.label,
  description = excluded.description,
  status = excluded.status;

insert into public.archetype_configs (archetype_key, version, scoring_config) values
  ('corporate_board', 1, '{"eye_contact":{"kind":"floor","low":0.35,"ideal":0.80},"expression":{"kind":"target","ideal":0.12,"tol_low":0.22,"tol_high":0.60},"posture":{"kind":"floor","low":0.40,"ideal":1.0},"gesture_frequency":{"kind":"target","ideal":0.25,"tol_low":0.45,"tol_high":0.85},"gesture_range":{"kind":"target","ideal":0.20,"tol_low":0.40,"tol_high":0.80},"openness":{"kind":"floor","low":0.12,"ideal":0.40},"smile_naturalness":{"kind":"floor","low":0.15,"ideal":0.65},"movement_purposefulness":{"kind":"floor","low":0.20,"ideal":0.75},"spatial_use":{"kind":"target","ideal":0.25,"tol_low":0.25,"tol_high":0.55},"gesture_freq_weight":0.60}'::jsonb),
  ('motivational_keynote', 1, '{"eye_contact":{"kind":"floor","low":0.25,"ideal":0.65},"expression":{"kind":"floor","low":0.02,"ideal":0.14},"posture":{"kind":"floor","low":0.35,"ideal":0.98},"gesture_frequency":{"kind":"target","ideal":0.70,"tol_low":0.90,"tol_high":0.90},"gesture_range":{"kind":"target","ideal":0.75,"tol_low":0.90,"tol_high":0.85},"openness":{"kind":"floor","low":0.12,"ideal":0.45},"smile_naturalness":{"kind":"floor","low":0.20,"ideal":0.75},"movement_purposefulness":{"kind":"floor","low":0.25,"ideal":0.80},"spatial_use":{"kind":"floor","low":0.10,"ideal":0.65},"gesture_freq_weight":0.40}'::jsonb),
  ('startup_pitch', 1, '{"eye_contact":{"kind":"floor","low":0.30,"ideal":0.72},"expression":{"kind":"floor","low":0.02,"ideal":0.12},"posture":{"kind":"floor","low":0.40,"ideal":1.0},"gesture_frequency":{"kind":"target","ideal":0.50,"tol_low":0.75,"tol_high":0.85},"gesture_range":{"kind":"target","ideal":0.50,"tol_low":0.75,"tol_high":0.85},"openness":{"kind":"floor","low":0.12,"ideal":0.42},"smile_naturalness":{"kind":"floor","low":0.20,"ideal":0.70},"movement_purposefulness":{"kind":"floor","low":0.30,"ideal":0.82},"spatial_use":{"kind":"target","ideal":0.45,"tol_low":0.40,"tol_high":0.45},"gesture_freq_weight":0.50}'::jsonb),
  ('academic_conference', 1, '{"eye_contact":{"kind":"floor","low":0.25,"ideal":0.60},"expression":{"kind":"target","ideal":0.14,"tol_low":0.24,"tol_high":0.65},"posture":{"kind":"floor","low":0.40,"ideal":1.0},"gesture_frequency":{"kind":"target","ideal":0.35,"tol_low":0.60,"tol_high":0.85},"gesture_range":{"kind":"target","ideal":0.30,"tol_low":0.55,"tol_high":0.82},"openness":{"kind":"floor","low":0.10,"ideal":0.38},"smile_naturalness":{"kind":"floor","low":0.10,"ideal":0.55},"movement_purposefulness":{"kind":"floor","low":0.20,"ideal":0.72},"spatial_use":{"kind":"target","ideal":0.25,"tol_low":0.25,"tol_high":0.50},"gesture_freq_weight":0.55}'::jsonb),
  ('informal_team', 1, '{"eye_contact":{"kind":"floor","low":0.20,"ideal":0.55},"expression":{"kind":"floor","low":0.02,"ideal":0.13},"posture":{"kind":"floor","low":0.32,"ideal":0.96},"gesture_frequency":{"kind":"target","ideal":0.50,"tol_low":0.80,"tol_high":0.95},"gesture_range":{"kind":"target","ideal":0.50,"tol_low":0.80,"tol_high":0.95},"openness":{"kind":"floor","low":0.10,"ideal":0.42},"smile_naturalness":{"kind":"floor","low":0.20,"ideal":0.70},"movement_purposefulness":{"kind":"floor","low":0.15,"ideal":0.65},"spatial_use":{"kind":"floor","low":0.10,"ideal":0.55},"gesture_freq_weight":0.50}'::jsonb),
  ('job_interview', 1, '{"eye_contact":{"kind":"floor","low":0.35,"ideal":0.78},"expression":{"kind":"target","ideal":0.12,"tol_low":0.22,"tol_high":0.60},"posture":{"kind":"floor","low":0.42,"ideal":1.0},"gesture_frequency":{"kind":"target","ideal":0.30,"tol_low":0.55,"tol_high":0.82},"gesture_range":{"kind":"target","ideal":0.25,"tol_low":0.50,"tol_high":0.80},"openness":{"kind":"floor","low":0.15,"ideal":0.42},"smile_naturalness":{"kind":"floor","low":0.20,"ideal":0.70},"movement_purposefulness":{"kind":"floor","low":0.20,"ideal":0.70},"spatial_use":{"kind":"target","ideal":0.15,"tol_low":0.15,"tol_high":0.45},"gesture_freq_weight":0.60}'::jsonb)
on conflict (archetype_key, version) do nothing;

create or replace function public.prevent_baseline_retirement()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.retired_at is not null and old.retired_at is null and exists (
    select 1 from public.projects p where p.baseline_session_id = old.id
  ) then
    raise exception 'The baseline session cannot be replaced' using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger sessions_protect_baseline before update of retired_at on public.sessions
for each row execute function public.prevent_baseline_retirement();

create or replace function public.commit_analysis_session(
  p_session_id uuid,
  p_report jsonb,
  p_cards jsonb,
  p_overall_score numeric,
  p_vocal_score numeric,
  p_face_score numeric,
  p_body_score numeric
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_session public.sessions%rowtype;
  v_project public.projects%rowtype;
  v_replace public.sessions%rowtype;
  v_active_count integer;
  v_sequence integer;
  v_card jsonb;
  v_index integer := 0;
  v_old_video text;
  v_old_landmarks text;
begin
  select * into v_session from public.sessions where id = p_session_id for update;
  if not found then raise exception 'Pending session not found' using errcode = 'P0002'; end if;
  if v_session.status not in ('queued', 'processing') then
    raise exception 'Session is not eligible for commit';
  end if;

  select * into v_project from public.projects where id = v_session.project_id for update;
  if not found or v_project.owner_id <> v_session.owner_id then
    raise exception 'Project ownership mismatch' using errcode = '42501';
  end if;
  if v_project.reset_generation <> v_session.generation then
    raise exception 'Project generation changed during analysis';
  end if;

  select count(*) into v_active_count
  from public.sessions
  where project_id = v_project.id and generation = v_project.reset_generation
    and status = 'success' and retired_at is null;

  if v_active_count >= 5 then
    if v_session.replace_session_id is null then
      raise exception 'replacement_required' using errcode = 'P0001';
    end if;
    select * into v_replace from public.sessions
    where id = v_session.replace_session_id for update;
    if not found
      or v_replace.project_id <> v_project.id
      or v_replace.owner_id <> v_project.owner_id
      or v_replace.generation <> v_project.reset_generation
      or v_replace.status <> 'success'
      or v_replace.retired_at is not null
      or v_replace.id = v_project.baseline_session_id then
      raise exception 'Invalid or stale replacement session' using errcode = '23514';
    end if;
    v_old_video := v_replace.video_object_path;
    v_old_landmarks := v_replace.landmarks_object_path;
    update public.sessions set
      status = 'replaced', retired_at = now(), retired_reason = 'replaced'
    where id = v_replace.id;
    insert into public.session_events(session_id, project_id, owner_id, event_type, payload)
    values (v_replace.id, v_project.id, v_project.owner_id, 'replaced', jsonb_build_object('replacement_session_id', p_session_id));
    insert into public.session_events(session_id, project_id, owner_id, event_type, payload)
    values (v_replace.id, v_project.id, v_project.owner_id, 'artifact_cleanup_pending', jsonb_build_object('paths', jsonb_build_array(v_old_video, v_old_landmarks)));
  elsif v_session.replace_session_id is not null then
    raise exception 'A replacement is only allowed when five sessions are retained' using errcode = '23514';
  end if;

  v_sequence := v_project.next_sequence_number;
  update public.projects set next_sequence_number = v_sequence + 1 where id = v_project.id;
  update public.sessions set
    status = 'success', stage = 'Analysis complete', error = null,
    sequence_number = v_sequence, retained_at = now(), completed_at = now()
  where id = p_session_id;

  insert into public.analysis_results(
    session_id, project_id, owner_id, report_version,
    overall_score, vocal_score, face_score, body_score,
    normalized_scores, metric_confidence, report
  ) values (
    p_session_id, v_project.id, v_project.owner_id, coalesce(p_report->>'version', '1.0'),
    p_overall_score, p_vocal_score, p_face_score, p_body_score,
    coalesce(p_report->'scores', '{}'::jsonb),
    coalesce(p_report->'raw_analysis'->'metric_confidence', '{}'::jsonb), p_report
  );

  if jsonb_typeof(p_cards) = 'array' then
    for v_card in select value from jsonb_array_elements(p_cards) loop
      insert into public.coaching_cards(
        session_id, project_id, owner_id, module, source_metric,
        problem, importance, actionable_fix, fingerprint, display_order
      ) values (
        p_session_id, v_project.id, v_project.owner_id,
        coalesce(v_card->>'module', 'audio'), v_card->>'source_metric',
        coalesce(v_card->>'problem', ''), coalesce(v_card->>'importance', ''),
        coalesce(v_card->>'actionable_fix', ''),
        encode(digest(lower(coalesce(v_card->>'module','') || '|' || coalesce(v_card->>'problem','') || '|' || coalesce(v_card->>'actionable_fix','')), 'sha256'), 'hex'),
        v_index
      ) on conflict (session_id, fingerprint) do nothing;
      v_index := v_index + 1;
    end loop;
  end if;

  if v_project.baseline_session_id is null then
    update public.projects set baseline_session_id = p_session_id where id = v_project.id;
    insert into public.session_events(session_id, project_id, owner_id, event_type)
    values (p_session_id, v_project.id, v_project.owner_id, 'baseline_assigned');
  end if;
  insert into public.session_events(session_id, project_id, owner_id, event_type, payload)
  values (p_session_id, v_project.id, v_project.owner_id, 'committed', jsonb_build_object('sequence_number', v_sequence));

  return jsonb_build_object(
    'session_id', p_session_id, 'sequence_number', v_sequence,
    'baseline', v_project.baseline_session_id is null,
    'replaced_session_id', v_session.replace_session_id,
    'old_video_object_path', v_old_video,
    'old_landmarks_object_path', v_old_landmarks
  );
end;
$$;

revoke all on function public.commit_analysis_session(uuid, jsonb, jsonb, numeric, numeric, numeric, numeric) from public, anon, authenticated;
grant execute on function public.commit_analysis_session(uuid, jsonb, jsonb, numeric, numeric, numeric, numeric) to service_role;

alter table public.profiles enable row level security;
alter table public.archetypes enable row level security;
alter table public.archetype_configs enable row level security;
alter table public.projects enable row level security;
alter table public.sessions enable row level security;
alter table public.analysis_results enable row level security;
alter table public.coaching_cards enable row level security;
alter table public.session_events enable row level security;

create policy profiles_select_own on public.profiles for select to authenticated
using ((select auth.jwt()->>'sub') = id);
create policy profiles_insert_own on public.profiles for insert to authenticated
with check ((select auth.jwt()->>'sub') = id);
create policy profiles_update_own on public.profiles for update to authenticated
using ((select auth.jwt()->>'sub') = id) with check ((select auth.jwt()->>'sub') = id);
create policy archetypes_read on public.archetypes for select to authenticated using (true);
create policy archetype_configs_read on public.archetype_configs for select to authenticated using (true);
create policy projects_owner_all on public.projects for all to authenticated
using ((select auth.jwt()->>'sub') = owner_id)
with check ((select auth.jwt()->>'sub') = owner_id);
create policy sessions_owner_read on public.sessions for select to authenticated
using ((select auth.jwt()->>'sub') = owner_id);
create policy analysis_results_owner_read on public.analysis_results for select to authenticated
using ((select auth.jwt()->>'sub') = owner_id);
create policy coaching_cards_owner_read on public.coaching_cards for select to authenticated
using ((select auth.jwt()->>'sub') = owner_id);
create policy session_events_owner_read on public.session_events for select to authenticated
using ((select auth.jwt()->>'sub') = owner_id);

insert into storage.buckets (id, name, public, file_size_limit)
values ('session-artifacts', 'session-artifacts', false, 262144000)
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit;

create policy session_artifacts_owner_read on storage.objects for select to authenticated
using (bucket_id = 'session-artifacts' and (storage.foldername(name))[1] = (select auth.jwt()->>'sub'));
create policy session_artifacts_owner_insert on storage.objects for insert to authenticated
with check (bucket_id = 'session-artifacts' and (storage.foldername(name))[1] = (select auth.jwt()->>'sub'));
create policy session_artifacts_owner_update on storage.objects for update to authenticated
using (bucket_id = 'session-artifacts' and (storage.foldername(name))[1] = (select auth.jwt()->>'sub'))
with check (bucket_id = 'session-artifacts' and (storage.foldername(name))[1] = (select auth.jwt()->>'sub'));
create policy session_artifacts_owner_delete on storage.objects for delete to authenticated
using (bucket_id = 'session-artifacts' and (storage.foldername(name))[1] = (select auth.jwt()->>'sub'));
