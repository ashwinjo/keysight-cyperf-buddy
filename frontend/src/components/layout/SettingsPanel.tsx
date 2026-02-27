/**
 * SettingsPanel — modal dialog for configuring the CyPerf Controller endpoint.
 *
 * Uses Radix UI Dialog (via local ui/dialog.tsx).
 * Calls POST /api/admin/config/cyperf-endpoint to validate + persist the endpoint.
 *
 * Backend behaviour to handle:
 *   - HTTP 200  → endpoint saved, is_valid=true
 *   - HTTP 400  → validation failed; detail field contains the reason
 *   - HTTP 500  → DB write failed after validation passed
 *
 * On success the modal auto-closes after 1 second and invokes onEndpointSaved.
 * On failure the error is shown in-line and the modal stays open.
 */
import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import axios from "axios";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

interface SettingsPanelProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  currentEndpoint?: string;
  onEndpointSaved?: (endpoint: string) => void;
}

export function SettingsPanel({
  isOpen,
  onOpenChange,
  currentEndpoint,
  onEndpointSaved,
}: SettingsPanelProps) {
  const [endpoint, setEndpoint] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [validationSuccess, setValidationSuccess] = useState(false);

  // Pre-fill when modal opens or currentEndpoint changes
  useEffect(() => {
    if (isOpen) {
      setEndpoint(currentEndpoint ?? "");
      setValidationError(null);
      setValidationSuccess(false);
    }
  }, [isOpen, currentEndpoint]);

  const handleSave = async () => {
    const trimmed = endpoint.trim();

    if (!trimmed) {
      setValidationError("Endpoint cannot be empty.");
      return;
    }

    setIsSaving(true);
    setValidationError(null);
    setValidationSuccess(false);

    try {
      await axios.post("/api/admin/config/cyperf-endpoint", {
        endpoint: trimmed,
      });

      // HTTP 200 means validated and saved
      setValidationSuccess(true);
      onEndpointSaved?.(trimmed);

      // Auto-close after 1 second so user sees the success message
      setTimeout(() => onOpenChange(false), 1000);
    } catch (err) {
      let message = "Failed to save endpoint. Please try again.";

      if (axios.isAxiosError(err)) {
        // Extract backend detail string from 400 / 500 responses
        const detail = err.response?.data?.detail;
        if (typeof detail === "string" && detail.length > 0) {
          message = detail;
        } else if (err.response?.status === 500) {
          message =
            "Endpoint validated but database write failed. Please retry.";
        } else if (err.response?.status === 400) {
          message = "Endpoint validation failed. Check the address and try again.";
        }
      } else if (err instanceof Error) {
        message = err.message;
      }

      setValidationError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !isSaving && endpoint.trim()) {
      void handleSave();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>CyPerf Controller Settings</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Endpoint input field */}
          <div>
            <label
              htmlFor="cyperf-endpoint-input"
              className="text-sm font-medium text-luxury-text"
            >
              Controller Endpoint
            </label>
            <p className="text-xs text-luxury-text-secondary mt-1">
              DNS name or IP address of your Keysight CyPerf Controller.
              The backend will test connectivity before saving.
            </p>
            <Input
              id="cyperf-endpoint-input"
              type="text"
              placeholder="e.g., cyperf.example.com or 192.168.1.100"
              value={endpoint}
              onChange={(e) => {
                setEndpoint(e.target.value);
                // Clear feedback on each keystroke so user gets fresh result
                setValidationError(null);
                setValidationSuccess(false);
              }}
              onKeyDown={handleKeyDown}
              disabled={isSaving}
              autoComplete="off"
              className="mt-2"
              aria-describedby={
                validationError
                  ? "endpoint-error"
                  : validationSuccess
                    ? "endpoint-success"
                    : undefined
              }
            />
          </div>

          {/* Validation error banner */}
          {validationError && (
            <div
              id="endpoint-error"
              role="alert"
              className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-700 rounded-md"
            >
              <AlertCircle
                className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5"
                aria-hidden="true"
              />
              <p className="text-sm text-red-400">{validationError}</p>
            </div>
          )}

          {/* Validation success banner */}
          {validationSuccess && (
            <div
              id="endpoint-success"
              role="status"
              className="flex items-start gap-2 p-3 bg-green-900/20 border border-green-700 rounded-md"
            >
              <CheckCircle
                className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5"
                aria-hidden="true"
              />
              <p className="text-sm text-green-400">
                Endpoint validated and saved successfully.
              </p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              onClick={handleCancel}
              variant="outline"
              size="sm"
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              onClick={() => void handleSave()}
              size="sm"
              disabled={isSaving || !endpoint.trim()}
              className="gap-2"
            >
              {isSaving && (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              )}
              {isSaving ? "Validating..." : "Save & Validate"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
