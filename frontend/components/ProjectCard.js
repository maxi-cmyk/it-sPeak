"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { formatDate, getDaysUntilDeadline } from "@/lib/data";

export default function ProjectCard({ project, onPin, onEdit, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();
  const days = getDaysUntilDeadline(project.deadline);

  return (
    <article
      className="surface-card-interactive group relative flex min-h-52 cursor-pointer flex-col hover:shadow-xl hover:shadow-black/10"
      onClick={() => router.push(`/project/${project.id}`)}
      onKeyDown={(event) => { if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); router.push(`/project/${project.id}`); } }}
      role="link"
      tabIndex={0}
    >
      {project.pinned && (
        <span className="text-accent absolute right-11 top-4" title="Pinned project">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m12 17 5 5M5 3l14 14M5 3l4 4-3 5 6 6 5-3 4 4M4 20l4-4" /></svg>
        </span>
      )}

      <div className="flex items-start justify-between mb-4">
        <h3 className="group-hover-accent pr-6 text-base font-semibold leading-snug text-zinc-50 transition-colors">
          {project.name}
        </h3>
        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen((o) => !o); }}
          className="icon-button -mr-2 -mt-2 flex-shrink-0"
          aria-label="Options"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
          </svg>
        </button>
      </div>

      <p className="mb-4 line-clamp-2 min-h-10 text-sm leading-5 text-zinc-400">{project.description || "No rehearsal goal added yet."}</p>

      <p className="mb-4 text-xs font-semibold text-zinc-500">
        {project.session_count ?? 0}/5 sessions
      </p>

      <div className="mt-auto flex items-center gap-2 border-t border-zinc-800 pt-4 text-xs">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-zinc-500">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <span className={days !== null && days <= 30 ? "text-readiness" : "text-zinc-500"}>
          {days === null ? "No deadline" : `${days > 0 ? `${days} days left` : "Deadline passed"} — ${formatDate(project.deadline)}`}
        </span>
      </div>

      {menuOpen && (
        <div
          className="absolute right-4 top-12 z-20 w-36 overflow-hidden rounded-lg border border-zinc-700 bg-zinc-800 shadow-xl shadow-black/20"
          onClick={(e) => e.stopPropagation()}
        >
          {[
            { label: project.pinned ? "Unpin" : "Pin", action: onPin },
            { label: "Edit", action: onEdit },
            { label: "Delete", action: onDelete, danger: true },
          ].map(({ label, action, danger }) => (
            <button
              key={label}
              onClick={() => { action?.(); setMenuOpen(false); }}
              className={`flex w-full items-center px-3 py-3 text-left text-sm transition-colors hover:bg-zinc-700 ${danger ? "text-red-700" : "text-zinc-200"}`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {menuOpen && (
        <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
      )}
    </article>
  );
}
