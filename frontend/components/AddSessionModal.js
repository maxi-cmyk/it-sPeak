"use client";
import { useState } from "react";

export default function AddSessionModal({ onClose, onConfirm }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleFile = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="session-dialog-title">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-panel max-w-md">
        <div className="flex items-center justify-between mb-6">
          <div><p className="page-kicker mb-1">New rehearsal</p><h2 id="session-dialog-title" className="text-lg font-semibold text-zinc-50">Upload your recording</h2></div>
          <button onClick={onClose} className="icon-button -mr-2" aria-label="Close upload dialog">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <label
          htmlFor="video-upload"
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl p-10 cursor-pointer transition-colors ${
            dragging
              ? "border-blue-400 bg-blue-500/10"
              : file
              ? "border-emerald-500 bg-emerald-500/10"
              : "border-zinc-700 hover:border-zinc-500 bg-zinc-800/50"
          }`}
        >
          <input id="video-upload" type="file" accept="video/*" className="hidden" onChange={handleFile} />
          {file ? (
            <>
              <div className="w-10 h-10 rounded-full bg-emerald-500/15 flex items-center justify-center text-emerald-700 text-xl">✓</div>
              <p className="max-w-full break-words text-center text-sm font-medium text-emerald-700">{file.name}</p>
              <p className="text-xs text-zinc-500">Click to choose a different file</p>
            </>
          ) : (
            <>
              <div className="w-12 h-12 rounded-full bg-zinc-700 flex items-center justify-center">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="text-zinc-400" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" />
                  <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
                </svg>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-zinc-300">Drag and drop your video here</p>
                <p className="mt-1 text-xs text-zinc-500">or choose a file from your device</p>
                <p className="mt-3 text-[11px] text-zinc-600">English video · up to 3 minutes</p>
              </div>
            </>
          )}
        </label>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="btn-secondary flex-1"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(file)}
            disabled={!file}
            className="btn-primary flex-1"
          >
            Analyse recording
          </button>
        </div>
      </div>
    </div>
  );
}
