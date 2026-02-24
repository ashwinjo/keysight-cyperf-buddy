import { useState } from 'react';

interface SearchFormProps {
  onSearch: (cveId: string) => void;
  isLoading: boolean;
}

export default function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const [input, setInput] = useState('');
  const [error, setError] = useState('');

  const validateCVEID = (id: string): boolean => {
    // Format: CVE-YYYY-NNNNN or CVE-YYYY-NNNN
    const cveRegex = /^CVE-\d{4}-\d{4,5}$/i;
    return cveRegex.test(id.trim());
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim().toUpperCase();

    if (!trimmed) {
      setError('Please enter a CVE ID');
      return;
    }

    if (!validateCVEID(trimmed)) {
      setError('Invalid CVE format. Use: CVE-YYYY-NNNNN');
      return;
    }

    setError('');
    onSearch(trimmed);
  };

  return (
    <form onSubmit={handleSubmit} className="card-luxury">
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="e.g., CVE-2024-1234"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (error) setError('');
          }}
          className="input-luxury flex-1"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading}
          className="btn-luxury-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>
      {error && (
        <p className="mt-4 text-sm text-red-400 font-medium tracking-tight px-4 py-3 bg-red-900/20 border border-red-900/50 rounded">
          ⚠ {error}
        </p>
      )}
    </form>
  );
}
