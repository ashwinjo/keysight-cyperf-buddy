import { useState } from 'react';
import { useSearchCVE } from '../hooks/useAPI';
import { SortState } from '../types/api';
import SearchForm from '../components/pages/SearchForm';
import DataTable from '../components/shared/DataTable';

export default function SearchPage() {
  const [searchInput, setSearchInput] = useState<string | null>(null);
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });

  const { data: cveResult, isLoading } = useSearchCVE(searchInput);

  // Convert single CVE result to array for DataTable
  const tableData = cveResult ? [cveResult] : [];

  const handleSort = (column: SortState['column']) => {
    if (sortState.column === column) {
      // Toggle direction or clear sort
      const nextDirection = sortState.direction === 'asc' ? 'desc' : null;
      setSortState({
        column: nextDirection ? column : null,
        direction: nextDirection,
      });
    } else {
      // Start new sort (ascending)
      setSortState({ column, direction: 'asc' });
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">Search CVEs</h1>

      <SearchForm
        onSearch={setSearchInput}
        isLoading={isLoading}
      />

      {searchInput && (
        <div className="mb-4 p-3 bg-gray-800 border border-gray-700 rounded text-gray-300 text-sm">
          Searching for: <span className="font-mono font-semibold">{searchInput}</span>
        </div>
      )}

      <DataTable
        data={tableData}
        isLoading={isLoading}
        sortState={sortState}
        onSort={handleSort}
      />

      {cveResult && (
        <div className="mt-6 p-4 bg-gray-900 border border-gray-700 rounded">
          <h2 className="text-lg font-semibold text-white mb-2">Details</h2>
          <div className="space-y-2 text-sm text-gray-300">
            <p><strong>Description:</strong> {cveResult.description}</p>
            <p><strong>CVSS v3.1:</strong> {cveResult.cvss_v3_1_score}</p>
            {cveResult.cvss_v4_0_score && (
              <p><strong>CVSS v4.0:</strong> {cveResult.cvss_v4_0_score}</p>
            )}
            <p><strong>References:</strong></p>
            <ul className="ml-4 list-disc">
              {cveResult.references.map((ref, i) => (
                <li key={i} className="text-blue-400 hover:underline">
                  <a href={ref} target="_blank" rel="noopener noreferrer">{ref}</a>
                </li>
              ))}
            </ul>
            {cveResult.attack_profile && (
              <p><strong>Cyperf Profile:</strong> {cveResult.attack_profile}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
