export const improvementAreaGroups = [
  {
    key: "audio",
    label: "Audio delivery",
    detail: "How your voice carries the message",
    options: [
      { value: "pacing", label: "Pacing", detail: "Speaking rate and rhythm" },
      { value: "intonation", label: "Vocab variety", detail: "Pitch range and emphasis" },
      { value: "filler_words", label: "Filler words", detail: "Clean, intentional phrasing" },
    ],
  },
  {
    key: "visual",
    label: "Visual delivery",
    detail: "How you appear and move on camera",
    options: [
      { value: "eye_contact", label: "Eye contact", detail: "Audience and camera connection" },
      { value: "facial_expression", label: "Facial expressions", detail: "Visible emphasis and variation" },
      { value: "posture", label: "Posture", detail: "Upright, grounded alignment" },
      { value: "gestures", label: "Gestures", detail: "Purposeful range and openness" },
    ],
  },
];

export const improvementAreas = improvementAreaGroups.flatMap((group) => group.options);
export const improvementAreaValues = improvementAreas.map((option) => option.value);
export const improvementAreaLabels = Object.fromEntries(improvementAreas.map((option) => [option.value, option.label]));
export const improvementAreaGroupByValue = Object.fromEntries(
  improvementAreaGroups.flatMap((group) => group.options.map((option) => [option.value, group.key])),
);
export const improvementAreaModuleByValue = {
  pacing: "audio",
  intonation: "audio",
  filler_words: "audio",
  eye_contact: "face",
  facial_expression: "face",
  posture: "body",
  gestures: "body",
};
