import { useState, useMemo } from 'react';
import { useLatestCVEs } from '../hooks/useAPI';
import { SortState, CVEResponse } from '../types/api';
import DataTable from '../components/shared/DataTable';

const PAGE_SIZE = 500; // Backend max limit per page

export default function BrowsePage() {
  const [searchInput, setSearchInput] = useState('');
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });

  // Load all CVEs from database with Cyperf strike information
  // Show ONLY synced CVEs (testable = true)
  const { data: browseResult, isLoading } = useLatestCVEs(1, PAGE_SIZE);

  const tableData = browseResult?.cves || [];

  // Client-side filtering: search + always filter to testable only
  const filteredData = useMemo(() => {
    let results = tableData.filter((cve: CVEResponse) => cve.testable === true);

    // Apply search filter (CVE ID or strike name)
    if (searchInput.trim()) {
      const query = searchInput.toLowerCase();
      results = results.filter((cve: CVEResponse) =>
        cve.id.toLowerCase().includes(query) ||
        cve.attack_profiles?.some((profile: string) => profile.toLowerCase().includes(query))
      );
    }

    return results;
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
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          Synced CVEs
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          CVEs available for testing with Cyperf (synced from Cyperf instance)
        </p>
      </div>

      <div className="card-luxury space-y-5">
        {/* Search Input */}
        <div>
          <label className="block text-sm font-semibold text-luxury-text mb-3 tracking-tight">
            Search by CVE ID or Strike Name
          </label>
          <input
            type="text"
            placeholder="e.g., CVE-2023-26360 or Adobe"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="input-luxury w-full"
          />
        </div>

        {/* Stats */}
        <div className="flex items-center gap-6 text-xs tracking-tight border-t border-luxury-border pt-4">
          <div>
            <p className="text-luxury-text-secondary uppercase tracking-luxury mb-1">Synced CVEs</p>
            <p className="text-lg font-semibold text-luxury-accent">{filteredData.length}</p>
          </div>
          {searchInput && (
            <div>
              <p className="text-luxury-text-secondary uppercase tracking-luxury mb-1">Matching Results</p>
              <p className="text-lg font-semibold text-luxury-text">{filteredData.length}</p>
            </div>
          )}
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
