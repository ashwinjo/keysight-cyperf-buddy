interface TestableFilterProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export default function TestableFilter({ checked, onChange }: TestableFilterProps) {
  return (
    <label className="flex items-center gap-2 mb-4 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4 rounded bg-gray-800 border border-gray-700 cursor-pointer accent-blue-600"
      />
      <span className="text-gray-300 font-medium">Testable with Cyperf</span>
    </label>
  );
}
