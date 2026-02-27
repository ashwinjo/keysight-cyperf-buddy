import { useState } from 'react';
import { SearchBox } from '../shared/SearchBox';

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

  const handleSubmit = () => {
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
    <SearchBox
      label="Search CVEs"
      placeholder="e.g., CVE-2024-1234"
      value={input}
      onChange={(v) => {
        setInput(v);
        if (error) setError('');
      }}
      onSubmit={handleSubmit}
      isLoading={isLoading}
      submitLabel="Search"
      error={error}
    />
  );
}
