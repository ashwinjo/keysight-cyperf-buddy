/**
 * Badge component for CVE testability status display.
 *
 * Renders a pill-shaped badge indicating whether Cyperf can test a given CVE.
 * Green for testable, gray for non-testable — matches Phase 4 design contract.
 */
export interface BadgeProps {
  testable: boolean;
}

export default function Badge({ testable }: BadgeProps) {
  if (testable) {
    return (
      <span className="inline-block px-3 py-1 rounded-full bg-green-900 text-green-200 text-xs font-semibold">
        Can Cyperf Test?
      </span>
    );
  }

  return (
    <span className="inline-block px-3 py-1 rounded-full bg-gray-700 text-gray-300 text-xs font-semibold">
      Cannot Test
    </span>
  );
}
