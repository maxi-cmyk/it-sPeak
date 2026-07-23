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
import { buildProgressData } from "@/lib/progressData.mjs";
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
  const deadlineStatus = days === null ? null : days > 0 ? `${days} days remaining` : days === 0 ? "Deadline today" : "Deadline passed";
  const progressData = buildProgressData(sessions);
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
  if (!project) return <div className="app-shell flex items-center justify-center gap-3 text-zinc-400"><span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-400" /><span>Loading project…</span></div>;
  return <div className="app-shell"><Navbar backHref="/" />
    <main className="page-container">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className={`flex flex-col gap-6 ${latest ? "lg:col-span-2" : "lg:col-span-3"}`}>
          <header className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900">
            <div className="p-5 sm:p-6">
              <div className="flex flex-col items-start justify-between gap-5 sm:flex-row">
                <div className="min-w-0">
                  <p className="page-kicker">{sessions.length}/5 sessions</p>
                  <h1 className="page-title break-words">{project.name}</h1>
                  <p className="page-summary">{project.description || "No project description added yet."}</p>
                </div>
                <button onClick={openProjectEditor} className="btn-secondary w-full shrink-0 sm:w-auto" aria-label={`Edit ${project.name}`}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                  Edit project
                </button>
              </div>
            </div>

            <div className="grid border-t border-zinc-800 sm:grid-cols-2">
              <section className="p-5 sm:p-6" aria-labelledby="selected-archetype-heading">
                <h2 id="selected-archetype-heading" className="section-label">Selected archetype</h2>
                <p className="mt-2 text-base font-semibold text-zinc-100">{archetypeLabels[project.archetype] || project.archetype}</p>
              </section>
              <section className="border-t border-zinc-800 p-5 sm:border-l sm:border-t-0 sm:p-6" aria-labelledby="project-deadline-heading">
                <h2 id="project-deadline-heading" className="section-label">Deadline</h2>
                {project.deadline ? <>
                  <p className={`mt-2 text-base font-semibold ${days !== null && days <= 30 ? "text-readiness" : "text-zinc-100"}`}>{deadlineStatus}</p>
                  <p className="mt-1 text-sm text-zinc-500">{formatDate(project.deadline)}</p>
                </> : <>
                  <p className="mt-2 text-base font-semibold text-zinc-300">No deadline set</p>
                  <p className="mt-1 text-sm text-zinc-500">Add one from Edit project when your event date is confirmed.</p>
                </>}
              </section>
            </div>

            <section className="border-t border-zinc-800 p-5 sm:p-6" aria-labelledby="selected-focus-heading">
              <h2 id="selected-focus-heading" className="section-label mb-4">Areas to improve</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {improvementAreaGroups.map((group) => {
                  const selected = project.improvementAreas.filter((area) => improvementAreaGroupByValue[area] === group.key);
                  if (selected.length === 0) return null;
                  return <div key={group.key}>
                    <p className="mb-2 text-sm font-medium text-zinc-400">{group.label}</p>
                    <div className="flex flex-wrap gap-2">{selected.map((area) => <span key={area} className="chip chip-selected">{improvementAreaLabels[area]}</span>)}</div>
                  </div>;
                })}
              </div>
            </section>
          </header>

          <section className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900" aria-labelledby="sessions-heading">
            <div className="flex flex-col gap-3 border-b border-zinc-800 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div>
                <h2 id="sessions-heading" className="text-base font-semibold text-zinc-100">Sessions</h2>
                <p className="mt-1 text-sm text-zinc-500">Session 1 is used as the baseline for your progress.</p>
              </div>
              {sessions.length > 0 && <button onClick={() => setModal("allSessions")} className="btn-quiet w-full sm:w-auto">View all</button>}
            </div>
            <div className="p-4 sm:p-5">
              {sessions.length === 0 ? <div className="rounded-lg border border-dashed border-zinc-700 bg-zinc-800/45 px-6 py-10 text-center">
                <p className="mx-auto mb-5 max-w-md text-sm leading-6 text-zinc-400">Add Session 1 to set the baseline for your progress.</p>
                <button onClick={() => setModal("addSession")} className="btn-primary">Add first session</button>
              </div> : <div className="flex flex-col gap-3">{sessions.slice(0,3).map((session,index) => <SessionCard key={session.id} session={session} prev={sessions[index+1]} onClick={() => router.push(`/session/${session.id}`)} />)}</div>}
            </div>
          </section>
        </div>

        {latest && <aside className="flex flex-col gap-5 lg:sticky lg:top-24 lg:self-start">
          <div className="surface-card">
            <h2 className="section-label">Latest session</h2>
            <p className="mt-2 text-sm font-semibold text-zinc-100">{latest.name}</p>
            <p className="mt-1 text-sm text-zinc-500">{formatDate(latest.date)}</p>
            <div className="my-5 flex justify-center"><ScoreRing score={latest.overallScore} /></div>
            <div className="flex flex-col gap-3"><RatingBar label="Voice" value={latest.tone} target={85} /><RatingBar label="Body" value={latest.body} target={85} /><RatingBar label="Facial expressions" value={latest.face} target={85} /></div>
          </div>
          <button onClick={() => setModal("addSession")} className="btn-primary w-full">New session</button>
        </aside>}
      </div>

      {sessions.length > 0 && <section className="surface-card mt-8" aria-labelledby="progress-heading">
        <div className="mb-5 border-b border-zinc-800 pb-4">
          <h2 id="progress-heading" className="text-base font-semibold text-zinc-100">Progress over time</h2>
          <p className="mt-1 text-sm text-zinc-500">See how each session compares with Session 1.</p>
        </div>
        <TimelineChart data={progressData} />
      </section>}
    </main>
    {modal === "allSessions" && <AllSessionsModal sessions={sessions} projectId={id} onClose={() => setModal(null)} onAddSession={() => setModal("addSession")} />}
    {modal === "editProject" && <AddProjectModal initial={project} submitting={editState.saving} submitError={editState.error} onConfirm={handleProjectEdit} onClose={() => { if (!editState.saving) setModal(null); }} />}
    {modal === "addSession" && <AddSessionModal onClose={() => setModal(null)} onConfirm={handleSessionUpload} />}
    {modal === "processing" && <ProcessingModal job={analysisJob} onComplete={() => { load(); router.push(`/session/${analysisJob.sessionId}`); }} onConfirm={analysisJob.confirm} onReplace={analysisJob.chooseReplacement} onCancel={() => { analysisJob.reset(); setModal(null); }} />}
  </div>;
}
