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
      <span className="inline-block px-4 py-2 rounded-md bg-green-900/30 text-green-400
                       text-xs font-semibold tracking-luxury uppercase border border-green-700/50
                       transition-all duration-200 hover:border-green-600 hover:bg-green-900/50">
        Testable
      </span>
    );
  }

  return (
    <span className="inline-block px-4 py-2 rounded-md bg-gray-900/30 text-gray-400
                     text-xs font-semibold tracking-luxury uppercase border border-gray-700/50
                     transition-all duration-200 hover:border-gray-600 hover:bg-gray-900/50">
      Not Testable
    </span>
  );
}
