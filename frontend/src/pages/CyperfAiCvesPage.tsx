/**
 * CyperfAiCvesPage — displays AI-generated CVE entries from the ai_cves table.
 *
 * Fetches from GET /api/ai-cves. If the backend endpoint is not yet implemented,
 * the endpoint-not-available state is rendered with a clear TODO indicator.
 *
 * Structure mirrors BrowsePage.tsx: search input, stats bar, results table.
 * No Cyperf strike action (AI CVEs are informational / roadmap items).
 */
import { useState, useMemo } from 'react';
import { useAiCVEs } from '../hooks/useAPI';
import { AiCVEResponse } from '../types/api';

// TODO(quick-4): Replace with DataTable once the backend endpoint is implemented
// and the AiCVEResponse shape is confirmed against the real ai_cves schema.
function AiCveTable({ data }: { data: AiCVEResponse[] }) {
  if (data.length === 0) {
    return (
      <div className="card-luxury text-center py-12 space-y-2">
        <p className="text-luxury-text-secondary text-sm">No AI CVE entries found.</p>
        <p className="text-luxury-text-secondary text-xs">
          The ai_cves table may be empty or the sync job has not yet run.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-luxury-border">
      <table className="min-w-full divide-y divide-luxury-border text-sm">
        <thead className="bg-luxury-bg-subtle">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-luxury-text-secondary tracking-luxury uppercase">
              Strike ID
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-luxury-text-secondary tracking-luxury uppercase">
              AI Strike Name
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-luxury-text-secondary tracking-luxury uppercase">
              Description
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-luxury-border bg-luxury-bg">
          {data.map((entry, idx) => (
            <tr key={`${entry.id}-${idx}`} className="hover:bg-luxury-bg-subtle transition-colors">
              <td className="px-4 py-3 font-mono font-semibold text-luxury-accent whitespace-nowrap text-xs">
                {entry.id}
              </td>
              <td className="px-4 py-3 text-luxury-text-secondary font-mono text-xs">
                {entry.ai_strike_name ?? <span className="italic">—</span>}
              </td>
              <td className="px-4 py-3 text-luxury-text max-w-2xl">
                <p className="line-clamp-2 leading-relaxed text-sm">{entry.description || '—'}</p>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CyperfAiCvesPage() {
  const [searchInput, setSearchInput] = useState('');
  const { data: aiCves, isLoading, isError, error } = useAiCVEs();

  const filteredData = useMemo(() => {
    const records = aiCves ?? [];
    if (!searchInput.trim()) return records;
    const query = searchInput.toLowerCase();
    return records.filter(
      (entry: AiCVEResponse) =>
        entry.id.toLowerCase().includes(query) ||
        (entry.description?.toLowerCase().includes(query) ?? false) ||
        (entry.ai_strike_name?.toLowerCase().includes(query) ?? false)
    );
  }, [aiCves, searchInput]);

  // Determine whether the error is a 404 / endpoint-not-available scenario
  const isEndpointMissing =
    isError &&
    error instanceof Error &&
    (error.message.includes('404') || error.message.includes('Network Error'));

  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          All Cyperf Non CVE Strikes
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          AI-generated and non-CVE attack variants from Cyperf
        </p>
      </div>

      {/* Endpoint-not-available placeholder */}
      {isEndpointMissing && (
        <div className="card-luxury border border-luxury-accent/30 space-y-3">
          <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">
            Endpoint Unavailable
          </p>
          <p className="text-luxury-text text-sm leading-relaxed">
            The <span className="font-mono text-luxury-accent">/api/ai-cves</span> endpoint
            has not yet been implemented on the backend. Once the{' '}
            <span className="font-mono text-luxury-accent">ai_cves</span> table and
            corresponding FastAPI route are deployed, this page will display AI-generated
            CVE entries automatically.
          </p>
          {/* TODO(quick-4): Remove this block once /api/ai-cves is implemented */}
          <p className="text-luxury-text-secondary text-xs">
            See backend roadmap: implement <code>GET /api/ai-cves</code> returning{' '}
            <code>{'{ results: AiCVEResponse[], total: number }'}</code>.
          </p>
        </div>
      )}

      {/* Generic error state (not a missing endpoint) */}
      {isError && !isEndpointMissing && (
        <div className="card-luxury border border-red-700/40 space-y-2">
          <p className="text-xs tracking-luxury uppercase text-red-400 font-semibold">
            Error Loading Non-CVE Strikes
          </p>
          <p className="text-luxury-text-secondary text-sm">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      )}

      {/* Search + stats — only shown when endpoint is reachable */}
      {!isEndpointMissing && (
        <div className="card-luxury space-y-5">
          <div>
            <label className="block text-sm font-semibold text-luxury-text mb-3 tracking-tight">
              Search by CVE ID, Strike Name, or Description
            </label>
            <input
              type="text"
              placeholder="e.g., CVE-2024-1234 or InjectionAI"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="input-luxury w-full"
            />
          </div>

          <div className="flex items-center gap-6 text-xs tracking-tight border-t border-luxury-border pt-4">
            <div>
              <p className="text-luxury-text-secondary uppercase tracking-luxury mb-1">
                Non-CVE Strikes
              </p>
              <p className="text-lg font-semibold text-luxury-accent">
                {isLoading ? '—' : filteredData.length}
              </p>
            </div>
            {searchInput && (
              <div>
                <p className="text-luxury-text-secondary uppercase tracking-luxury mb-1">
                  Matching
                </p>
                <p className="text-lg font-semibold text-luxury-text">{filteredData.length}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="card-luxury flex items-center gap-3 text-luxury-text-secondary text-sm">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-luxury-accent border-t-transparent" />
          Loading AI CVE entries...
        </div>
      )}

      {/* Results table — only when data is available */}
      {!isLoading && !isError && <AiCveTable data={filteredData} />}
    </div>
  );
}
