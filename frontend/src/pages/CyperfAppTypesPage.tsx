/**
 * Cyperf Application Types Page
 *
 * Displays all Cyperf application types fetched from the Controller.
 * No pagination - displays all records in a single table.
 * Client-side search filters by name or description (case-insensitive).
 */
import { useState } from 'react';
import { useCyperfApplicationTypes } from '../hooks/useAPI';
import { Input } from '../components/ui/input';

export default function CyperfAppTypesPage() {
  const { data: appTypes, isLoading, isError, error } = useCyperfApplicationTypes();
  const [query, setQuery] = useState('');

  const filtered = (appTypes ?? []).filter((at) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (
      at.name?.toLowerCase().includes(q) ||
      at.description?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          Cyperf App Types
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Application types available in Cyperf for test scenario configuration
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="card-luxury flex items-center gap-3 text-luxury-text-secondary text-sm">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-luxury-accent border-t-transparent" />
          Loading application types...
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="card-luxury border border-red-700/40 space-y-2">
          <p className="text-xs tracking-luxury uppercase text-red-400 font-semibold">
            Error Loading Application Types
          </p>
          <p className="text-luxury-text-secondary text-sm">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      )}

      {/* Stats */}
      {!isLoading && !isError && (
        <div className="card-luxury">
          <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold mb-3">
            Summary
          </p>
          <p className="text-lg font-semibold text-luxury-accent">
            {query.trim()
              ? `${filtered.length} of ${appTypes?.length || 0} application types`
              : `${appTypes?.length || 0} application types`}
          </p>
        </div>
      )}

      {/* Search input */}
      {!isLoading && !isError && appTypes && appTypes.length > 0 && (
        <div className="flex items-center gap-3">
          <Input
            type="search"
            placeholder="Filter by name or description..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="max-w-md"
          />
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && appTypes && appTypes.length > 0 && filtered.length > 0 && (
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
              {filtered.map((appType) => (
                <tr key={appType.id} className="hover:bg-luxury-bg-subtle transition-colors">
                  <td className="px-4 py-3 font-mono font-semibold text-luxury-accent text-xs">
                    {appType.id}
                  </td>
                  <td className="px-4 py-3 text-luxury-text font-semibold">
                    {appType.name}
                  </td>
                  <td className="px-4 py-3 text-luxury-text-secondary max-w-2xl">
                    <p className="line-clamp-2">{appType.description || '—'}</p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* No search results (data exists but filter returns nothing) */}
      {!isLoading && !isError && appTypes && appTypes.length > 0 && filtered.length === 0 && (
        <div className="card-luxury text-center py-12 space-y-2">
          <p className="text-luxury-text-secondary text-sm">No application types match your search.</p>
          <p className="text-luxury-text-secondary text-xs">
            Try a different name or description term.
          </p>
        </div>
      )}

      {/* Empty state (no data at all) */}
      {!isLoading && !isError && (!appTypes || appTypes.length === 0) && (
        <div className="card-luxury text-center py-12 space-y-2">
          <p className="text-luxury-text-secondary text-sm">No application types found.</p>
          <p className="text-luxury-text-secondary text-xs">
            Run admin sync endpoint to fetch application types from Cyperf.
          </p>
        </div>
      )}
    </div>
  );
}
