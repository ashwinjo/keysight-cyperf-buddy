import { useState, useMemo } from 'react';
import { useLatestCVEs } from '../hooks/useAPI';
import { SortState, CVEResponse } from '../types/api';
import DataTable from '../components/shared/DataTable';

const PAGE_SIZE = 500; // Backend max limit per page

export default function BrowsePage() {
  const [searchInput, setSearchInput] = useState('');
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });

  // Load all CVEs from database with Cyperf strike information
  // The database contains CVE-to-Strike mappings synced from Cyperf
  const { data: browseResult, isLoading } = useLatestCVEs(1, PAGE_SIZE);

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
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          Browse CVEs
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Explore the complete CVE database with Cyperf testability status
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

        {/* Stats */}
        <div className="flex items-center gap-6 text-xs tracking-tight border-t border-luxury-border pt-4">
          <div>
            <p className="text-luxury-text-secondary uppercase tracking-luxury mb-1">Total CVEs</p>
            <p className="text-lg font-semibold text-luxury-accent">{tableData.length}</p>
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
