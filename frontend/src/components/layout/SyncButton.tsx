/**
 * SyncButton — navbar component for triggering a full CyPerf data sync.
 *
 * Calls POST /admin/sync-all which:
 *   1. Syncs apps + app types synchronously (counts returned immediately)
 *   2. Queues CVE sync via APScheduler (polled via useSyncPolling)
 *
 * States:
 *   idle    → "Sync Data"
 *   loading → "Syncing..." (apps done inline; CVE polling active)
 *   success → green checkmark + "Synced" (resets after 3s)
 *   error   → red alert icon + error message (resets after 5s)
 *
 * Success toast: "Synced — 1,708 CVEs · 330 app types · 567 apps"
 */
import { useState, useEffect, useRef } from "react";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { useQueryClient } from "@tanstack/react-query";
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
  const queryClient = useQueryClient();

  // Track the active loading toast ID so we can dismiss it on completion
  const loadingToastRef = useRef<string | number | undefined>(undefined);
  // Apps sync counts from the initial POST response — combined into CVE success toast
  const appsSyncedRef = useRef<{ app_types_count: number; applications_count: number } | null>(null);

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
      const apps = appsSyncedRef.current;
      let successMsg = "Sync completed";
      const parts: string[] = [];
      if (cveCount !== undefined && cveCount !== null) {
        parts.push(`${cveCount.toLocaleString()} CVEs`);
      }
      if (apps) {
        parts.push(`${apps.app_types_count} app types`);
        parts.push(`${apps.applications_count} apps`);
      }
      if (parts.length > 0) {
        successMsg = `Sync completed — ${parts.join(" · ")}`;
      }
      toast.success(successMsg);
      // Refresh apps tables so they reflect the newly synced data
      void queryClient.invalidateQueries({ queryKey: ["cyperf", "applications"] });
      void queryClient.invalidateQueries({ queryKey: ["cyperf", "application-types"] });
      appsSyncedRef.current = null;
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
    appsSyncedRef.current = null;
    resetPolling();
    onSyncStart?.();

    const toastId = toast.loading("Syncing apps + CVEs from CyPerf…");
    loadingToastRef.current = toastId;

    try {
      const res = await axios.post<{
        status: "sync_queued" | "sync_completed";
        message: string;
        job_id?: string;
        apps_synced?: { app_types_count: number; applications_count: number };
      }>("/admin/sync-all");

      const data = res.data;

      // Store apps counts for use in the final success toast
      if (data.apps_synced) {
        appsSyncedRef.current = data.apps_synced;
      }

      if (data.status === "sync_queued") {
        const appMsg = data.apps_synced
          ? `Apps done (${data.apps_synced.app_types_count} types · ${data.apps_synced.applications_count} apps) — polling for CVEs…`
          : "Sync queued — polling for completion…";
        toast.loading(appMsg, { id: toastId });
        loadingToastRef.current = toastId;
        setPollActive(true);
      } else if (data.status === "sync_completed") {
        toast.dismiss(toastId);
        loadingToastRef.current = undefined;
        const apps = data.apps_synced;
        const parts = apps
          ? [`${apps.app_types_count} app types`, `${apps.applications_count} apps`]
          : [];
        toast.success(`Sync completed — ${[data.message, ...parts].join(" · ")}`);
        void queryClient.invalidateQueries({ queryKey: ["cyperf", "applications"] });
        void queryClient.invalidateQueries({ queryKey: ["cyperf", "application-types"] });
        appsSyncedRef.current = null;
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
