import { useState, useMemo } from 'react';
import { useLatestCVEs } from '../hooks/useAPI';
import { SortState, CVEResponse } from '../types/api';
import TestableFilter from '../components/pages/TestableFilter';
import DataTable from '../components/shared/DataTable';

const PAGE_SIZE = 1000; // Load all CVEs at once

export default function BrowsePage() {
  const [searchInput, setSearchInput] = useState('');
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });

  // Always load from page 1 with large page size to get all CVEs
  const { data: browseResult, isLoading } = useLatestCVEs(1, PAGE_SIZE, false);

  const tableData = browseResult?.cves || [];
  const total = browseResult?.total || 0;
  const hasNext = browseResult?.has_next || false;

  // Client-side search across CVE ID and Strike names
  const filteredData = useMemo(() => {
    if (!searchInput.trim()) return tableData;
    const query = searchInput.toLowerCase();
    return tableData.filter((cve: CVEResponse) =>
      cve.id.toLowerCase().includes(query) ||
      cve.attack_profiles?.some((profile: string) => profile.toLowerCase().includes(query))
    );
  }, [tableData, searchInput]);

  const handleSort = (column: SortState['column']) => {
    if (sortState.column === column) {
      const nextDirection = sortState.direction === 'asc' ? 'desc' : null;
      setSortState({
        column: nextDirection ? column : null,
        direction: nextDirection,
      });
    } else {
      setSortState({ column, direction: 'asc' });
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">Browse All CVEs & Cyperf Strikes</h1>

      <div className="mb-6 p-4 bg-gray-900 border border-gray-700 rounded space-y-4">
        {/* Search Input */}
        <div>
          <label className="block text-sm font-semibold text-gray-300 mb-2">
            Search by CVE ID or Strike Name
          </label>
          <input
            type="text"
            placeholder="e.g., CVE-2023-26360 or nginx"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
          />
        </div>

        {/* Stats */}
        <p className="text-xs text-gray-400">
          Total CVEs in database: <span className="font-semibold text-white">{tableData.length}</span>
          {searchInput && ` • Matching your search: ${filteredData.length}`}
        </p>
      </div>

      <DataTable
        data={filteredData}
        isLoading={isLoading}
        sortState={sortState}
        onSort={handleSort}
      />
    </div>
  );
}
