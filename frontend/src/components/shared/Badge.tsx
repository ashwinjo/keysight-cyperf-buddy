export interface BadgeProps {
  testable: boolean;
}

export default function Badge({ testable }: BadgeProps) {
  if (testable) {
    return (
      <span className="inline-block px-3 py-1 rounded-full bg-green-900 text-green-200 text-xs font-semibold">
        Can test
      </span>
    );
  }

  return (
    <span className="inline-block px-3 py-1 rounded-full bg-gray-700 text-gray-300 text-xs font-semibold">
      Not testable
    </span>
  );
}
