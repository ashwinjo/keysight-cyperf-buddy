import React from 'react';
import { cn } from '../../lib/utils';

export interface SearchBoxProps {
  label: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  isLoading?: boolean;
  submitLabel?: string;
  stats?: React.ReactNode;
  error?: string;
  className?: string;
}

export function SearchBox({
  label,
  placeholder,
  value,
  onChange,
  onSubmit,
  isLoading = false,
  submitLabel = 'Search',
  stats,
  error,
  className,
}: SearchBoxProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (onSubmit && e.key === 'Enter') {
      onSubmit();
    }
  };

  return (
    <div className={cn('card-luxury', className)}>
      <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold mb-3">
        {label}
      </p>
      <div className="flex gap-3 items-center">
        <input
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onSubmit ? handleKeyDown : undefined}
          disabled={isLoading}
          className="input-luxury flex-1"
        />
        {onSubmit && (
          <button
            type="button"
            onClick={onSubmit}
            disabled={isLoading}
            className="btn-luxury-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Searching...' : submitLabel}
          </button>
        )}
      </div>
      {stats && <div className="mt-3">{stats}</div>}
      {error && (
        <p className="mt-3 text-sm text-red-400 font-medium tracking-tight px-4 py-3 bg-red-900/20 border border-red-900/50 rounded">
          &#x26A0; {error}
        </p>
      )}
    </div>
  );
}
