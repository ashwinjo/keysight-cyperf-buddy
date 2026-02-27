/**
 * ErrorBoundary — React class component that catches render errors in its subtree.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <ComponentThatMightCrash />
 *   </ErrorBoundary>
 *
 *   // With custom fallback:
 *   <ErrorBoundary fallback={<div />}>
 *     <NavbarControls />
 *   </ErrorBoundary>
 *
 * Default fallback: a non-intrusive error strip that matches the luxury dark theme.
 * componentDidCatch logs to console.error so errors surface in dev tools and error
 * monitoring services (Sentry, Datadog, etc.) without crashing the whole app.
 *
 * Note: This must be a class component — React's error boundary lifecycle
 * (getDerivedStateFromError / componentDidCatch) is not available in function components.
 */
import React, { Component, ReactNode } from "react";
import { AlertCircle } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom UI to render instead of the default error strip. Pass <div /> to render nothing. */
  fallback?: ReactNode;
  /** Optional label for the error log message (helps identify which boundary caught the error) */
  label?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    const label = this.props.label ?? "ErrorBoundary";
    console.error(`[${label}] Uncaught render error:`, error);
    console.error(`[${label}] Component stack:`, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Caller-supplied fallback takes priority (e.g. <div /> for invisible failure)
      if (this.props.fallback !== undefined) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          aria-label="Error loading sync controls"
          className="flex items-center gap-2 px-3 py-1.5 bg-red-900/20 border border-red-700/60
            rounded-md text-xs text-red-400"
        >
          <AlertCircle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
          <span>Error loading sync controls</span>
        </div>
      );
    }

    return this.props.children;
  }
}
