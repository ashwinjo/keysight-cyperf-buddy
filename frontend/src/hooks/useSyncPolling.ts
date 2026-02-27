/**
 * useSyncPolling — polls GET /admin/sync-status at a configurable interval.
 *
 * Designed to be activated after a manual sync is triggered from SyncButton.
 * Starts polling immediately when `isPolling` transitions to true.
 * Stops automatically when:
 *   - status changes from "running" (terminal state reached)
 *   - elapsed time exceeds maxDuration (5-minute safety timeout)
 *   - isPolling is set back to false by the caller
 *
 * Uses axios directly to match the project's existing pattern (no api.ts wrapper).
 * Interval is cleared on unmount / isPolling=false to avoid memory leaks.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";

export interface SyncStatus {
  status: "success" | "failed" | "running" | "never";
  last_successful_sync?: string | null;
  last_attempted_sync?: string | null;
  profiles_synced?: number;
  cves_extracted?: number;
  error_message?: string | null;
  next_scheduled_sync?: string | null;
}

interface UseSyncPollingOptions {
  /** Milliseconds between polls. Default: 2000 */
  pollInterval?: number;
  /** Maximum polling duration before giving up. Default: 300000 (5 min) */
  maxDuration?: number;
}

interface UseSyncPollingResult {
  syncStatus: SyncStatus | null;
  /** True while actively polling (isPolling=true AND polling hasn't stopped) */
  isPolling: boolean;
  error: string | null;
  /** Reset state (e.g. when starting a fresh sync) */
  reset: () => void;
}

export function useSyncPolling(
  active: boolean,
  options: UseSyncPollingOptions = {}
): UseSyncPollingResult {
  const { pollInterval = 2000, maxDuration = 300_000 } = options;

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [isActivelyPolling, setIsActivelyPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startTimeRef = useRef<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    startTimeRef.current = null;
    setIsActivelyPolling(false);
  }, []);

  const reset = useCallback(() => {
    clearPolling();
    setSyncStatus(null);
    setError(null);
  }, [clearPolling]);

  const pollOnce = useCallback(async () => {
    // Guard: stop if we've exceeded the max duration
    if (startTimeRef.current !== null) {
      const elapsed = Date.now() - startTimeRef.current;
      if (elapsed > maxDuration) {
        clearPolling();
        setError("Polling timed out after 5 minutes.");
        return;
      }
    }

    try {
      const res = await axios.get<SyncStatus>("/admin/sync-status");
      const data = res.data;
      setSyncStatus(data);
      setError(null);

      // Terminal states — stop polling
      if (data.status === "success" || data.status === "failed") {
        clearPolling();
      }
    } catch (err) {
      let message = "Failed to fetch sync status";
      if (axios.isAxiosError(err)) {
        message =
          err.response?.data?.detail ??
          err.response?.data?.message ??
          err.message ??
          message;
      } else if (err instanceof Error) {
        message = err.message;
      }
      // Error is non-fatal — surface it but keep polling
      setError(message);
    }
  }, [maxDuration, clearPolling]);

  useEffect(() => {
    if (!active) {
      // Caller deactivated polling — clean up but preserve last status
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      startTimeRef.current = null;
      setIsActivelyPolling(false);
      return;
    }

    // Start fresh polling session
    startTimeRef.current = Date.now();
    setIsActivelyPolling(true);

    // Fire immediately, then on interval
    void pollOnce();

    intervalRef.current = setInterval(() => {
      void pollOnce();
    }, pollInterval);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [active, pollInterval, pollOnce]);

  return {
    syncStatus,
    isPolling: isActivelyPolling,
    error,
    reset,
  };
}
