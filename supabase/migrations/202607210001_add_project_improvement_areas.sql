alter table public.projects
  add column if not exists improvement_areas text[] not null
  default array['pacing', 'intonation', 'filler_words', 'eye_contact', 'facial_expression', 'posture', 'gestures']::text[];

alter table public.projects
  drop constraint if exists projects_improvement_areas_check;

update public.projects as project
set improvement_areas = (
  select array_agg(distinct mapped_area order by mapped_area) as areas
  from unnest(project.improvement_areas) as current_area
  cross join lateral unnest(
    case current_area
      when 'voice' then array['pacing', 'intonation', 'filler_words']::text[]
      when 'face' then array['eye_contact', 'facial_expression']::text[]
      when 'body' then array['posture', 'gestures']::text[]
      else array[current_area]::text[]
    end
  ) as mapped_area
)
where project.improvement_areas && array['voice', 'face', 'body']::text[];

alter table public.projects
  alter column improvement_areas set default
  array['pacing', 'intonation', 'filler_words', 'eye_contact', 'facial_expression', 'posture', 'gestures']::text[];

alter table public.projects
  add constraint projects_improvement_areas_check check (
    cardinality(improvement_areas) > 0
    and improvement_areas <@ array['pacing', 'intonation', 'filler_words', 'eye_contact', 'facial_expression', 'posture', 'gestures']::text[]
  );
