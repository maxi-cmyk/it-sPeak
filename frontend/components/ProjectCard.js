"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { formatDate, getDaysUntilDeadline } from "@/lib/data";
import { improvementAreaLabels } from "@/lib/improvementAreas.mjs";

export default function ProjectCard({ project, pending = false, onPin, onEdit, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef(null);
  const days = getDaysUntilDeadline(project.deadline);
  const sessionCount = Math.max(0, Math.min(5, Number(project.session_count) || 0));
  const deadlineTone = days === null ? "text-zinc-400" : days < 0 ? "text-warning" : days <= 30 ? "text-readiness" : "text-zinc-400";
  const deadlineLabel = days === null
    ? "No deadline"
    : `${days < 0 ? "Deadline passed" : days === 0 ? "Due today" : `${days} ${days === 1 ? "day" : "days"} left`} · ${formatDate(project.deadline)}`;

  useEffect(() => {
    if (!menuOpen) return undefined;
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [menuOpen]);

  return (
    <article className="surface-card-interactive group relative h-full min-h-80 p-0 hover:shadow-lg hover:shadow-black/10">
      <Link href={`/project/${project.id}`} aria-label={`Open ${project.name}`} className="flex h-full min-h-80 flex-col rounded-xl p-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-blue-400">
        <div className="mb-3 flex min-w-0 items-start gap-2 pr-10">
          <h2 className="group-hover-accent min-w-0 break-words text-lg font-semibold leading-snug text-zinc-50 transition-colors">{project.name}</h2>
          {project.pinned && <span className="text-accent mt-0.5 flex-shrink-0" title="Pinned project"><span className="sr-only">Pinned</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m12 17 5 5M5 3l14 14M5 3l4 4-3 5 6 6 5-3 4 4M4 20l4-4" /></svg></span>}
        </div>

        <p className="mb-5 line-clamp-2 min-h-12 text-sm leading-6 text-zinc-400">{project.description || "No project description added yet."}</p>

        <div className="mb-6">
          <p className="mb-2 text-xs font-semibold text-zinc-400">Areas to improve</p>
          <div className="flex flex-wrap gap-1.5">
            {(project.improvementAreas || []).map((area) => <span key={area} className="chip chip-selected px-2.5 py-1">{improvementAreaLabels[area] || area}</span>)}
          </div>
        </div>

        <div className="mt-auto border-t border-zinc-800 pt-4">
          <div className="flex items-baseline justify-between gap-3 text-xs">
            <span className="font-medium text-zinc-400">Sessions</span>
            <span className="font-semibold text-zinc-300">{sessionCount}/5</span>
          </div>
          <div className="mt-2 grid grid-cols-5 gap-1.5" aria-hidden="true">
            {Array.from({ length: 5 }, (_, index) => <span key={index} className={`h-1 rounded-full ${index < sessionCount ? "bg-zinc-400" : "bg-zinc-800"}`} />)}
          </div>
          <div className={`mt-4 flex items-start gap-2 text-xs ${deadlineTone}`}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 flex-shrink-0" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
            <span>{deadlineLabel}</span>
          </div>
        </div>
      </Link>

      <button
        ref={menuButtonRef}
        type="button"
        onClick={() => setMenuOpen((open) => !open)}
        disabled={pending}
        className="icon-button absolute right-3 top-3 z-30"
        aria-label={`Project options for ${project.name}`}
        aria-expanded={menuOpen}
        aria-controls={`project-menu-${project.id}`}
      >
        {pending ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-500 border-t-blue-500" aria-hidden="true" /> : <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" /></svg>}
      </button>

      {menuOpen && (
        <div
          id={`project-menu-${project.id}`}
          className="absolute right-3 top-12 z-30 w-40 overflow-hidden rounded-lg border border-zinc-700 bg-zinc-800 p-1 shadow-xl shadow-black/20"
        >
          {[
            { label: project.pinned ? "Unpin" : "Pin", action: onPin },
            { label: "Edit", action: onEdit },
            { label: "Delete", action: onDelete, danger: true },
          ].map(({ label, action, danger }) => (
            <button
              key={label}
              type="button"
              disabled={pending}
              onClick={() => { setMenuOpen(false); action?.(); }}
              className={`flex min-h-10 w-full items-center rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-zinc-700 disabled:cursor-wait disabled:opacity-50 ${danger ? "text-red-700" : "text-zinc-200"}`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {menuOpen && (
        <button type="button" tabIndex={-1} aria-label="Close project options" className="fixed inset-0 z-20 cursor-default" onClick={() => setMenuOpen(false)} />
      )}
    </article>
  );
}
