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
    <div className="sticky top-16 z-40 bg-luxury-accent/10 text-luxury-accent px-8 py-4 border-b border-luxury-accent/30 flex justify-between items-center shadow-elegant animate-in">
      <span className="text-sm font-medium tracking-tight">
        ⚠ Data is {Math.floor(diffHours)}h old. Testability status may be inaccurate.
      </span>
      <button
        onClick={() => setIsDismissed(true)}
        className="ml-6 text-luxury-accent hover:text-luxury-accent-alt font-semibold transition-colors"
      >
        ✕
      </button>
    </div>
  );
}
