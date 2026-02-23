import { useState } from 'react';
import { useLatestCVEs } from '../hooks/useAPI';
import { SortState } from '../types/api';
import TestableFilter from '../components/pages/TestableFilter';
import DataTable from '../components/shared/DataTable';

const PAGE_SIZE = 25;

export default function BrowsePage() {
  const [page, setPage] = useState(1);
  const [onlyTestable, setOnlyTestable] = useState(false);
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });

  const { data: browseResult, isLoading } = useLatestCVEs(page, PAGE_SIZE, onlyTestable);

  const tableData = browseResult?.cves || [];
  const total = browseResult?.total || 0;
  const hasNext = browseResult?.has_next || false;

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
      <h1 className="text-3xl font-bold text-white mb-6">Browse Latest CVEs</h1>

      <div className="mb-6 p-4 bg-gray-900 border border-gray-700 rounded">
        <TestableFilter checked={onlyTestable} onChange={setOnlyTestable} />
        <p className="text-xs text-gray-400">
          Showing {tableData.length} of {total} CVEs
          {onlyTestable && ' (testable only)'}
        </p>
      </div>

      <DataTable
        data={tableData}
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
