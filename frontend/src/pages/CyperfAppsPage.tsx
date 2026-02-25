/**
 * Cyperf Applications Page
 *
 * Displays all Cyperf applications fetched from the Controller.
 * No pagination - displays all records in a single table.
 */
import { useCyperfApplications } from '../hooks/useAPI';

export default function CyperfAppsPage() {
  const { data: apps, isLoading, isError, error } = useCyperfApplications();

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

      {/* Stats */}
      {!isLoading && !isError && (
        <div className="card-luxury">
          <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold mb-3">
            Summary
          </p>
          <p className="text-lg font-semibold text-luxury-accent">
            {apps?.length || 0} applications
          </p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && apps && apps.length > 0 && (
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
              {apps.map((app) => (
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

      {/* Empty state */}
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
