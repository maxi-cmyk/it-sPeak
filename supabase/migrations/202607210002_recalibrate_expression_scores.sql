-- Make facial-expression scoring usable with the observed normalized landmark
-- variance while preserving stricter expectations for energetic archetypes.
with expression_bands(archetype_key, band) as (
  values
    ('corporate_board', '{"kind":"target","ideal":0.12,"tol_low":0.12,"tol_high":0.35}'::jsonb),
    ('motivational_keynote', '{"kind":"floor","low":0.03,"ideal":0.25}'::jsonb),
    ('startup_pitch', '{"kind":"floor","low":0.03,"ideal":0.20}'::jsonb),
    ('academic_conference', '{"kind":"target","ideal":0.14,"tol_low":0.14,"tol_high":0.40}'::jsonb),
    ('informal_team', '{"kind":"floor","low":0.03,"ideal":0.22}'::jsonb),
    ('job_interview', '{"kind":"target","ideal":0.12,"tol_low":0.12,"tol_high":0.35}'::jsonb)
)
update public.archetype_configs as configs
set scoring_config = jsonb_set(configs.scoring_config, '{expression}', bands.band, true)
from expression_bands as bands
where configs.archetype_key = bands.archetype_key
  and configs.version = 1;
