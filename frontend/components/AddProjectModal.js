"use client";
import { useState } from "react";
import { improvementAreaGroups, improvementAreaValues } from "@/lib/improvementAreas.mjs";

export default function AddProjectModal({ initial, onConfirm, onClose }) {
  const [form, setForm] = useState({
    name: "",
    description: "",
    deadline: "",
    ...initial,
    improvementAreas: initial?.improvementAreas || improvementAreaValues,
  });

  const toggleImprovementArea = (area) => {
    setForm((current) => ({
      ...current,
      improvementAreas: current.improvementAreas.includes(area)
        ? current.improvementAreas.filter((item) => item !== area)
        : [...current.improvementAreas, area],
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name.trim() || form.improvementAreas.length === 0) return;
    onConfirm(form);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-zinc-50">
            {initial ? "Edit Project" : "New Project"}
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Project Name</label>
            <input
              type="text"
              required
              placeholder="e.g. TED Talk prep"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-violet-500 transition-colors"
            />
          </div>
          <fieldset>
            <legend className="text-xs text-zinc-400">Fields to improve</legend>
            <p className="mb-3 mt-1 text-xs leading-relaxed text-zinc-600">
              Choose one or more. Your results will rank these by score and redirect your focus once you pass 80.
            </p>
            <div className="space-y-4">
              {improvementAreaGroups.map((group) => (
                <section key={group.key} aria-labelledby={`${group.key}-improvement-heading`}>
                  <div className="mb-2 flex items-baseline justify-between gap-3">
                    <h3 id={`${group.key}-improvement-heading`} className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-300">{group.label}</h3>
                    <span className="text-[10px] text-zinc-600">{group.detail}</span>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {group.options.map((option) => {
                      const selected = form.improvementAreas.includes(option.value);
                      return (
                        <button
                          key={option.value}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => toggleImprovementArea(option.value)}
                          className={`relative min-h-24 rounded-xl border p-3 text-left transition-all ${selected ? "border-violet-400 bg-violet-500/10 shadow-[inset_0_0_0_1px_rgba(167,139,250,0.18)]" : "border-zinc-700 bg-zinc-950/40 hover:border-zinc-600"}`}
                        >
                          <span className={`mb-2 flex h-7 w-7 items-center justify-center rounded-lg text-sm ${selected ? "bg-violet-400 text-zinc-950" : "bg-zinc-800 text-zinc-400"}`}>{option.icon}</span>
                          <span className="block text-sm font-medium text-zinc-100">{option.label}</span>
                          <span className="mt-0.5 block text-[11px] leading-4 text-zinc-500">{option.detail}</span>
                          <span className={`absolute right-2.5 top-2.5 flex h-5 w-5 items-center justify-center rounded-full border text-[11px] ${selected ? "border-violet-400 bg-violet-400 text-zinc-950" : "border-zinc-700 text-transparent"}`}>✓</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
            {form.improvementAreas.length === 0 && <p role="alert" className="mt-2 text-xs text-amber-300">Select at least one field to continue.</p>}
          </fieldset>
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Description</label>
            <textarea
              rows={3}
              placeholder="What is this project about?"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-violet-500 transition-colors resize-none"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Deadline</label>
            <input
              type="date"
              value={form.deadline}
              onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-zinc-50 focus:outline-none focus:border-violet-500 transition-colors"
            />
          </div>
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-lg border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!form.name.trim() || form.improvementAreas.length === 0}
              className="flex-1 rounded-lg bg-violet-600 py-2.5 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-500"
            >
              {initial ? "Save Changes" : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
