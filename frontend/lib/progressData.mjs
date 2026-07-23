export const CURRENT_AUDIO_SCORING_VERSION = "yin-semitone-v2";

export function buildProgressData(sessions) {
  const chronological = [...sessions].reverse();
  const hasCurrentTone = chronological.some(
    (session) => session.audioScoringVersion === CURRENT_AUDIO_SCORING_VERSION,
  );
  const hasLegacyTone = chronological.some(
    (session) => session.audioScoringVersion !== CURRENT_AUDIO_SCORING_VERSION,
  );
  const mixedAudioVersions = hasCurrentTone && hasLegacyTone;

  return chronological.map((session) => ({
    session: session.name,
    "Facial expressions": session.face,
    Tone: mixedAudioVersions && session.audioScoringVersion !== CURRENT_AUDIO_SCORING_VERSION
      ? undefined
      : session.tone,
    Body: session.body,
  }));
}
