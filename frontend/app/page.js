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
    try { await createProject({ name: form.name, goal: form.description || null, deadline: form.deadline || null }); setModal(null); await load(); }
    catch (error) { setState({ loading: false, error: error.message }); }
  };
  const handleEdit = async (id, form) => {
    try { await updateProject(id, { name: form.name, goal: form.description || null, deadline: form.deadline || null }); setModal(null); await load(); }
    catch (error) { setState({ loading: false, error: error.message }); }
  };
  const handlePin = async (project) => { await updateProject(project.id, { pinned: !project.pinned }); await load(); };
  const handleDelete = async (id) => { if (!window.confirm("Delete this project and all retained rehearsals? This cannot be undone.")) return; await deleteProject(id); await load(); };

  return (
    <div className="min-h-screen bg-zinc-950"><Navbar />
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-end justify-between mb-8"><div><p className="text-xs uppercase tracking-[0.22em] text-violet-400 mb-2">Practice archive</p><h1 className="text-2xl font-bold text-zinc-50">Dashboard</h1><p className="text-zinc-500 text-sm mt-1">Every project, baseline and rehearsal in one place.</p></div><button onClick={() => setModal("add")} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors">+ Add Project</button></div>
        {state.error && <div role="alert" className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"><p>{state.error}</p><button onClick={load} className="mt-2 underline">Try again</button></div>}
        {state.loading ? <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{[0,1,2].map((item) => <div key={item} className="h-48 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900" />)}</div> : projects.length === 0 ? <div className="flex flex-col items-center justify-center py-24 text-center rounded-2xl border border-dashed border-zinc-800"><div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-3xl mb-4">🎤</div><p className="text-zinc-300 font-medium mb-1">No projects yet</p><p className="text-zinc-600 text-sm">Create a project; its first successful rehearsal becomes your protected baseline.</p></div> : <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{projects.map((project) => <ProjectCard key={project.id} project={project} onPin={() => handlePin(project)} onEdit={() => setModal({ type: "edit", project })} onDelete={() => handleDelete(project.id)} />)}</div>}
      </main>
      {modal === "add" && <AddProjectModal onConfirm={handleAdd} onClose={() => setModal(null)} />}
      {modal?.type === "edit" && <AddProjectModal initial={modal.project} onConfirm={(form) => handleEdit(modal.project.id, form)} onClose={() => setModal(null)} />}
    </div>
  );
}
