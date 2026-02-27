/**
 * SyncButton — navbar component for triggering manual CyPerf data sync.
 *
 * Calls POST /admin/sync-cyperf-now and displays status feedback:
 *   idle    → "Sync Data" (outline button)
 *   loading → spinning loader + "Syncing..." (polling active via useSyncPolling)
 *   success → green checkmark + "Synced" (resets after 3s)
 *   error   → red alert icon + error message (resets after 5s)
 *
 * Toast notifications fired for all state transitions via sonner.
 * Button is disabled when no endpoint is configured or during loading.
 * Displays last sync timestamp inline when provided (idle state only).
 *
 * Polling lifecycle:
 *   1. User clicks → POST /admin/sync-cyperf-now
 *   2. If response.status === "sync_queued": start useSyncPolling
 *   3. Polling hits terminal state (success/failed) → show toast, update UI
 *   4. If response.status === "sync_completed": immediate success (no polling needed)
 */
import { useState, useEffect, useRef } from "react";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { useSyncPolling } from "../../hooks/useSyncPolling";

type SyncButtonStatus = "idle" | "loading" | "success" | "error";

interface SyncButtonProps {
  endpoint?: string;
  lastSyncAt?: string | null;
  onSyncStart?: () => void;
  onSyncComplete?: (success: boolean) => void;
}

export function SyncButton({
  endpoint,
  lastSyncAt,
  onSyncStart,
  onSyncComplete,
}: SyncButtonProps) {
  const [status, setStatus] = useState<SyncButtonStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [pollActive, setPollActive] = useState(false);

  // Track the active loading toast ID so we can dismiss it on completion
  const loadingToastRef = useRef<string | number | undefined>(undefined);

  const {
    syncStatus,
    error: pollingError,
    reset: resetPolling,
  } = useSyncPolling(pollActive);

  // React to polling reaching a terminal state
  useEffect(() => {
    if (!syncStatus) return;

    if (syncStatus.status === "success") {
      // Dismiss the loading toast
      if (loadingToastRef.current !== undefined) {
        toast.dismiss(loadingToastRef.current);
        loadingToastRef.current = undefined;
      }
      const cveCount = syncStatus.cves_extracted;
      const successMsg =
        cveCount !== undefined && cveCount !== null
          ? `Sync completed — ${cveCount.toLocaleString()} CVEs extracted`
          : "Sync completed successfully";
      toast.success(successMsg);
      setStatus("success");
      setPollActive(false);
      onSyncComplete?.(true);
      setTimeout(() => {
        setStatus("idle");
        resetPolling();
      }, 3000);
    } else if (syncStatus.status === "failed") {
      if (loadingToastRef.current !== undefined) {
        toast.dismiss(loadingToastRef.current);
        loadingToastRef.current = undefined;
      }
      const errMsg = syncStatus.error_message ?? "Unknown error during sync";
      toast.error(`Sync failed: ${errMsg}`);
      setError(errMsg);
      setStatus("error");
      setPollActive(false);
      onSyncComplete?.(false);
      setTimeout(() => {
        setStatus("idle");
        setError(null);
        resetPolling();
      }, 5000);
    }
  }, [syncStatus, onSyncComplete, resetPolling]);

  // Surface polling errors as informational toasts (non-terminal)
  useEffect(() => {
    if (pollingError && pollActive) {
      toast.warning(`Status check failed: ${pollingError}`, {
        description: "Will retry...",
        duration: 3000,
      });
    }
  }, [pollingError, pollActive]);

  const handleSync = async () => {
    if (!endpoint) {
      toast.error("Endpoint not configured. Open settings to configure.");
      return;
    }

    setStatus("loading");
    setError(null);
    resetPolling();
    onSyncStart?.();

    const toastId = toast.loading("Starting CyPerf sync...");
    loadingToastRef.current = toastId;

    try {
      const res = await axios.post<{
        status: "sync_queued" | "sync_completed";
        message: string;
        job_id?: string;
      }>("/admin/sync-cyperf-now");

      const data = res.data;

      if (data.status === "sync_queued") {
        // Update loading toast message
        toast.loading("Sync queued — polling for completion...", { id: toastId });
        loadingToastRef.current = toastId;
        // Activate polling — useSyncPolling will take it from here
        setPollActive(true);
      } else if (data.status === "sync_completed") {
        // Immediate completion (no polling needed)
        toast.dismiss(toastId);
        loadingToastRef.current = undefined;
        toast.success(`Sync completed — ${data.message}`);
        setStatus("success");
        onSyncComplete?.(true);
        setTimeout(() => setStatus("idle"), 3000);
      }
    } catch (err) {
      toast.dismiss(toastId);
      loadingToastRef.current = undefined;

      let message = "Sync failed";
      if (axios.isAxiosError(err)) {
        message =
          err.response?.data?.detail ??
          err.response?.data?.message ??
          err.message ??
          "Sync failed";
      } else if (err instanceof Error) {
        message = err.message;
      }

      toast.error(`Sync failed: ${message}`);
      setError(message);
      setStatus("error");
      onSyncComplete?.(false);
      setTimeout(() => {
        setStatus("idle");
        setError(null);
      }, 5000);
    }
  };

  const isDisabled = status === "loading" || !endpoint;

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-3">
        {/* Last sync timestamp — only shown in idle state */}
        {lastSyncAt && status === "idle" && (
          <span className="text-xs text-luxury-text-secondary">
            Last:{" "}
            {new Date(lastSyncAt).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}

        {/* Sync button */}
        <button
          onClick={() => void handleSync()}
          disabled={isDisabled}
          aria-label={
            !endpoint
              ? "Sync Data (endpoint not configured)"
              : status === "loading"
                ? "Sync in progress"
                : "Trigger manual CyPerf data sync"
          }
          title={
            !endpoint
              ? "Configure CyPerf endpoint in settings before syncing"
              : "Trigger manual CyPerf data sync"
          }
          className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-semibold
            tracking-luxury uppercase transition-all duration-200 border
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-luxury-accent
            focus-visible:ring-offset-2 focus-visible:ring-offset-luxury-bg
            disabled:pointer-events-none disabled:opacity-50
            ${
              status === "success"
                ? "border-green-600 text-green-400 bg-green-900/20"
                : status === "error"
                  ? "border-red-700 text-red-400 bg-red-900/20"
                  : "border-luxury-border text-luxury-text hover:border-luxury-accent hover:text-luxury-accent"
            }`}
        >
          {status === "loading" && (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          )}
          {status === "success" && (
            <CheckCircle className="h-3.5 w-3.5 text-green-400" aria-hidden="true" />
          )}
          {status === "error" && (
            <AlertCircle className="h-3.5 w-3.5 text-red-400" aria-hidden="true" />
          )}

          {status === "loading"
            ? "Syncing..."
            : status === "success"
              ? "Synced"
              : status === "error"
                ? "Sync Failed"
                : "Sync Data"}
        </button>
      </div>

      {/* Inline error message (below button) */}
      {error && status === "error" && (
        <span
          className="text-xs text-red-400 max-w-[220px] text-right leading-tight"
          role="alert"
          aria-live="polite"
        >
          {error}
        </span>
      )}
    </div>
  );
}
