-- pgcrypto is installed in Supabase's extensions schema. The initial function
-- searched only public, so its unqualified digest() call failed at commit time.
alter function public.commit_analysis_session(uuid, jsonb, jsonb, numeric, numeric, numeric, numeric)
set search_path = public, extensions;
