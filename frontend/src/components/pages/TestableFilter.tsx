interface TestableFilterProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export default function TestableFilter({ checked, onChange }: TestableFilterProps) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-5 h-5 rounded bg-luxury-bg-subtle border border-luxury-border cursor-pointer accent-luxury-accent transition-all hover:border-luxury-accent"
      />
      <span className="text-luxury-text font-semibold text-sm tracking-tight group-hover:text-luxury-accent transition-colors">
        Testable with Cyperf
      </span>
    </label>
  );
}
