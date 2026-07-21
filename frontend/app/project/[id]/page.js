"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import ScoreRing from "@/components/ScoreRing";
import RatingBar from "@/components/RatingBar";
import SessionCard from "@/components/SessionCard";
import AllSessionsModal from "@/components/AllSessionsModal";
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
  const { id } = useParams(); const router = useRouter(); const analysisJob = useAnalysisJob();
  const { authReady, getProject, listProjectSessions } = useApi();
  const [modal, setModal] = useState(null); const [project, setProject] = useState(null); const [sessions, setSessions] = useState([]); const [error, setError] = useState(null);
  const load = async () => { try { const [projectRow, sessionRows] = await Promise.all([getProject(id), listProjectSessions(id)]); setProject(projectFromApi(projectRow)); setSessions(sessionRows.map(sessionFromApi).filter(Boolean)); setError(null); } catch (requestError) { setError(requestError.message); } };
  useEffect(() => { if (authReady) load(); }, [id, authReady]);
  useEffect(() => { if (analysisJob.status === "replacement_required") setModal("processing"); }, [analysisJob.status]);
  const latest = sessions[0] || null; const days = project ? getDaysUntilDeadline(project.deadline) : null;
  const pillarData = [...sessions].reverse().map((session) => ({ session: session.name, Facial: session.face, Tone: session.tone, Body: session.body }));
  const handleSessionUpload = (file) => { setModal("processing"); analysisJob.start({ file, projectId: id, archetype: project?.default_archetype_key || "corporate_board", audienceContext: project?.description || "" }); };
  if (error) return <div className="min-h-screen bg-zinc-950 flex flex-col gap-3 items-center justify-center text-red-300"><p>{error}</p><button onClick={load} className="underline">Try again</button></div>;
  if (!project) return <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-zinc-500">Loading project…</div>;
  return <div className="min-h-screen bg-zinc-950"><Navbar backHref="/" /><main className="max-w-5xl mx-auto px-6 py-10"><div className="grid grid-cols-1 lg:grid-cols-3 gap-8"><div className="lg:col-span-2 flex flex-col gap-6"><div><p className="text-xs uppercase tracking-[0.22em] text-violet-400 mb-2">Project {sessions.length}/5 retained</p><h1 className="text-2xl font-bold text-zinc-50">{project.name}</h1><p className="text-zinc-400 text-sm leading-relaxed mt-2">{project.description || "No rehearsal goal added yet."}</p><div className="mt-4 flex flex-col gap-3"><span className="w-fit rounded-full border border-zinc-700 bg-zinc-800 px-2.5 py-1 text-xs font-medium text-zinc-400">{archetypeLabels[project.archetype] || project.archetype}</span>{improvementAreaGroups.map((group) => { const selected = project.improvementAreas.filter((area) => improvementAreaGroupByValue[area] === group.key); if (selected.length === 0) return null; return <div key={group.key}><p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5">{group.label}</p><div className="flex flex-wrap gap-2">{selected.map((area) => <span key={area} className="rounded-full border border-violet-500/25 bg-violet-500/10 px-2.5 py-1 text-xs font-medium text-violet-300">{improvementAreaLabels[area]}</span>)}</div></div>; })}</div></div>{project.deadline && <div className="inline-flex w-fit items-center gap-2 px-3 py-1.5 rounded-full text-xs border border-zinc-700 bg-zinc-800 text-zinc-400"><span>{days > 0 ? `${days} days till deadline` : "Deadline passed"}</span><span>·</span><span>{formatDate(project.deadline)}</span></div>}<section><div className="flex items-center justify-between mb-3"><h2 className="text-base font-semibold text-zinc-200">Retained sessions</h2><button onClick={() => setModal("allSessions")} className="text-xs text-violet-400 border border-violet-500/30 px-3 py-1.5 rounded-lg">View all</button></div>{sessions.length === 0 ? <div className="bg-zinc-900 border border-zinc-800 border-dashed rounded-xl p-8 text-center"><p className="text-zinc-500 text-sm mb-3">Your first successful analysis becomes the protected baseline.</p><button onClick={() => setModal("addSession")} className="text-violet-400 text-sm">Start Session 1 →</button></div> : <div className="flex flex-col gap-3">{sessions.slice(0,3).map((session,index) => <SessionCard key={session.id} session={session} prev={sessions[index+1]} onClick={() => router.push(`/session/${session.id}`)} />)}</div>}</section></div><aside className="flex flex-col gap-5">{latest ? <><div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5"><h3 className="text-xs text-zinc-500 uppercase tracking-wider mb-4">Latest rehearsal</h3><div className="flex justify-center mb-4"><ScoreRing score={latest.overallScore} /></div><div className="flex flex-col gap-3"><RatingBar label="Voice" value={latest.tone} target={85} /><RatingBar label="Body" value={latest.body} target={85} /><RatingBar label="Face" value={latest.face} target={85} /></div></div><button onClick={() => setModal("addSession")} className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium text-sm">+ New Session</button></> : <button onClick={() => setModal("addSession")} className="w-full py-2.5 rounded-lg bg-violet-600 text-white font-medium text-sm">+ Add Session</button>}</aside></div>{sessions.length > 0 && <section className="mt-8 bg-zinc-900 border border-zinc-800 rounded-xl p-5"><h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Pillar progress</h2><TimelineChart data={pillarData} /></section>}</main>
    {modal === "allSessions" && <AllSessionsModal sessions={sessions} projectId={id} onClose={() => setModal(null)} onAddSession={() => setModal("addSession")} />}
    {modal === "addSession" && <AddSessionModal onClose={() => setModal(null)} onConfirm={handleSessionUpload} />}
    {modal === "processing" && <ProcessingModal job={analysisJob} onComplete={() => { load(); router.push(`/session/${analysisJob.sessionId}`); }} onConfirm={analysisJob.confirm} onReplace={analysisJob.chooseReplacement} onCancel={() => { analysisJob.reset(); setModal(null); }} />}
  </div>;
}
