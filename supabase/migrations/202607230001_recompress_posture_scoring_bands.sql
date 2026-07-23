-- Recompress the posture FloorBands so the posture score stops saturating at
-- full marks. The upright-shoulder proxy tops out near 1.0 for almost anyone
-- facing the camera, so the previous low ideals (~0.45-0.58) mapped essentially
-- every recording to 100. Raising `low` to ~0.32-0.42 and `ideal` to ~0.96-1.0
-- means a merely-normal posture proxy lands ~50-60 while only steady, genuinely
-- square posture reaches 80-100. Only the "posture" band changes per archetype;
-- all other bands are carried over unchanged from 202607220001.
update public.archetype_configs
set scoring_config = jsonb_set(scoring_config, '{posture}', '{"kind":"floor","low":0.40,"ideal":1.0}'::jsonb)
where archetype_key in ('corporate_board', 'startup_pitch', 'academic_conference') and version = 1;

update public.archetype_configs
set scoring_config = jsonb_set(scoring_config, '{posture}', '{"kind":"floor","low":0.35,"ideal":0.98}'::jsonb)
where archetype_key = 'motivational_keynote' and version = 1;

update public.archetype_configs
set scoring_config = jsonb_set(scoring_config, '{posture}', '{"kind":"floor","low":0.32,"ideal":0.96}'::jsonb)
where archetype_key = 'informal_team' and version = 1;

update public.archetype_configs
set scoring_config = jsonb_set(scoring_config, '{posture}', '{"kind":"floor","low":0.42,"ideal":1.0}'::jsonb)
where archetype_key = 'job_interview' and version = 1;
