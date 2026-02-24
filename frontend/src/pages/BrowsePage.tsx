import { useState, useMemo } from 'react';
import { useLatestCVEs } from '../hooks/useAPI';
import { SortState, CVEResponse } from '../types/api';
import DataTable from '../components/shared/DataTable';

const PAGE_SIZE = 500; // Backend max limit per page

export default function BrowsePage() {
  const [searchInput, setSearchInput] = useState('');
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });
  const [currentPage, setCurrentPage] = useState(1);
  const [showOnlyTestable, setShowOnlyTestable] = useState(false);

  // Load CVEs from database with Cyperf strike information
  // The database contains CVE-to-Strike mappings synced from Cyperf
  // Note: Testable CVEs are from older years (pre-2026); browse pages to find them
  const { data: browseResult, isLoading } = useLatestCVEs(currentPage, PAGE_SIZE);

  const tableData = browseResult?.cves || [];
  const total = browseResult?.total || 0;

  // Client-side filtering: search + testable filter
  const filteredData = useMemo(() => {
    let results = tableData;

    // Apply search filter
    if (searchInput.trim()) {
      const query = searchInput.toLowerCase();
      results = results.filter((cve: CVEResponse) =>
        cve.id.toLowerCase().includes(query) ||
        cve.attack_profiles?.some((profile: string) => profile.toLowerCase().includes(query))
      );
    }

    // Apply testable filter
    if (showOnlyTestable) {
      results = results.filter((cve: CVEResponse) => cve.testable === true);
    }

    return results;
  }, [tableData, searchInput, showOnlyTestable]);

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
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          Browse CVEs
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Explore the CVE database with Cyperf testability status. Testable CVEs are from years 2023 and earlier.
        </p>
      </div>

      <div className="card-luxury space-y-5">
        {/* Search Input */}
        <div>
          <label className="block text-sm font-semibold text-luxury-text mb-3 tracking-tight">
            Search by CVE ID or Test Profile
          </label>
          <input
            type="text"
            placeholder="e.g., CVE-2023-26360 or nginx"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="input-luxury w-full"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-6 pt-4 border-t border-luxury-border">
          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={showOnlyTestable}
              onChange={(e) => {
                setShowOnlyTestable(e.target.checked);
                setCurrentPage(1); // Reset to first page when filtering
              }}
              className="w-5 h-5 rounded bg-luxury-bg-subtle border border-luxury-border cursor-pointer accent-luxury-accent transition-all hover:border-luxury-accent"
            />
            <span className="text-sm font-semibold text-luxury-text tracking-tight group-hover:text-luxury-accent transition-colors">
              Show Testable Only
            </span>
          </label>
        </div>

        {/* Stats and Pagination */}
        <div className="space-y-4 pt-4 border-t border-luxury-border">
          <div className="flex items-center justify-between text-xs tracking-tight">
            <div className="space-y-1">
              <p className="text-luxury-text-secondary uppercase tracking-luxury">Showing Results</p>
              <p className="text-sm text-luxury-text">
                Page {currentPage} • {filteredData.length} of {tableData.length} total on this page
                {showOnlyTestable && ` (filtered to testable only)`}
              </p>
            </div>
          </div>

          {/* Pagination Controls */}
          <div className="flex items-center gap-4 pt-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-2 text-xs font-semibold tracking-luxury uppercase bg-luxury-bg-subtle border border-luxury-border rounded hover:border-luxury-accent disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              ← Previous
            </button>

            <input
              type="number"
              value={currentPage}
              onChange={(e) => setCurrentPage(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-16 px-2 py-2 text-xs text-center bg-luxury-bg-subtle border border-luxury-border rounded text-luxury-text"
              min="1"
            />

            <button
              onClick={() => setCurrentPage(currentPage + 1)}
              className="px-3 py-2 text-xs font-semibold tracking-luxury uppercase bg-luxury-bg-subtle border border-luxury-border rounded hover:border-luxury-accent transition-all"
            >
              Next →
            </button>

            <span className="ml-auto text-xs text-luxury-text-secondary">
              💡 Tip: Testable CVEs are from 2023 and earlier. Try page 50+ or filter by testable.
            </span>
          </div>
        </div>
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
