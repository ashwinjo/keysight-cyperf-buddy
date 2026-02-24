/**
 * Badge component for CVE testability status display.
 *
 * Refined luxury aesthetic with sophisticated styling and elegant typography.
 * Gold/bronze for testable, refined slate for non-testable.
 */
export interface BadgeProps {
  testable: boolean;
}

export default function Badge({ testable }: BadgeProps) {
  if (testable) {
    return (
      <span className="inline-block px-4 py-2 rounded-md bg-red-50 text-keysight-red
                       text-xs font-semibold tracking-luxury uppercase border border-red-200
                       transition-all duration-200 hover:border-keysight-red hover:bg-red-100">
        Testable
      </span>
    );
  }

  return (
    <span className="inline-block px-4 py-2 rounded-md bg-luxury-bg/5 text-luxury-text-secondary
                     text-xs font-semibold tracking-luxury uppercase border border-luxury-border
                     transition-all duration-200 hover:text-luxury-text">
      Not Testable
    </span>
  );
}
