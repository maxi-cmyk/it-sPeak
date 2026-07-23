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
  const [modalState, setModalState] = useState({ saving: false, error: null });
  const [pendingProjectId, setPendingProjectId] = useState(null);
  const [state, setState] = useState({ loading: true, error: null, errorTitle: null });

  const load = async () => {
    setState({ loading: true, error: null, errorTitle: null });
    try {
      setProjects((await listProjects()).map(projectFromApi));
      setState({ loading: false, error: null, errorTitle: null });
    } catch (error) {
      setState({ loading: false, error: error.message, errorTitle: "Projects could not be loaded." });
    }
  };
  useEffect(() => { if (authReady) load(); }, [authReady]);

  const handleAdd = async (form) => {
    setModalState({ saving: true, error: null });
    try {
      await createProject({ name: form.name, goal: form.description || null, deadline: form.deadline || null, improvement_areas: form.improvementAreas, default_archetype_key: form.archetype });
      setModal(null);
      setModalState({ saving: false, error: null });
      await load();
    } catch (error) {
      setModalState({ saving: false, error: error.message });
    }
  };
  const handleEdit = async (id, form) => {
    setModalState({ saving: true, error: null });
    try {
      await updateProject(id, { name: form.name, goal: form.description || null, deadline: form.deadline || null, improvement_areas: form.improvementAreas, default_archetype_key: form.archetype });
      setModal(null);
      setModalState({ saving: false, error: null });
      await load();
    } catch (error) {
      setModalState({ saving: false, error: error.message });
    }
  };
  const handlePin = async (project) => {
    setPendingProjectId(project.id);
    try {
      await updateProject(project.id, { pinned: !project.pinned });
      setProjects((current) => current.map((item) => item.id === project.id ? { ...item, pinned: !item.pinned } : item));
      setState((current) => ({ ...current, error: null, errorTitle: null }));
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, errorTitle: "The project pin could not be updated." }));
    } finally {
      setPendingProjectId(null);
    }
  };
  const handleDelete = async (id) => {
    if (!window.confirm("Delete this project and all its sessions? This cannot be undone.")) return;
    setPendingProjectId(id);
    try {
      await deleteProject(id);
      setProjects((current) => current.filter((project) => project.id !== id));
      setState((current) => ({ ...current, error: null, errorTitle: null }));
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, errorTitle: "The project could not be deleted." }));
    } finally {
      setPendingProjectId(null);
    }
  };

  const openAddModal = () => {
    setModalState({ saving: false, error: null });
    setModal("add");
  };

  const openEditModal = (project) => {
    setModalState({ saving: false, error: null });
    setModal({ type: "edit", project });
  };

  return (
    <div className="app-shell"><Navbar />
      <main className="page-container">
        <header className="archive-header">
          <div className="min-w-0">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 className="page-title">Practice archive</h1>
              {!state.loading && !state.error && <p className="text-sm text-zinc-400" aria-live="polite">{projects.length} {projects.length === 1 ? "project" : "projects"}</p>}
            </div>
          </div>
          {!state.loading && projects.length > 0 && <button onClick={openAddModal} className="btn-primary w-full sm:w-auto">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            New project
          </button>}
        </header>
        {state.error && <div role="alert" className="status-panel mb-6 border-red-500/30 bg-red-500/10 text-red-700"><p className="font-semibold">{state.errorTitle}</p><p className="mt-1 text-sm text-red-700">{state.error}</p>{projects.length === 0 && <button onClick={load} className="btn-quiet mt-3 border-red-500/40 text-red-700 hover:bg-red-500/10">Try again</button>}</div>}
        {state.loading ? (
          <div role="status" aria-live="polite">
            <span className="sr-only">Loading projects</span>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">{[0,1,2].map((item) => <div key={item} className="surface-card h-80 animate-pulse"><div className="h-5 w-2/3 rounded bg-zinc-800" /><div className="mt-5 h-4 w-full rounded bg-zinc-800" /><div className="mt-2 h-4 w-4/5 rounded bg-zinc-800" /><div className="mt-7 h-4 w-28 rounded bg-zinc-800" /><div className="mt-3 flex gap-2"><div className="h-7 w-20 rounded-full bg-zinc-800" /><div className="h-7 w-24 rounded-full bg-zinc-800" /></div><div className="mt-8 border-t border-zinc-800 pt-4"><div className="h-3 w-32 rounded bg-zinc-800" /><div className="mt-3 grid grid-cols-5 gap-1.5">{[0,1,2,3,4].map((segment) => <div key={segment} className="h-1 rounded-full bg-zinc-800" />)}</div></div></div>)}</div>
          </div>
        ) : state.error && projects.length === 0 ? null : projects.length === 0 ? (
          <section className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-700 bg-zinc-900/45 px-6 py-16 text-center sm:py-20">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl border border-zinc-700 bg-zinc-800 text-zinc-400">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h5M8 16h3"/></svg>
            </div>
            <h2 className="text-lg font-semibold text-zinc-100">Set up your first rehearsal project</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-zinc-400">Choose the speaking areas you want to improve. Session 1 will be used as the baseline for your progress.</p>
            <button onClick={openAddModal} className="btn-primary mt-6">Create first project</button>
          </section>
        ) : (
          <section aria-label="Rehearsal projects" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{projects.map((project) => <ProjectCard key={project.id} project={project} pending={pendingProjectId === project.id} onPin={() => handlePin(project)} onEdit={() => openEditModal(project)} onDelete={() => handleDelete(project.id)} />)}</section>
        )}
      </main>
      {modal === "add" && <AddProjectModal submitting={modalState.saving} submitError={modalState.error} onConfirm={handleAdd} onClose={() => { if (!modalState.saving) setModal(null); }} />}
      {modal?.type === "edit" && <AddProjectModal initial={modal.project} submitting={modalState.saving} submitError={modalState.error} onConfirm={(form) => handleEdit(modal.project.id, form)} onClose={() => { if (!modalState.saving) setModal(null); }} />}
    </div>
  );
}
