import { useState, useMemo } from 'react';
import { useLatestCVEs } from '../hooks/useAPI';
import { SortState, CVEResponse } from '../types/api';
import TestableFilter from '../components/pages/TestableFilter';
import DataTable from '../components/shared/DataTable';

const PAGE_SIZE = 100;

export default function BrowsePage() {
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage] = useState(1);
  const [onlyTestable, setOnlyTestable] = useState(false);
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });

  const { data: browseResult, isLoading } = useLatestCVEs(page, PAGE_SIZE, onlyTestable);

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

  const handleNextPage = () => {
    if (hasNext) setPage(page + 1);
  };

  const handlePrevPage = () => {
    if (page > 1) setPage(page - 1);
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

        {/* Filters */}
        <TestableFilter checked={onlyTestable} onChange={setOnlyTestable} />

        {/* Stats */}
        <p className="text-xs text-gray-400">
          Showing {filteredData.length} of {tableData.length} CVEs on this page
          {onlyTestable && ' (testable only)'}
          {searchInput && ` • Filtered by: "${searchInput}"`}
        </p>
      </div>

      <DataTable
        data={filteredData}
        isLoading={isLoading}
        sortState={sortState}
        onSort={handleSort}
      />

      <div className="mt-6 flex justify-between items-center">
        <button
          onClick={handlePrevPage}
          disabled={page === 1 || isLoading}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white rounded transition"
        >
          &larr; Previous
        </button>

        <span className="text-gray-400 text-sm">
          Page {page} of {Math.ceil(total / PAGE_SIZE)}
        </span>

        <button
          onClick={handleNextPage}
          disabled={!hasNext || isLoading}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white rounded transition"
        >
          Next &rarr;
        </button>
      </div>
    </div>
  );
}
