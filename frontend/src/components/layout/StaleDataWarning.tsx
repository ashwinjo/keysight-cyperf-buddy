import { useState } from 'react';
import { useSyncStatus } from '../../hooks/useAPI';

export default function StaleDataWarning() {
  const { data: syncStatus } = useSyncStatus();
  const [isDismissed, setIsDismissed] = useState(false);

  if (!syncStatus?.last_successful_sync || isDismissed) {
    return null;
  }

  const lastSync = new Date(syncStatus.last_successful_sync);
  const now = new Date();
  const diffMs = now.getTime() - lastSync.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  const isStale = diffHours > 25;

  if (!isStale) {
    return null;
  }

  return (
    <div className="sticky top-16 z-40 bg-yellow-900 text-yellow-200 px-6 py-3 border-b border-yellow-700 flex justify-between items-center">
      <span className="text-sm font-medium">
        Cyperf data is outdated (last sync {Math.floor(diffHours)}h ago). Some testability badges may be inaccurate.
      </span>
      <button
        onClick={() => setIsDismissed(true)}
        className="ml-4 text-yellow-300 hover:text-yellow-100 font-bold"
      >
        &#x2715;
      </button>
    </div>
  );
}
