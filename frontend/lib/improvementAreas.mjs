export const improvementAreaGroups = [
  {
    key: "audio",
    label: "Audio delivery",
    detail: "How your voice carries the message",
    options: [
      { value: "pacing", label: "Pacing", detail: "Speaking rate and rhythm", icon: "◷" },
      { value: "intonation", label: "Vocab variety", detail: "Pitch range and emphasis", icon: "⌁" },
      { value: "filler_words", label: "Filler words", detail: "Clean, intentional phrasing", icon: "···" },
    ],
  },
  {
    key: "visual",
    label: "Visual delivery",
    detail: "How you appear and move on camera",
    options: [
      { value: "eye_contact", label: "Eye contact", detail: "Audience and camera connection", icon: "◉" },
      { value: "facial_expression", label: "Expression", detail: "Visible emphasis and variation", icon: "⌒" },
      { value: "posture", label: "Posture", detail: "Upright, grounded alignment", icon: "↥" },
      { value: "gestures", label: "Gestures", detail: "Purposeful range and openness", icon: "↗" },
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
