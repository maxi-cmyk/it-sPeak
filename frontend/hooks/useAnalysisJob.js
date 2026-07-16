"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { confirmSession, getSessionAnalysis, uploadSession } from "@/lib/api";

const INITIAL_STATE = { sessionId: null, accessToken: null, status: "idle", stage: null, error: null, result: null, qualityGate: null };

export default function useAnalysisJob() {
  const [job, setJob] = useState(INITIAL_STATE);
  const controllerRef = useRef(null);

  const start = useCallback(async ({ file, projectId, archetype, audienceContext }) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setJob({ ...INITIAL_STATE, status: "uploading", stage: "Uploading video securely" });
    try {
      const accepted = await uploadSession({ file, projectId, archetype, audienceContext, signal: controller.signal });
      const metadata = { accessToken: accepted.access_token, projectId, expiresAt: accepted.expires_at };
      sessionStorage.setItem(`itspeak:session:${accepted.session_id}`, JSON.stringify(metadata));
      setJob({ ...INITIAL_STATE, sessionId: accepted.session_id, accessToken: accepted.access_token, status: accepted.status, stage: "Checking recording quality" });
    } catch (error) {
      if (error.name !== "AbortError") setJob({ ...INITIAL_STATE, status: "failure", error: error.message });
    }
  }, []);

  useEffect(() => {
    if (!job.sessionId || !job.accessToken || ["success", "failure", "rejected", "needs_confirmation"].includes(job.status)) return;
    const controller = new AbortController();
    let active = true;
    let timeoutId;
    const poll = async () => {
      try {
        const payload = await getSessionAnalysis(job.sessionId, job.accessToken, controller.signal);
        if (!active) return;
        if (payload.status === "success" && payload.result) {
          const key = `itspeak:session:${job.sessionId}`;
          const metadata = JSON.parse(sessionStorage.getItem(key) || "{}");
          sessionStorage.setItem(key, JSON.stringify({ ...metadata, report: payload.result, qualityGate: payload.quality_gate }));
        }
        setJob((current) => ({ ...current, status: payload.status, stage: payload.stage, result: payload.result, qualityGate: payload.quality_gate, error: payload.error }));
        if (!["success", "failure", "rejected", "needs_confirmation"].includes(payload.status)) timeoutId = window.setTimeout(poll, 1500);
      } catch (error) {
        if (error.name !== "AbortError" && active) setJob((current) => ({ ...current, status: "failure", error: error.message }));
      }
    };
    poll();
    return () => { active = false; controller.abort(); window.clearTimeout(timeoutId); };
  }, [job.sessionId, job.accessToken, job.status]);

  const confirm = useCallback(async () => {
    setJob((current) => ({ ...current, status: "queued", stage: "Waiting for full analysis" }));
    try {
      const payload = await confirmSession(job.sessionId, job.accessToken);
      setJob((current) => ({ ...current, status: payload.status, stage: payload.stage }));
    } catch (error) {
      setJob((current) => ({ ...current, status: "failure", error: error.message }));
    }
  }, [job.sessionId, job.accessToken]);

  const reset = useCallback(() => { controllerRef.current?.abort(); setJob(INITIAL_STATE); }, []);
  return { ...job, start, confirm, reset };
}
