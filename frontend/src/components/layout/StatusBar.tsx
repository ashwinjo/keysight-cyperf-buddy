import { useSyncStatus } from '../../hooks/useAPI';

export default function StatusBar() {
  const { data: syncStatus } = useSyncStatus();

  const formatTimeSince = (isoTimestamp: string | null): string => {
    if (!isoTimestamp) return 'unknown';
    const lastSync = new Date(isoTimestamp);
    const now = new Date();
    const diffMs = now.getTime() - lastSync.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    return `${diffHours}h ago`;
  };

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
