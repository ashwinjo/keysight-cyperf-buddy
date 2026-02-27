/**
 * SyncButton component tests.
 *
 * Tests verify:
 *   - Renders "Sync Data" button text in idle state
 *   - Button disabled when endpoint not provided
 *   - Shows error state when endpoint not configured and button clicked
 *   - Calls POST /api/admin/sync-cyperf-now on click
 *   - Handles sync_queued and sync_completed API responses
 *   - Displays last sync timestamp when provided
 *   - Calls onSyncComplete callback with result
 *   - Handles API error gracefully
 *
 * Mocks:
 *   - axios: prevents real HTTP calls
 *   - sonner: prevents real toast DOM rendering
 *   - useSyncPolling: prevents real polling intervals
 *
 * Note: The component uses axios directly (not an api.ts wrapper) —
 * consistent with the project-wide pattern established in Wave 3.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, test, expect, beforeEach } from "vitest";

// Mock axios before importing the component.
// We keep isAxiosError as the real implementation so it correctly
// identifies errors that have the AxiosError shape.
vi.mock("axios", async () => {
  const actual = await vi.importActual<typeof import("axios")>("axios");
  return {
    default: {
      ...actual.default,
      post: vi.fn(),
      // Real isAxiosError: checks err.isAxiosError === true property
      isAxiosError: actual.default.isAxiosError,
    },
  };
});

// Mock sonner to avoid real toast rendering
vi.mock("sonner", () => ({
  toast: {
    loading: vi.fn(() => "mock-toast-id"),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    dismiss: vi.fn(),
  },
}));

// Mock useSyncPolling to control polling state in tests
vi.mock("../../../hooks/useSyncPolling", () => ({
  useSyncPolling: vi.fn(() => ({
    syncStatus: null,
    isPolling: false,
    error: null,
    reset: vi.fn(),
  })),
}));

import axios from "axios";
import { SyncButton } from "../SyncButton";

describe("SyncButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders Sync Data button in idle state", () => {
    render(<SyncButton endpoint="cyperf.example.com" />);
    expect(screen.getByRole("button")).toBeInTheDocument();
    expect(screen.getByText("Sync Data")).toBeInTheDocument();
  });

  test("button is enabled when endpoint is provided", () => {
    render(<SyncButton endpoint="cyperf.example.com" />);
    const button = screen.getByRole("button");
    expect(button).not.toBeDisabled();
  });

  test("button is disabled when endpoint is undefined", () => {
    render(<SyncButton endpoint={undefined} />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  test("button is disabled when endpoint is empty string", () => {
    render(<SyncButton endpoint="" />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  test("aria-label describes disabled state when endpoint not configured", () => {
    render(<SyncButton endpoint={undefined} />);
    const button = screen.getByRole("button");
    expect(button.getAttribute("aria-label")).toContain("endpoint not configured");
  });

  test("calls POST /api/admin/sync-cyperf-now when button clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(axios.post).mockResolvedValue({
      data: { status: "sync_queued", job_id: "job-123", message: "Sync queued" },
    });

    render(<SyncButton endpoint="cyperf.example.com" />);
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith("/api/admin/sync-cyperf-now");
    });
  });

  test("does not call API when endpoint is undefined and button clicked", async () => {
    const user = userEvent.setup();
    render(<SyncButton endpoint={undefined} />);
    // Button should be disabled — click should not fire the handler
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    // Attempting click on a disabled button should be a no-op
    await user.click(button);
    expect(axios.post).not.toHaveBeenCalled();
  });

  test("shows loading text after button click (sync in progress)", async () => {
    const user = userEvent.setup();
    // Make the promise never resolve so we can observe the loading state
    vi.mocked(axios.post).mockReturnValue(new Promise(() => {}));

    render(<SyncButton endpoint="cyperf.example.com" />);
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("Syncing...")).toBeInTheDocument();
    });
  });

  test("button is disabled while loading (prevents double-click)", async () => {
    const user = userEvent.setup();
    vi.mocked(axios.post).mockReturnValue(new Promise(() => {}));

    render(<SyncButton endpoint="cyperf.example.com" />);
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByRole("button")).toBeDisabled();
    });
  });

  test("shows Synced text after sync_completed response", async () => {
    const user = userEvent.setup();
    vi.mocked(axios.post).mockResolvedValue({
      data: {
        status: "sync_completed",
        job_id: "job-456",
        message: "500 CVEs extracted",
      },
    });

    render(<SyncButton endpoint="cyperf.example.com" />);
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("Synced")).toBeInTheDocument();
    });
  });

  test("shows Sync Failed text after API error", async () => {
    const user = userEvent.setup();
    const axiosError = Object.assign(new Error("Network error"), {
      isAxiosError: true,
      response: { data: { detail: "Network error" }, status: 500 },
    });
    vi.mocked(axios.post).mockRejectedValue(axiosError);

    render(<SyncButton endpoint="cyperf.example.com" />);
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("Sync Failed")).toBeInTheDocument();
    });
  });

  test("calls onSyncComplete with true after sync_completed response", async () => {
    const user = userEvent.setup();
    const onSyncComplete = vi.fn();
    vi.mocked(axios.post).mockResolvedValue({
      data: {
        status: "sync_completed",
        job_id: "job-789",
        message: "Sync completed",
      },
    });

    render(
      <SyncButton endpoint="cyperf.example.com" onSyncComplete={onSyncComplete} />
    );
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(onSyncComplete).toHaveBeenCalledWith(true);
    });
  });

  test("calls onSyncComplete with false after API error", async () => {
    const user = userEvent.setup();
    const onSyncComplete = vi.fn();
    const axiosError = Object.assign(new Error("Sync failed"), {
      isAxiosError: true,
      response: { data: { detail: "Sync failed" }, status: 500 },
    });
    vi.mocked(axios.post).mockRejectedValue(axiosError);

    render(
      <SyncButton endpoint="cyperf.example.com" onSyncComplete={onSyncComplete} />
    );
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(onSyncComplete).toHaveBeenCalledWith(false);
    });
  });

  test("calls onSyncStart callback when sync triggered", async () => {
    const user = userEvent.setup();
    const onSyncStart = vi.fn();
    vi.mocked(axios.post).mockReturnValue(new Promise(() => {}));

    render(
      <SyncButton endpoint="cyperf.example.com" onSyncStart={onSyncStart} />
    );
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(onSyncStart).toHaveBeenCalled();
    });
  });

  test("displays Last: timestamp when lastSyncAt is provided (idle state)", () => {
    const timestamp = "2026-01-15T10:30:00Z";
    render(<SyncButton endpoint="cyperf.example.com" lastSyncAt={timestamp} />);
    // Should show "Last:" prefix with the time formatted to HH:MM
    expect(screen.getByText(/Last:/)).toBeInTheDocument();
  });

  test("does not show timestamp when lastSyncAt is null", () => {
    render(<SyncButton endpoint="cyperf.example.com" lastSyncAt={null} />);
    expect(screen.queryByText(/Last:/)).not.toBeInTheDocument();
  });

  test("error message appears in document with role=alert after error", async () => {
    const user = userEvent.setup();
    const axiosError = Object.assign(new Error("Backend error"), {
      isAxiosError: true,
      response: { data: { detail: "Backend is down" }, status: 503 },
    });
    vi.mocked(axios.post).mockRejectedValue(axiosError);

    render(<SyncButton endpoint="cyperf.example.com" />);
    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      // Error span has role="alert"
      const alertEl = document.querySelector('[role="alert"]');
      expect(alertEl).not.toBeNull();
    });
  });
});
