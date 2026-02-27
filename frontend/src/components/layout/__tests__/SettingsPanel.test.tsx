/**
 * SettingsPanel component tests.
 *
 * Tests verify:
 *   - Renders modal content when isOpen=true
 *   - Does not render dialog when isOpen=false
 *   - Pre-fills input with currentEndpoint
 *   - Save & Validate button disabled when input is empty
 *   - Calls POST /api/admin/config/cyperf-endpoint on save
 *   - Handles 400 validation failure error
 *   - Handles network error
 *   - Calls onEndpointSaved callback on success
 *   - Calls onOpenChange(false) to close modal on success
 *   - Enter key triggers save
 *
 * Mocks:
 *   - axios: prevents real HTTP calls
 *   - sonner: prevents real toast DOM rendering
 *
 * Note: SettingsPanel uses Radix Dialog which requires the component to be
 * rendered inside a standard DOM environment (jsdom).
 * The dialog renders in a Radix Portal, so we use getAllByRole / queryAllByRole
 * for queries that span the portal boundary.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, test, expect, beforeEach } from "vitest";

// Mock axios before importing the component.
// isAxiosError is kept as the real implementation — it checks the
// error.isAxiosError === true property which we set on test errors.
vi.mock("axios", async () => {
  const actual = await vi.importActual<typeof import("axios")>("axios");
  return {
    default: {
      ...actual.default,
      post: vi.fn(),
      isAxiosError: actual.default.isAxiosError,
    },
  };
});

// Mock sonner to avoid real toast rendering in jsdom
vi.mock("sonner", () => ({
  toast: {
    loading: vi.fn(() => "mock-toast-id"),
    success: vi.fn(),
    error: vi.fn(),
    dismiss: vi.fn(),
  },
}));

import axios from "axios";
import { SettingsPanel } from "../SettingsPanel";

describe("SettingsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders modal title when isOpen is true", () => {
    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );
    expect(
      screen.getByText("CyPerf Controller Settings")
    ).toBeInTheDocument();
  });

  test("renders Controller Endpoint label when open", () => {
    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );
    expect(screen.getByText("Controller Endpoint")).toBeInTheDocument();
  });

  test("renders endpoint input with placeholder when open", () => {
    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );
    const input = screen.getByPlaceholderText(/e\.g\.,/);
    expect(input).toBeInTheDocument();
  });

  test("does not render dialog content when isOpen is false", () => {
    render(
      <SettingsPanel isOpen={false} onOpenChange={vi.fn()} />
    );
    // Title should not be in the document when dialog is closed
    expect(
      screen.queryByText("CyPerf Controller Settings")
    ).not.toBeInTheDocument();
  });

  test("pre-fills endpoint input with currentEndpoint", () => {
    render(
      <SettingsPanel
        isOpen={true}
        onOpenChange={vi.fn()}
        currentEndpoint="cyperf.example.com"
      />
    );
    const input = screen.getByDisplayValue("cyperf.example.com") as HTMLInputElement;
    expect(input.value).toBe("cyperf.example.com");
  });

  test("Save & Validate button is disabled when input is empty", () => {
    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );
    const saveButton = screen.getByText("Save & Validate");
    expect(saveButton.closest("button")).toBeDisabled();
  });

  test("Save & Validate button is enabled after typing in the input", async () => {
    const user = userEvent.setup();
    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "new.example.com");

    const saveButton = screen.getByText("Save & Validate");
    expect(saveButton.closest("button")).not.toBeDisabled();
  });

  test("calls POST /api/admin/config/cyperf-endpoint with typed endpoint on save", async () => {
    const user = userEvent.setup();
    vi.mocked(axios.post).mockResolvedValue({
      data: { endpoint: "new.example.com", is_valid: true },
    });

    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "new.example.com");

    const saveButton = screen.getByText("Save & Validate");
    await user.click(saveButton);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        "/api/admin/config/cyperf-endpoint",
        { endpoint: "new.example.com" }
      );
    });
  });

  test("shows Validating... during save operation", async () => {
    const user = userEvent.setup();
    vi.mocked(axios.post).mockReturnValue(new Promise(() => {}));

    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "slow.example.com");

    const saveButton = screen.getByText("Save & Validate");
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText("Validating...")).toBeInTheDocument();
    });
  });

  test("shows validation error banner on axios error", async () => {
    const user = userEvent.setup();
    const axiosError = Object.assign(new Error("Endpoint unreachable"), {
      isAxiosError: true,
      response: {
        status: 400,
        data: { detail: "Endpoint unreachable (connection timeout after 5 seconds)" },
      },
    });
    vi.mocked(axios.post).mockRejectedValue(axiosError);

    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "unreachable.example.com");

    const saveButton = screen.getByText("Save & Validate");
    await user.click(saveButton);

    await waitFor(() => {
      // Error banner has role="alert"
      const alertEl = document.querySelector('[role="alert"]');
      expect(alertEl).not.toBeNull();
    });
  });

  test("displays backend error detail from 400 response in error banner", async () => {
    const user = userEvent.setup();
    const axiosError = Object.assign(new Error("Bad request"), {
      isAxiosError: true,
      response: {
        status: 400,
        data: { detail: "Endpoint unreachable (connection timeout after 5 seconds)" },
      },
    });
    vi.mocked(axios.post).mockRejectedValue(axiosError);

    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "unreachable.example.com");

    await user.click(screen.getByText("Save & Validate"));

    await waitFor(() => {
      expect(
        screen.getByText("Endpoint unreachable (connection timeout after 5 seconds)")
      ).toBeInTheDocument();
    });
  });

  test("calls onEndpointSaved callback with saved endpoint on success", async () => {
    const user = userEvent.setup();
    const onEndpointSaved = vi.fn();
    vi.mocked(axios.post).mockResolvedValue({
      data: { endpoint: "saved.example.com", is_valid: true },
    });

    render(
      <SettingsPanel
        isOpen={true}
        onOpenChange={vi.fn()}
        onEndpointSaved={onEndpointSaved}
      />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "saved.example.com");

    await user.click(screen.getByText("Save & Validate"));

    await waitFor(() => {
      expect(onEndpointSaved).toHaveBeenCalledWith("saved.example.com");
    });
  });

  test("calls onOpenChange(false) after successful save (modal closes)", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    vi.mocked(axios.post).mockResolvedValue({
      data: { endpoint: "close-test.example.com", is_valid: true },
    });

    render(
      <SettingsPanel isOpen={true} onOpenChange={onOpenChange} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "close-test.example.com");

    await user.click(screen.getByText("Save & Validate"));

    await waitFor(
      () => {
        expect(onOpenChange).toHaveBeenCalledWith(false);
      },
      { timeout: 2000 }
    );
  });

  test("Cancel button calls onOpenChange(false)", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();

    render(
      <SettingsPanel isOpen={true} onOpenChange={onOpenChange} />
    );

    const cancelButton = screen.getByText("Cancel");
    await user.click(cancelButton);

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  test("Enter key in input triggers save", async () => {
    const user = userEvent.setup();
    vi.mocked(axios.post).mockResolvedValue({
      data: { endpoint: "enter-key.example.com", is_valid: true },
    });

    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "enter-key.example.com");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        "/api/admin/config/cyperf-endpoint",
        { endpoint: "enter-key.example.com" }
      );
    });
  });

  test("input strips leading/trailing whitespace on save", async () => {
    const user = userEvent.setup();
    vi.mocked(axios.post).mockResolvedValue({
      data: { endpoint: "trim.example.com", is_valid: true },
    });

    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    // Type with spaces around the hostname
    await user.type(input, "  trim.example.com  ");

    await user.click(screen.getByText("Save & Validate"));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        "/api/admin/config/cyperf-endpoint",
        { endpoint: "trim.example.com" }
      );
    });
  });

  test("input has aria-describedby pointing to error banner when error shown", async () => {
    const user = userEvent.setup();
    const axiosError = Object.assign(new Error("Fail"), {
      isAxiosError: true,
      response: {
        status: 400,
        data: { detail: "Endpoint unreachable (connection timeout)" },
      },
    });
    vi.mocked(axios.post).mockRejectedValue(axiosError);

    render(
      <SettingsPanel isOpen={true} onOpenChange={vi.fn()} />
    );

    const input = screen.getByPlaceholderText(/e\.g\.,/);
    await user.type(input, "bad.example.com");
    await user.click(screen.getByText("Save & Validate"));

    await waitFor(() => {
      expect(input.getAttribute("aria-describedby")).toBe("endpoint-error");
    });
  });
});
