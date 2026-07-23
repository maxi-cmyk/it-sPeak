export default function ImprovementAreaIcon({ area, size = 20, className = "" }) {
  const paths = {
    pacing: <><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3.5 2" /></>,
    intonation: <path d="M3 15c2.25 0 2.25-6 4.5-6s2.25 6 4.5 6 2.25-10 4.5-10S18.75 15 21 15" />,
    filler_words: <><path d="M5.5 18.5 3 21v-5a8.5 8.5 0 1 1 3.2 3.2" /><path d="M8 12h.01M12 12h.01M16 12h.01" strokeWidth="2.5" /></>,
    eye_contact: <><path d="M2.5 12s3.5-5.5 9.5-5.5 9.5 5.5 9.5 5.5-3.5 5.5-9.5 5.5S2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="2.5" /></>,
    facial_expression: <><circle cx="12" cy="12" r="9" /><path d="M8.5 9h.01M15.5 9h.01" strokeWidth="2.5" /><path d="M8 14c1 1.5 2.3 2.25 4 2.25s3-.75 4-2.25" /></>,
    posture: <><circle cx="12" cy="5" r="2" /><path d="M12 8v8M6.5 12.5 12 10l5.5 2.5M8.5 21 12 16l3.5 5" /></>,
    gestures: <><path d="M7.5 12V8.5a1.25 1.25 0 0 1 2.5 0V11 6.5a1.25 1.25 0 0 1 2.5 0V11 6a1.25 1.25 0 0 1 2.5 0v5-2a1.25 1.25 0 0 1 2.5 0v6.5A5.5 5.5 0 0 1 12 21h-.5a5 5 0 0 1-3.6-1.5l-3.2-3.3a1.5 1.5 0 0 1 2.1-2.1l1.7 1.7" /></>,
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {paths[area]}
    </svg>
  );
}
