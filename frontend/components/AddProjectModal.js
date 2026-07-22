"use client";
import { useEffect, useState } from "react";
import { improvementAreaGroups, improvementAreaValues } from "@/lib/improvementAreas.mjs";
import useApi from "@/hooks/useApi";

export default function AddProjectModal({ initial, onConfirm, onClose, submitting = false, submitError = null }) {
  const { authReady, listArchetypes } = useApi();
  const [archetypes, setArchetypes] = useState([]);
  const [form, setForm] = useState({
    name: "",
    description: "",
    deadline: "",
    ...initial,
    archetype: initial?.archetype || "corporate_board",
    improvementAreas: initial?.improvementAreas || improvementAreaValues,
  });

  useEffect(() => {
    if (!authReady) return undefined;
    const controller = new AbortController();
    listArchetypes(controller.signal).then(setArchetypes).catch(() => {});
    return () => controller.abort();
  }, [authReady]);

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
    if (submitting || !form.name.trim() || form.improvementAreas.length === 0) return;
    onConfirm(form);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="project-dialog-title">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-panel max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 id="project-dialog-title" className="text-lg font-semibold text-zinc-50">
            {initial ? "Edit Project" : "New Project"}
          </h2>
          <button onClick={onClose} className="icon-button -mr-2" aria-label="Close project dialog">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {submitError && (
            <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-700">
              Project changes could not be saved. {submitError}
            </div>
          )}
          <div>
            <label className="field-label" htmlFor="project-name">Project name</label>
            <input
              id="project-name"
              type="text"
              required
              placeholder="e.g. TED Talk prep"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="field-control"
            />
          </div>
          {archetypes.length > 0 && (
            <fieldset>
              <legend className="field-label">Speaking archetype</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {archetypes.filter((item) => item.status === "enabled").map((item) => {
                  const selected = form.archetype === item.key;
                  return (
                    <button
                      key={item.key}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setForm({ ...form, archetype: item.key })}
                      className={`min-h-10 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${selected ? "text-accent border-blue-600/60 bg-blue-500/10 shadow-[inset_0_0_0_1px_rgba(37,99,235,0.14)]" : "border-zinc-700 bg-zinc-950/40 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"}`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}
          <fieldset>
            <legend className="field-label mb-0">Fields to improve</legend>
            <p className="mb-4 mt-1 text-xs leading-5 text-zinc-500">
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
                          className={`relative min-h-24 rounded-xl border p-3 text-left transition-[border-color,background-color,box-shadow] duration-150 ${selected ? "border-blue-600/60 bg-blue-500/10 shadow-[inset_0_0_0_1px_rgba(37,99,235,0.14)]" : "border-zinc-700 bg-zinc-950/40 hover:border-zinc-600 hover:bg-zinc-800/50"}`}
                        >
                          <span className={`mb-2 flex h-7 w-7 items-center justify-center rounded-lg text-sm ${selected ? "bg-blue-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>{option.icon}</span>
                          <span className="block text-sm font-medium text-zinc-100">{option.label}</span>
                          <span className="mt-0.5 block text-[11px] leading-4 text-zinc-500">{option.detail}</span>
                          <span className={`absolute right-2.5 top-2.5 flex h-5 w-5 items-center justify-center rounded-full border text-[11px] ${selected ? "border-blue-600 bg-blue-600 text-white" : "border-zinc-700 text-transparent"}`}>✓</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
            {form.improvementAreas.length === 0 && <p role="alert" className="text-readiness mt-2 text-xs">Select at least one field to continue.</p>}
          </fieldset>
          <div>
            <label className="field-label" htmlFor="project-description">Rehearsal goal</label>
            <textarea
              id="project-description"
              rows={3}
              placeholder="What are you preparing for?"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="field-control resize-none"
            />
          </div>
          <div>
            <label className="field-label" htmlFor="project-deadline">Deadline</label>
            <input
              id="project-deadline"
              type="date"
              value={form.deadline}
              onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              className="field-control"
            />
          </div>
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !form.name.trim() || form.improvementAreas.length === 0}
              className="btn-primary flex-1"
            >
              {submitting ? "Saving…" : initial ? "Save Changes" : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
