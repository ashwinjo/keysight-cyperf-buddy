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
    <form onSubmit={handleSubmit} className="mb-6">
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="e.g., CVE-2024-1234"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (error) setError('');
          }}
          className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white font-medium rounded transition"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>
      {error && <p className="mt-2 text-red-400 text-sm">{error}</p>}
    </form>
  );
}
