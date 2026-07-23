"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import ScoreRing from "@/components/ScoreRing";
import RatingBar from "@/components/RatingBar";
import SessionCard from "@/components/SessionCard";
import AllSessionsModal from "@/components/AllSessionsModal";
import AddProjectModal from "@/components/AddProjectModal";
import AddSessionModal from "@/components/AddSessionModal";
import ProcessingModal from "@/components/ProcessingModal";
import useAnalysisJob from "@/hooks/useAnalysisJob";
import useApi from "@/hooks/useApi";
import { formatDate, getDaysUntilDeadline, projectFromApi, sessionFromApi } from "@/lib/data";
import { archetypeLabels } from "@/lib/archetypes.mjs";
import { improvementAreaGroups, improvementAreaGroupByValue, improvementAreaLabels } from "@/lib/improvementAreas.mjs";
import dynamic from "next/dynamic";

const TimelineChart = dynamic(() => import("@/components/TimelineChart"), { ssr: false });

export default function ProjectPage() {
  const { id } = useParams();
  const router = useRouter();
  const analysisJob = useAnalysisJob();
  const { authReady, getProject, listProjectSessions, updateProject } = useApi();
  const [modal, setModal] = useState(null);
  const [project, setProject] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState(null);
  const [editState, setEditState] = useState({ saving: false, error: null });
  const [detailsOpen, setDetailsOpen] = useState(false);

  const load = async () => {
    try {
      const [projectRow, sessionRows] = await Promise.all([getProject(id), listProjectSessions(id)]);
      setProject(projectFromApi(projectRow));
      setSessions(sessionRows.map(sessionFromApi).filter(Boolean));
      setError(null);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  useEffect(() => { if (authReady) load(); }, [id, authReady]);
  useEffect(() => { if (analysisJob.status === "replacement_required") setModal("processing"); }, [analysisJob.status]);
  const latest = sessions[0] || null;
  const days = project ? getDaysUntilDeadline(project.deadline) : null;
  const pillarData = [...sessions].reverse().map((session) => ({ session: session.name, "Facial expressions": session.face, Tone: session.tone, Body: session.body }));
  const handleSessionUpload = (file) => { setModal("processing"); analysisJob.start({ file, projectId: id, archetype: project?.default_archetype_key || "corporate_board", audienceContext: project?.description || "" }); };

  const handleProjectEdit = async (form) => {
    setEditState({ saving: true, error: null });
    try {
      await updateProject(id, {
        name: form.name,
        goal: form.description || null,
        deadline: form.deadline || null,
        improvement_areas: form.improvementAreas,
        default_archetype_key: form.archetype,
      });
      await load();
      setModal(null);
    } catch (requestError) {
      setEditState({ saving: false, error: requestError.message });
      return;
    }
    setEditState({ saving: false, error: null });
  };

  const openProjectEditor = () => {
    setEditState({ saving: false, error: null });
    setModal("editProject");
  };

  if (error) return <div className="app-shell flex flex-col items-center justify-center gap-3 px-6 text-center text-red-700"><p className="font-medium">This project could not be loaded.</p><p className="text-sm text-red-700/80">{error}</p><button onClick={load} className="btn-secondary mt-2">Try again</button></div>;
  if (!project) return <div className="app-shell flex items-center justify-center gap-3 text-zinc-400"><span className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-blue-400" aria-hidden="true" /><span>Loading project…</span></div>;
  return <div className="app-shell"><Navbar backHref="/" /><main className="page-container"><div className="grid grid-cols-1 gap-8 lg:grid-cols-3"><div className="flex flex-col gap-6 lg:col-span-2"><header><div className="min-w-0"><div className="flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-2"><h1 className="page-title break-words">{project.name}</h1><button onClick={openProjectEditor} className="icon-button shrink-0" aria-label={`Edit ${project.name}`}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg></button></div>{project.deadline && <div className="chip w-fit shrink-0"><span className={days !== null && days <= 30 ? "text-readiness" : "text-zinc-400"}>{days > 0 ? `${days} days until deadline` : "Deadline passed"}</span><span className="mx-2 text-zinc-600">·</span><span>{formatDate(project.deadline)}</span></div>}</div><p className="page-summary">{project.description || "No rehearsal goal added yet."}</p></div><button onClick={() => setDetailsOpen((open) => !open)} className="btn-quiet mt-4 w-fit" aria-expanded={detailsOpen}><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={`transition-transform duration-150 ${detailsOpen ? "rotate-90" : ""}`}><path d="M9 6l6 6-6 6" /></svg>Project details</button>{detailsOpen && <div className="mt-4 flex flex-col gap-4"><span className="chip w-fit">{archetypeLabels[project.archetype] || project.archetype}</span>{improvementAreaGroups.map((group) => { const selected = project.improvementAreas.filter((area) => improvementAreaGroupByValue[area] === group.key); if (selected.length === 0) return null; return <div key={group.key}><p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-600">{group.label} focus</p><div className="flex flex-wrap gap-2">{selected.map((area) => <span key={area} className="chip chip-selected">{improvementAreaLabels[area]}</span>)}</div></div>; })}</div>}</header><section><div className="mb-4 flex items-center justify-between"><h2 className="text-base font-semibold text-zinc-200">Retained sessions <span className="font-normal text-zinc-500">({sessions.length}/5)</span></h2>{sessions.length > 0 && <button onClick={() => setModal("allSessions")} className="btn-quiet">View all</button>}</div>{sessions.length === 0 ? <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-900 p-8 text-center"><p className="mb-4 text-sm leading-6 text-zinc-500">Your first successful analysis becomes the protected baseline.</p><button onClick={() => setModal("addSession")} className="btn-primary">Add first session</button></div> : <div className="flex flex-col gap-4">{sessions.slice(0,3).map((session,index) => <SessionCard key={session.id} session={session} prev={sessions[index+1]} onClick={() => router.push(`/session/${session.id}`)} />)}</div>}</section></div>{latest && <aside className="flex flex-col gap-6"><div className="surface-card"><h3 className="section-label mb-4">Latest rehearsal</h3><div className="mb-4 flex justify-center"><ScoreRing score={latest.overallScore} /></div><div className="flex flex-col gap-4"><RatingBar label="Voice" value={latest.tone} target={85} /><RatingBar label="Body" value={latest.body} target={85} /><RatingBar label="Facial expressions" value={latest.face} target={85} /></div></div><button onClick={() => setModal("addSession")} className="btn-primary w-full">New session</button></aside>}</div>{sessions.length > 0 && <section className="surface-card mt-8"><h2 className="section-label mb-4">Pillar progress</h2><TimelineChart data={pillarData} /></section>}</main>
    {modal === "allSessions" && <AllSessionsModal sessions={sessions} projectId={id} onClose={() => setModal(null)} onAddSession={() => setModal("addSession")} />}
    {modal === "editProject" && <AddProjectModal initial={project} submitting={editState.saving} submitError={editState.error} onConfirm={handleProjectEdit} onClose={() => { if (!editState.saving) setModal(null); }} />}
    {modal === "addSession" && <AddSessionModal onClose={() => setModal(null)} onConfirm={handleSessionUpload} />}
    {modal === "processing" && <ProcessingModal job={analysisJob} onComplete={() => { load(); router.push(`/session/${analysisJob.sessionId}`); }} onConfirm={analysisJob.confirm} onReplace={analysisJob.chooseReplacement} onCancel={() => { analysisJob.reset(); setModal(null); }} />}
  </div>;
}
