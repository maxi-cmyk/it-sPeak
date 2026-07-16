"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import RatingBar from "@/components/RatingBar";
import ScoreRing from "@/components/ScoreRing";
import VideoAnalysisPlayer from "@/components/VideoAnalysisPlayer";
import { getSessionAnalysis } from "@/lib/api";
import { getSessionById, formatDate } from "@/lib/data";
import { reportToSession } from "@/lib/reportAdapter";

const SkillRadar = dynamic(() => import("@/components/SkillRadar"), { ssr: false });
const TimelineChart = dynamic(() => import("@/components/TimelineChart"), { ssr: false });

export default function SessionSummaryPage() {
  const { id } = useParams();
  const [session, setSession] = useState(() => getSessionById(id));
  const [error, setError] = useState(null);
  const [accessToken, setAccessToken] = useState(null);

  useEffect(() => {
    if (getSessionById(id)) return;
    const projectId = new URLSearchParams(window.location.search).get("projectId") || "1";
    const cached = sessionStorage.getItem(`itspeak:session:${id}`);
    const metadata = cached ? JSON.parse(cached) : null;
    if (!metadata?.accessToken) {
      setError("This temporary analysis link has expired or is unavailable in this browser.");
      return;
    }
    setAccessToken(metadata.accessToken);
    if (metadata.report) {
      setSession(reportToSession(metadata.report, id, projectId, metadata.qualityGate));
      return;
    }
    const controller = new AbortController();
    getSessionAnalysis(id, metadata.accessToken, controller.signal)
      .then((payload) => {
        if (payload.status !== "success" || !payload.result) {
          throw new Error("This analysis is not ready yet.");
        }
        setSession(reportToSession(payload.result, id, projectId, payload.quality_gate));
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      });
    return () => controller.abort();
  }, [id]);

  if (!session) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-3 text-zinc-400">
        <span className={`h-2.5 w-2.5 rounded-full ${error ? "bg-red-400" : "bg-violet-400 animate-pulse"}`} />
        <p>{error || "Loading your analysis…"}</p>
      </div>
    );
  }

  const projectHref = `/project/${session.projectId}`;
  return (
    <div className="min-h-screen bg-zinc-950">
      <Navbar backHref={projectHref} />
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between mb-8">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-violet-400 mb-2">Combined analysis</p>
            <h1 className="text-2xl font-bold text-zinc-50">{session.name}</h1>
            <p className="text-zinc-500 text-sm mt-1">{session.duration} &bull; {formatDate(session.date)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-zinc-500 mb-1">Overall Score</p>
            <ScoreRing score={session.overallScore} size={110} />
          </div>
        </div>

        {accessToken && (
          <VideoAnalysisPlayer sessionId={id} token={accessToken} analysis={session.rawAnalysis} qualityGate={session.qualityGate} />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Coaching priorities</h2>
            <div className="flex flex-col gap-4">
              {session.feedback.map((item, index) => (
                <div key={`${item.text}-${index}`} className="flex gap-3">
                  <span className="text-lg flex-shrink-0 mt-0.5">{item.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{item.text}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">→ {item.tip}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Current rating vs target</h2>
            <div className="flex flex-col gap-4">
              <RatingBar label="Tone" value={session.tone} target={session.targetTone} />
              <RatingBar label="Body" value={session.body} target={session.targetBody} />
              <RatingBar label="Face" value={session.face} target={session.targetFace} />
            </div>
          </section>
        </div>

        {session.audioMetrics && (
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            {Object.entries(session.audioMetrics).map(([key, metric]) => (
              <div key={key} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                <p className="text-xs uppercase tracking-wider text-zinc-500">{key}</p>
                <p className="mt-2 text-xl font-semibold text-zinc-100">{metric.value}</p>
                <p className="mt-1 text-xs text-zinc-500">{metric.label} · score {Math.round(metric.score)}</p>
              </div>
            ))}
          </section>
        )}

        {session.transcript && (
          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 mb-6">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Transcript</h2>
            <p className="text-sm leading-7 text-zinc-300">{session.transcript}</p>
          </section>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Pillar snapshot</h2>
            <TimelineChart data={session.timelineData} />
          </section>
          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Skill breakdown</h2>
            <SkillRadar data={session.radarData} />
          </section>
        </div>
      </main>
    </div>
  );
}
