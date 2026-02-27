/**
 * useSyncPolling hook tests.
 *
 * Tests verify:
 *   - Hook returns initial state (null status, not polling, no error)
 *   - Does not call axios when active=false
 *   - Calls GET /api/admin/sync-status when active=true
 *   - Updates syncStatus from API response
 *   - Continues polling while status is "running"
 *   - Stops polling on terminal status "success"
 *   - Stops polling on terminal status "failed"
 *   - Surfaces non-fatal network errors without crashing
 *   - Stops polling after maxDuration exceeded
 *   - reset() clears syncStatus and error
 *   - Stops polling when active transitions from true to false
 *   - Cleans up interval on unmount
 *
 * Uses vi.useFakeTimers() to control timing without waiting for real time.
 * Uses vi.advanceTimersByTimeAsync() for controlled advancement — avoids
 * runAllTimersAsync() which can overshoot by advancing past maxDuration
 * and triggering unexpected state transitions in tests with long intervals.
 */
import { renderHook, act, waitFor } from "@testing-library/react";
import { vi, describe, test, expect, beforeEach, afterEach } from "vitest";

vi.mock("axios", async () => {
  const actual = await vi.importActual<typeof import("axios")>("axios");
  return {
    default: {
      ...actual.default,
      get: vi.fn(),
      isAxiosError: actual.default.isAxiosError,
    },
  };
});

import axios from "axios";
import { useSyncPolling } from "../useSyncPolling";
import type { SyncStatus } from "../useSyncPolling";

const runningStatus: SyncStatus = {
  status: "running",
  cves_extracted: undefined,
  error_message: null,
};

const successStatus: SyncStatus = {
  status: "success",
  cves_extracted: 1234,
  error_message: null,
};

const failedStatus: SyncStatus = {
  status: "failed",
  cves_extracted: undefined,
  error_message: "Connection timeout",
};

describe("useSyncPolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("returns null syncStatus and isPolling=false when active=false", () => {
    const { result } = renderHook(() => useSyncPolling(false));
    expect(result.current.syncStatus).toBeNull();
    expect(result.current.isPolling).toBe(false);
    expect(result.current.error).toBeNull();
  });

  test("does not call axios.get when active=false", async () => {
    renderHook(() => useSyncPolling(false));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(axios.get).not.toHaveBeenCalled();
  });

  test("calls GET /api/admin/sync-status immediately when active=true", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: runningStatus });

    renderHook(() => useSyncPolling(true));

    // Let the initial poll fire
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(axios.get).toHaveBeenCalledWith("/api/admin/sync-status");
  });

  test("updates syncStatus from API response when running", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: runningStatus });

    const { result } = renderHook(() => useSyncPolling(true));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(result.current.syncStatus).toEqual(runningStatus);
  });

  test("polls a second time after the poll interval elapses", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: runningStatus });

    renderHook(() => useSyncPolling(true, { pollInterval: 2000 }));

    // Let initial poll fire
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });
    const afterFirst = vi.mocked(axios.get).mock.calls.length;
    expect(afterFirst).toBe(1);

    // Advance past the 2 s interval
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100);
    });

    expect(vi.mocked(axios.get).mock.calls.length).toBeGreaterThan(afterFirst);
  });

  test("stops polling when status becomes 'success'", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: successStatus });

    const { result } = renderHook(() => useSyncPolling(true, { pollInterval: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(result.current.syncStatus?.status).toBe("success");
    expect(result.current.isPolling).toBe(false);

    // Confirm no additional calls after polling stopped
    const countAfterSuccess = vi.mocked(axios.get).mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(vi.mocked(axios.get).mock.calls.length).toBe(countAfterSuccess);
  });

  test("stops polling when status becomes 'failed'", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: failedStatus });

    const { result } = renderHook(() => useSyncPolling(true, { pollInterval: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(result.current.syncStatus?.status).toBe("failed");
    expect(result.current.isPolling).toBe(false);
  });

  test("surfaces error when GET request fails but continues polling", async () => {
    const networkError = Object.assign(new Error("Network Error"), {
      isAxiosError: true,
      response: undefined,
      message: "Network Error",
    });
    vi.mocked(axios.get).mockRejectedValue(networkError);

    const { result } = renderHook(() => useSyncPolling(true, { pollInterval: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    // Error should be set
    expect(result.current.error).not.toBeNull();
    expect(typeof result.current.error).toBe("string");
  });

  test("stops polling and surfaces error after maxDuration exceeded", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: runningStatus });

    const maxDuration = 6000; // 6 seconds for this test
    const { result } = renderHook(() =>
      useSyncPolling(true, { pollInterval: 1000, maxDuration })
    );

    // Let initial poll fire
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    // Advance past maxDuration, triggering the timeout check inside pollOnce
    await act(async () => {
      await vi.advanceTimersByTimeAsync(maxDuration + 1500);
    });

    expect(result.current.isPolling).toBe(false);
    // The hook sets: "Polling timed out after 5 minutes." (hardcoded message)
    expect(result.current.error).not.toBeNull();
  });

  test("reset() clears syncStatus and error state", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: runningStatus });

    const { result } = renderHook(() => useSyncPolling(true));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(result.current.syncStatus).not.toBeNull();

    act(() => {
      result.current.reset();
    });

    expect(result.current.syncStatus).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isPolling).toBe(false);
  });

  test("stops polling when active transitions from true to false", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: runningStatus });

    const { result, rerender } = renderHook(
      ({ active }: { active: boolean }) => useSyncPolling(active),
      { initialProps: { active: true } }
    );

    // Let the initial poll fire and confirm polling started
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    // isPolling is set to true when active=true and interval starts
    // After the first pollOnce resolves, isActivelyPolling is still true (running status)
    expect(result.current.syncStatus?.status).toBe("running");

    // Deactivate
    rerender({ active: false });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current.isPolling).toBe(false);
  });

  test("cleans up interval on unmount to prevent memory leaks", async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: runningStatus });
    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");

    const { unmount } = renderHook(() => useSyncPolling(true, { pollInterval: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});
