"use client";
import { useEffect, useState } from "react";
import { improvementAreaGroups, improvementAreaValues } from "@/lib/improvementAreas.mjs";
import ImprovementAreaIcon from "@/components/ImprovementAreaIcon";
import useApi from "@/hooks/useApi";

const MAX_DESCRIPTION_WORDS = 100;
const countWords = (text) => (text.trim() ? text.trim().split(/\s+/).length : 0);

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

  const descriptionWordCount = countWords(form.description);
  const descriptionTooLong = descriptionWordCount > MAX_DESCRIPTION_WORDS;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (submitting || !form.name.trim() || form.improvementAreas.length === 0 || descriptionTooLong) return;
    onConfirm(form);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="project-dialog-title">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-panel max-w-lg">
        <div className="mb-5 flex items-center justify-between">
          <h2 id="project-dialog-title" className="text-lg font-semibold text-zinc-50">
            {initial ? "Edit project" : "New project"}
          </h2>
          <button onClick={onClose} disabled={submitting} className="icon-button -mr-2 disabled:cursor-wait disabled:opacity-50" aria-label="Close project dialog">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {submitError && (
            <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-3 text-sm text-red-700">
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
                      className={`flex min-h-12 items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors ${selected ? "text-accent border-blue-600/60 bg-blue-500/10 shadow-[inset_0_0_0_1px_rgba(37,99,235,0.14)]" : "border-zinc-700 bg-zinc-950/40 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"}`}
                    >
                      <span className="font-medium">{item.label}</span>
                      <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${selected ? "border-blue-600" : "border-zinc-600"}`} aria-hidden="true">
                        <span className={`h-2 w-2 rounded-full ${selected ? "bg-blue-600" : "bg-transparent"}`} />
                      </span>
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}
          <fieldset>
            <legend className="field-label mb-0">Fields to improve</legend>
            <p className="mb-4 mt-1 text-xs leading-5 text-zinc-500">
              Choose one or more. Your results will show which areas need the most work.
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
                          className={`relative min-h-20 rounded-xl border p-3 pr-11 text-left transition-[border-color,background-color,box-shadow] duration-150 ${selected ? "border-blue-600/60 bg-blue-500/10 shadow-[inset_0_0_0_1px_rgba(37,99,235,0.14)]" : "border-zinc-700 bg-zinc-950/40 hover:border-zinc-600 hover:bg-zinc-800/50"}`}
                        >
                          <span className="flex items-start gap-3">
                            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${selected ? "bg-blue-600 text-white" : "bg-zinc-800 text-zinc-400"}`}>
                              <ImprovementAreaIcon area={option.value} />
                            </span>
                            <span className="min-w-0 pt-0.5">
                              <span className="block text-sm font-semibold text-zinc-100">{option.label}</span>
                              <span className="mt-0.5 block text-sm leading-5 text-zinc-500">{option.detail}</span>
                            </span>
                          </span>
                          <span className={`absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-md border ${selected ? "border-blue-600 bg-blue-600 text-white" : "border-zinc-600 bg-zinc-900 text-transparent"}`} aria-hidden="true">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round"><path d="m3 8 3 3 7-7" /></svg>
                          </span>
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
            <div className="flex items-baseline justify-between">
              <label className="field-label" htmlFor="project-description">Rehearsal goal</label>
              <span className={`text-xs ${descriptionTooLong ? "text-warning" : "text-zinc-500"}`}>{descriptionWordCount}/{MAX_DESCRIPTION_WORDS} words</span>
            </div>
            <textarea
              id="project-description"
              rows={3}
              placeholder="What is this project preparing you for?"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="field-control resize-none"
              aria-invalid={descriptionTooLong}
            />
            {descriptionTooLong && <p role="alert" className="text-warning mt-2 text-xs">Keep your rehearsal goal under {MAX_DESCRIPTION_WORDS} words.</p>}
          </div>
          <div>
            <label className="field-label" htmlFor="project-deadline">Deadline</label>
            <input
              id="project-deadline"
              type="date"
              value={form.deadline}
              onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              className="field-control date-control"
            />
          </div>
          <div className="flex gap-3">
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
              disabled={submitting || !form.name.trim() || form.improvementAreas.length === 0 || descriptionTooLong}
              className="btn-primary flex-1"
            >
              {submitting ? "Saving…" : initial ? "Save changes" : "Create project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
