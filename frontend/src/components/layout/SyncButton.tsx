/**
 * SyncButton — navbar component for triggering manual CyPerf data sync.
 *
 * Calls POST /api/admin/sync-cyperf-now and displays status feedback:
 *   idle    → "Sync Data" (outline button)
 *   loading → spinning loader + "Syncing..."
 *   success → green checkmark + "Synced" (resets after 3s)
 *   error   → red alert icon + error message (resets after 5s)
 *
 * Button is disabled when no endpoint is configured or during loading.
 * Displays last sync timestamp inline when provided.
 */
import { useState } from "react";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import axios from "axios";

type SyncStatus = "idle" | "loading" | "success" | "error";

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
  const [status, setStatus] = useState<SyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    if (!endpoint) {
      setError("Endpoint not configured. Open settings to configure.");
      setStatus("error");
      setTimeout(() => {
        setStatus("idle");
        setError(null);
      }, 5000);
      return;
    }

    setStatus("loading");
    setError(null);
    onSyncStart?.();

    try {
      await axios.post("/api/admin/sync-cyperf-now");
      setStatus("success");
      onSyncComplete?.(true);
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err) {
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
        {/* Last sync timestamp */}
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
          onClick={handleSync}
          disabled={isDisabled}
          aria-label={
            !endpoint
              ? "Sync Data (endpoint not configured)"
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

      {/* Error message row */}
      {error && status === "error" && (
        <span className="text-xs text-red-400 max-w-[220px] text-right leading-tight">
          {error}
        </span>
      )}
    </div>
  );
}
