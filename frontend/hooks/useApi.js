"use client";

import { useAuth } from "@clerk/nextjs";
import { useMemo } from "react";
import { createApiClient } from "@/lib/api";

export default function useApi() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const client = useMemo(() => createApiClient(getToken), [getToken]);
  return { ...client, authReady: isLoaded && isSignedIn };
}
