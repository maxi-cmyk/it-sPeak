"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { formatDate, getDaysUntilDeadline } from "@/lib/data";

export default function ProjectCard({ project, onPin, onEdit, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();
  const days = getDaysUntilDeadline(project.deadline);

  return (
    <div
      className="relative bg-zinc-900 border border-zinc-800 rounded-xl p-5 cursor-pointer hover:border-zinc-600 transition-all group"
      onClick={() => router.push(`/project/${project.id}`)}
    >
      {project.pinned && (
        <span className="absolute top-3 right-10 text-violet-400 text-xs">📌</span>
      )}

      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-zinc-50 text-base leading-snug pr-6 group-hover:text-violet-400 transition-colors">
          {project.name}
        </h3>
        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen((o) => !o); }}
          className="text-zinc-500 hover:text-zinc-200 transition-colors p-0.5 flex-shrink-0"
          aria-label="Options"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
          </svg>
        </button>
      </div>

      <p className="text-zinc-500 text-sm leading-relaxed mb-4 line-clamp-2">{project.description}</p>

      <div className="flex items-center gap-1.5 text-xs">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-zinc-500">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <span className={days !== null && days <= 30 ? "text-amber-400" : "text-zinc-500"}>
          {days === null ? "No deadline" : `${days > 0 ? `${days} days left` : "Deadline passed"} — ${formatDate(project.deadline)}`}
        </span>
      </div>

      {menuOpen && (
        <div
          className="absolute right-4 top-10 z-20 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl overflow-hidden w-36"
          onClick={(e) => e.stopPropagation()}
        >
          {[
            { label: project.pinned ? "Unpin" : "Pin", icon: "📌", action: onPin },
            { label: "Edit", icon: "✏️", action: onEdit },
            { label: "Delete", icon: "🗑️", action: onDelete, danger: true },
          ].map(({ label, icon, action, danger }) => (
            <button
              key={label}
              onClick={() => { action?.(); setMenuOpen(false); }}
              className={`w-full flex items-center gap-2 px-3 py-2.5 text-sm hover:bg-zinc-700 transition-colors ${danger ? "text-red-400" : "text-zinc-200"}`}
            >
              <span>{icon}</span> {label}
            </button>
          ))}
        </div>
      )}

      {menuOpen && (
        <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
      )}
    </div>
  );
}
