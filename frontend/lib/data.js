export const sessions = {
  s1: {
    id: "s1",
    projectId: "1",
    name: "Session 1",
    score: 64,
    overallScore: 64,
    tone: 70,
    body: 45,
    face: 70,
    targetTone: 85,
    targetBody: 70,
    targetFace: 90,
    date: "2026-05-12",
    duration: "3min 10s",
    verdict: "You are not ready!",
    feedback: [
      { icon: "⚡", text: "Pace too fast in opening", tip: "Slow down during key points" },
      { icon: "🤲", text: "Arms crossed frequently", tip: "Open posture builds connection" },
      { icon: "🎤", text: "Vocal variety limited", tip: "Vary pitch to emphasise key words" },
    ],
    radarData: [
      { subject: "Facial", score: 70, fullMark: 100 },
      { subject: "Filler", score: 55, fullMark: 100 },
      { subject: "Tone", score: 65, fullMark: 100 },
      { subject: "Pace", score: 60, fullMark: 100 },
      { subject: "Vocal", score: 68, fullMark: 100 },
      { subject: "Body", score: 45, fullMark: 100 },
    ],
    timelineData: [
      { session: "S1", Facial: 70, Tone: 65, Body: 45, Pace: 60 },
    ],
  },
  s2: {
    id: "s2",
    projectId: "1",
    name: "Session 2",
    score: 76,
    overallScore: 74,
    tone: 80,
    body: 50,
    face: 90,
    targetTone: 90,
    targetBody: 75,
    targetFace: 95,
    date: "2026-05-28",
    duration: "2min 45s",
    verdict: "You are not ready!",
    feedback: [
      { icon: "👁️", text: "Eye contact dropped", tip: "Practice chin-up then look" },
      { icon: "💬", text: "Filler words increased", tip: "Pause instead of saying 'um'" },
      { icon: "🤲", text: "Strong open stance", tip: "Keep maintaining this posture" },
    ],
    radarData: [
      { subject: "Facial", score: 85, fullMark: 100 },
      { subject: "Filler", score: 60, fullMark: 100 },
      { subject: "Tone", score: 80, fullMark: 100 },
      { subject: "Pace", score: 70, fullMark: 100 },
      { subject: "Vocal", score: 75, fullMark: 100 },
      { subject: "Body", score: 50, fullMark: 100 },
    ],
    timelineData: [
      { session: "S1", Facial: 70, Tone: 65, Body: 45, Pace: 60 },
      { session: "S2", Facial: 85, Tone: 80, Body: 50, Pace: 70 },
    ],
  },
};

export const projectSessions = {
  "1": ["s2", "s1"],
  "2": [],
};

export const initialProjects = [
  {
    id: "1",
    name: "TED Talk – Climate Change",
    description: "Preparing for the annual sustainability conference keynote to an audience of 2,000.",
    deadline: "2026-12-12",
    pinned: false,
  },
  {
    id: "2",
    name: "Job Interview Prep",
    description: "Mock interviews for senior product manager roles at top tech companies.",
    deadline: "2027-01-05",
    pinned: true,
  },
];

export function getSessionById(id) {
  return sessions[id] || null;
}

export function getSessionsForProject(projectId) {
  const ids = projectSessions[projectId] || [];
  return ids.map((id) => sessions[id]).filter(Boolean);
}

export function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function getDaysUntilDeadline(deadline) {
  const today = new Date();
  const deadlineDate = new Date(deadline);
  return Math.ceil((deadlineDate - today) / (1000 * 60 * 60 * 24));
}
