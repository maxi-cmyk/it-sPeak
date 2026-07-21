-- Fix commit_analysis_session: pgcrypto's digest() lives in the
-- "extensions" schema on Supabase, but the function's search_path was
-- scoped to "public" only, so digest() could never resolve.

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
