const ICON_PROPS = { width: 15.4, height: 15.4, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" };

const PATHS = {
  pacing: (
    <>
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l3 2" />
      <path d="M9 2h6" />
    </>
  ),
  intonation: <path d="M2 12h3l2-7 3 14 3-11 2 4h5" />,
  filler_words: (
    <>
      <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.5 8.5 0 1 1 21 11.5Z" />
      <circle cx="8.5" cy="11.5" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="12" cy="11.5" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="11.5" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
  eye_contact: (
    <>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  facial_expression: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9 9.01V9" />
      <path d="M15 9.01V9" />
      <path d="M8 14s1.5 2 4 2 4-2 4-2" />
    </>
  ),
  posture: (
    <>
      <circle cx="12" cy="4.5" r="2.2" />
      <path d="M8.5 9h7l-1 5.5h-5Z" />
      <path d="M10 14.5v6" />
      <path d="M14 14.5v6" />
    </>
  ),
  gestures: (
    <>
      <path d="M8 13V6.5a1.5 1.5 0 0 1 3 0V12" />
      <path d="M11 12V4.5a1.5 1.5 0 0 1 3 0V12" />
      <path d="M14 12.5V6.5a1.5 1.5 0 0 1 3 0V13" />
      <path d="M17 10.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1.5c-2 0-3.3-.6-4.5-1.8l-2.8-2.8a1.5 1.5 0 0 1 2.1-2.1L9 16" />
    </>
  ),
};

PATHS.face = PATHS.facial_expression;
PATHS.body = PATHS.posture;
PATHS.audio = PATHS.intonation;

export default function ImprovementAreaIcon({ area }) {
  const path = PATHS[area];
  if (!path) return null;
  return <svg {...ICON_PROPS} aria-hidden="true">{path}</svg>;
}
