"use client";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import Navbar from "@/components/Navbar";
import ScoreRing from "@/components/ScoreRing";
import RatingBar from "@/components/RatingBar";
import { getSessionById, formatDate } from "@/lib/data";

const SkillRadar = dynamic(() => import("@/components/SkillRadar"), { ssr: false });
const TimelineChart = dynamic(() => import("@/components/TimelineChart"), { ssr: false });

export default function SessionSummaryPage() {
  const { id } = useParams();
  const session = getSessionById(id);

  if (!session) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-zinc-500">
        Session not found.
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
            <h1 className="text-2xl font-bold text-zinc-50">{session.name}</h1>
            <p className="text-zinc-500 text-sm mt-1">
              {session.duration} &bull; {formatDate(session.date)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-zinc-500 mb-1">Overall Score</p>
            <ScoreRing score={session.overallScore} size={110} />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Top Feedback</h2>
            <div className="flex flex-col gap-4">
              {session.feedback.map((item, i) => (
                <div key={i} className="flex gap-3">
                  <span className="text-lg flex-shrink-0 mt-0.5">{item.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{item.text}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">→ {item.tip}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">
              Current Rating vs Target
            </h2>
            <div className="flex flex-col gap-4">
              <RatingBar label="Tone" value={session.tone} target={session.targetTone} />
              <RatingBar label="Body" value={session.body} target={session.targetBody} />
              <RatingBar label="Face" value={session.face} target={session.targetFace} />
            </div>
            <p className="text-xs text-zinc-600 mt-4">
              <span className="inline-block w-0.5 h-3 bg-zinc-500 mr-1 align-middle" /> target
            </p>
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 mb-6">
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Video Playback</h2>
          <div className="relative bg-zinc-800 rounded-lg overflow-hidden" style={{ paddingBottom: "42%", minHeight: 180 }}>
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <button className="w-14 h-14 rounded-full bg-violet-600 hover:bg-violet-500 flex items-center justify-center transition-colors shadow-lg">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              </button>
              <p className="text-xs text-zinc-500">Video playback — {session.duration}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Pillar Timeline</h2>
            <TimelineChart data={session.timelineData} />
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Skill Breakdown</h2>
            <SkillRadar data={session.radarData} />
          </div>
        </div>
      </main>
    </div>
  );
}
