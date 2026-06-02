"use client";
import { useState, useEffect } from "react";

const STEPS = [
  "Uploading video",
  "Checking quality",
  "Transcribing audio",
  "Analysing facial presence",
  "Analysing body language",
  "Analysing vocal pattern",
  "Generating report",
];

export default function ProcessingModal({ onComplete, onCancel }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [done, setDone] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(80);

  useEffect(() => {
    if (done) return;
    if (currentStep >= STEPS.length) {
      setDone(true);
      return;
    }
    const stepDuration = currentStep < 2 ? 800 : 1400;
    const t = setTimeout(() => setCurrentStep((s) => s + 1), stepDuration);
    return () => clearTimeout(t);
  }, [currentStep, done]);

  useEffect(() => {
    if (done || secondsLeft <= 0) return;
    const t = setTimeout(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearTimeout(t);
  }, [secondsLeft, done]);

  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;
  const timeStr = `${mins > 0 ? `${mins}min ` : ""}${secs}s`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
      <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <h2 className="text-lg font-semibold text-zinc-50 mb-1">
          {done ? "Analysis Complete!" : "Analysing your session…"}
        </h2>
        {!done && (
          <p className="text-sm text-zinc-500 mb-5">Estimated time remaining: {timeStr}</p>
        )}

        <div className="flex flex-col gap-3 mb-6">
          {STEPS.map((step, i) => {
            const completed = i < currentStep;
            const active = i === currentStep;
            const pending = i > currentStep;
            return (
              <div key={step} className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold transition-all duration-300 ${
                  completed
                    ? "bg-emerald-500 text-white"
                    : active
                    ? "bg-violet-500 text-white animate-pulse"
                    : "bg-zinc-800 text-zinc-600"
                }`}>
                  {completed ? "✓" : i + 1}
                </div>
                <span className={`text-sm transition-colors ${
                  completed ? "text-emerald-400 line-through decoration-emerald-800" : active ? "text-zinc-50 font-medium" : "text-zinc-600"
                }`}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>

        {!done && (
          <div className="mb-5">
            <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-violet-500 rounded-full transition-all duration-700"
                style={{ width: `${(currentStep / STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        {done ? (
          <button
            onClick={onComplete}
            className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-colors"
          >
            View Results →
          </button>
        ) : (
          <button
            onClick={onCancel}
            className="w-full py-2.5 rounded-lg border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 text-sm transition-colors"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
