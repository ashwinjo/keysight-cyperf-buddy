/**
 * StatusBar footer component — displays time since last Cyperf sync.
 *
 * Renders at the bottom of every page via App.tsx layout composition.
 * Calls useSyncStatus() which auto-refetches every 5 minutes via React Query.
 *
 * Satisfies requirement SYNC-03: "Data last updated: X hours ago" always visible.
 */
import { useSyncStatus } from '../../hooks/useAPI';

/**
 * Convert ISO 8601 timestamp to human-readable "Xh ago" format.
 * Returns "unknown" if timestamp is null or unparseable.
 */
function formatTimeSince(isoTimestamp: string | null): string {
  if (!isoTimestamp) return 'unknown';
  const lastSync = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - lastSync.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  return `${diffHours}h ago`;
}

export default function StatusBar() {
  const { data: syncStatus } = useSyncStatus();

  const lastUpdateText = syncStatus?.last_successful_sync
    ? `Data last updated: ${formatTimeSince(syncStatus.last_successful_sync)}`
    : 'Data status: never synced';

  return (
    <footer className="mt-12 border-t border-gray-700 bg-dark-950 py-4 text-xs text-gray-500">
      <div className="mx-auto max-w-7xl px-6 flex justify-between">
        <span>{lastUpdateText}</span>
        <span>Cyperf CVE Tracker v0.1</span>
      </div>
    </footer>
  );
}
