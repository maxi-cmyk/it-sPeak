"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import ProjectCard from "@/components/ProjectCard";
import AddProjectModal from "@/components/AddProjectModal";
import { initialProjects } from "@/lib/data";

export default function Dashboard() {
  const [projects, setProjects] = useState(initialProjects);
  const [modal, setModal] = useState(null); // null | "add" | { type: "edit", project }

  const handleAdd = (form) => {
    setProjects((prev) => [
      ...prev,
      { id: Date.now().toString(), ...form, pinned: false },
    ]);
    setModal(null);
  };

  const handleEdit = (id, form) => {
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, ...form } : p)));
    setModal(null);
  };

  const handlePin = (id) => {
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, pinned: !p.pinned } : p)));
  };

  const handleDelete = (id) => {
    setProjects((prev) => prev.filter((p) => p.id !== id));
  };

  const sorted = [...projects].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));

  return (
    <div className="min-h-screen bg-zinc-950">
      <Navbar />
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-zinc-50">Dashboard</h1>
            <p className="text-zinc-500 text-sm mt-1">Manage your practice projects</p>
          </div>
          <button
            onClick={() => setModal("add")}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add Project
          </button>
        </div>

        {sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-3xl mb-4">🎤</div>
            <p className="text-zinc-300 font-medium mb-1">No projects yet</p>
            <p className="text-zinc-600 text-sm">Create your first project to get started</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sorted.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onPin={() => handlePin(project.id)}
                onEdit={() => setModal({ type: "edit", project })}
                onDelete={() => handleDelete(project.id)}
              />
            ))}
          </div>
        )}
      </main>

      {modal === "add" && (
        <AddProjectModal onConfirm={handleAdd} onClose={() => setModal(null)} />
      )}
      {modal?.type === "edit" && (
        <AddProjectModal
          initial={modal.project}
          onConfirm={(form) => handleEdit(modal.project.id, form)}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}
