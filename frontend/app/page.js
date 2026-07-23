"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import ProjectCard from "@/components/ProjectCard";
import AddProjectModal from "@/components/AddProjectModal";
import useApi from "@/hooks/useApi";
import { projectFromApi } from "@/lib/data";

export default function Dashboard() {
  const { authReady, createProject, deleteProject, listProjects, updateProject } = useApi();
  const [projects, setProjects] = useState([]);
  const [modal, setModal] = useState(null);
  const [state, setState] = useState({ loading: true, error: null });

  const load = async () => {
    setState({ loading: true, error: null });
    try { setProjects((await listProjects()).map(projectFromApi)); setState({ loading: false, error: null }); }
    catch (error) { setState({ loading: false, error: error.message }); }
  };
  useEffect(() => { if (authReady) load(); }, [authReady]);

  const handleAdd = async (form) => {
    try { await createProject({ name: form.name, goal: form.description || null, deadline: form.deadline || null, improvement_areas: form.improvementAreas, default_archetype_key: form.archetype }); setModal(null); await load(); }
    catch (error) { setState({ loading: false, error: error.message }); }
  };
  const handleEdit = async (id, form) => {
    try { await updateProject(id, { name: form.name, goal: form.description || null, deadline: form.deadline || null, improvement_areas: form.improvementAreas, default_archetype_key: form.archetype }); setModal(null); await load(); }
    catch (error) { setState({ loading: false, error: error.message }); }
  };
  const handlePin = async (project) => { await updateProject(project.id, { pinned: !project.pinned }); await load(); };
  const handleDelete = async (id) => { if (!window.confirm("Delete this project and all retained rehearsals? This cannot be undone.")) return; await deleteProject(id); await load(); };

  return (
    <div className="app-shell"><Navbar />
      <main className="page-container">
        <header className="page-header">
          <div>
            <h1 className="sr-only">Projects</h1>
            <p className="page-kicker">Practice archive</p>
          </div>
          <button onClick={() => setModal("add")} className="btn-primary w-full sm:w-auto">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            New project
          </button>
        </header>
        {state.error && <div role="alert" className="status-panel mb-6 border-red-500/30 bg-red-500/10 text-red-700"><p className="font-medium">Projects could not be loaded.</p><p className="mt-1 text-xs text-red-700">{state.error}</p><button onClick={load} className="btn-quiet mt-4 border-red-500/40 text-red-700 hover:bg-red-500/10">Try again</button></div>}
        {state.loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Loading projects">{[0,1,2].map((item) => <div key={item} className="h-52 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900" />)}</div>
        ) : projects.length === 0 ? (
          <section className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-800 px-6 py-20 text-center">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900 text-zinc-400">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h5M8 16h3"/></svg>
            </div>
            <h2 className="text-base font-semibold text-zinc-200">Set up your first rehearsal project</h2>
            <p className="mt-3 max-w-md text-sm leading-6 text-zinc-500">Choose the speaking areas you want to improve. Your first successful analysis becomes the protected baseline.</p>
            <button onClick={() => setModal("add")} className="btn-primary mt-6">Create first project</button>
          </section>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{projects.map((project) => <ProjectCard key={project.id} project={project} onPin={() => handlePin(project)} onEdit={() => setModal({ type: "edit", project })} onDelete={() => handleDelete(project.id)} />)}</div>
        )}
      </main>
      {modal === "add" && <AddProjectModal onConfirm={handleAdd} onClose={() => setModal(null)} />}
      {modal?.type === "edit" && <AddProjectModal initial={modal.project} onConfirm={(form) => handleEdit(modal.project.id, form)} onClose={() => setModal(null)} />}
    </div>
  );
}
