/**
 * Cyperf Applications Page
 *
 * Displays all Cyperf applications fetched from the Controller.
 * No pagination - displays all records in a single table.
 * Client-side search filters by name or description (case-insensitive).
 */
import { useState } from 'react';
import { useCyperfApplications } from '../hooks/useAPI';
import { SearchBox } from '../components/shared/SearchBox';

export default function CyperfAppsPage() {
  const { data: apps, isLoading, isError, error } = useCyperfApplications();
  const [query, setQuery] = useState('');

  const filtered = (apps ?? []).filter((app) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (
      app.name?.toLowerCase().includes(q) ||
      app.description?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          Cyperf Apps
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Applications available in Cyperf for testing and validation scenarios
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="card-luxury flex items-center gap-3 text-luxury-text-secondary text-sm">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-luxury-accent border-t-transparent" />
          Loading applications...
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="card-luxury border border-red-700/40 space-y-2">
          <p className="text-xs tracking-luxury uppercase text-red-400 font-semibold">
            Error Loading Applications
          </p>
          <p className="text-luxury-text-secondary text-sm">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      )}

      {/* Search with stats below input */}
      <SearchBox
        label="Filter Applications"
        placeholder="Filter by name or description..."
        value={query}
        onChange={setQuery}
        stats={
          !isLoading && !isError ? (
            <p className="text-sm font-semibold text-luxury-accent">
              {query.trim()
                ? `${filtered.length} of ${apps?.length || 0} applications`
                : `${apps?.length || 0} applications`}
            </p>
          ) : undefined
        }
      />

      {/* Table */}
      {!isLoading && !isError && apps && apps.length > 0 && filtered.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-luxury-border">
          <table className="min-w-full divide-y divide-luxury-border text-sm">
            <thead className="bg-luxury-bg-subtle">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-luxury-text-secondary tracking-luxury uppercase">
                  ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-luxury-text-secondary tracking-luxury uppercase">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-luxury-text-secondary tracking-luxury uppercase">
                  Description
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-luxury-border bg-luxury-bg">
              {filtered.map((app) => (
                <tr key={app.id} className="hover:bg-luxury-bg-subtle transition-colors">
                  <td className="px-4 py-3 font-mono font-semibold text-luxury-accent text-xs">
                    {app.id}
                  </td>
                  <td className="px-4 py-3 text-luxury-text font-semibold">
                    {app.name}
                  </td>
                  <td className="px-4 py-3 text-luxury-text-secondary max-w-2xl">
                    <p className="line-clamp-2">{app.description || '—'}</p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* No search results (data exists but filter returns nothing) */}
      {!isLoading && !isError && apps && apps.length > 0 && filtered.length === 0 && (
        <div className="card-luxury text-center py-12 space-y-2">
          <p className="text-luxury-text-secondary text-sm">No applications match your search.</p>
          <p className="text-luxury-text-secondary text-xs">
            Try a different name or description term.
          </p>
        </div>
      )}

      {/* Empty state (no data at all) */}
      {!isLoading && !isError && (!apps || apps.length === 0) && (
        <div className="card-luxury text-center py-12 space-y-2">
          <p className="text-luxury-text-secondary text-sm">No applications found.</p>
          <p className="text-luxury-text-secondary text-xs">
            Run admin sync endpoint to fetch applications from Cyperf.
          </p>
        </div>
      )}
    </div>
  );
}
