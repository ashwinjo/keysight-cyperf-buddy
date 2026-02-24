/**
 * Navigation component — premium luxury styling for CVE2Strike.
 *
 * Refined aesthetic with elegant typography, gold accents, and sophisticated
 * spacing. Uses display font for brand, subtle animations on interactions.
 * Includes manual sync button to refresh CVE strike data from Cyperf.
 */
import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';

interface NavItem {
  path: string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Search' },
  { path: '/browse', label: 'Browse' },
  { path: '/batch', label: 'Batch' },
];

export default function Navigation() {
  const location = useLocation();
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const isActive = (path: string) => location.pathname === path;

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncStatus('idle');

    try {
      await axios.post('/api/admin/sync-cyperf');
      setSyncStatus('success');
      // Reset success message after 3 seconds
      setTimeout(() => setSyncStatus('idle'), 3000);
    } catch (error) {
      setSyncStatus('error');
      // Reset error message after 5 seconds
      setTimeout(() => setSyncStatus('idle'), 5000);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <nav className="sticky top-0 z-50 bg-luxury-bg border-b border-luxury-border shadow-elegant">
      <div className="mx-auto max-w-7xl px-8 py-6">
        <div className="flex items-baseline justify-between">
          {/* Left side: Brand + Navigation menu */}
          <div className="flex items-baseline gap-16">
            {/* Brand name — elegant serif display */}
            <a
              href="/"
              className="font-display text-3xl font-bold text-luxury-accent tracking-luxury whitespace-nowrap
                         transition-all duration-300 hover:text-luxury-accent-alt"
            >
              CVE²Strike
            </a>

            {/* Navigation menu */}
            <div className="flex gap-10">
              {NAV_ITEMS.map(({ path, label }) => (
                <a
                  key={path}
                  href={path}
                  className={`text-sm font-semibold tracking-luxury uppercase transition-all duration-200 relative
                    after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0
                    after:bg-luxury-accent after:transition-all after:duration-300
                    ${
                      isActive(path)
                        ? 'text-luxury-accent after:w-full'
                        : 'text-luxury-text-secondary hover:text-luxury-text'
                    }`}
                >
                  {label}
                </a>
              ))}
            </div>
          </div>

          {/* Right side: Sync Data button */}
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className={`px-5 py-2 rounded-md text-xs font-semibold tracking-luxury uppercase transition-all duration-200
              ${
                syncStatus === 'success'
                  ? 'bg-green-900/30 text-green-300 border border-green-700/50'
                  : syncStatus === 'error'
                    ? 'bg-red-900/30 text-red-300 border border-red-700/50'
                    : 'bg-luxury-accent/10 text-luxury-accent border border-luxury-accent/30 hover:bg-luxury-accent/20'
              }
              ${isSyncing ? 'opacity-75 cursor-wait' : 'hover:border-luxury-accent cursor-pointer'}`}
            title="Trigger manual Cyperf sync to refresh CVE strike data"
          >
            {isSyncing ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"></span>
                Syncing...
              </span>
            ) : syncStatus === 'success' ? (
              <span>✓ Synced</span>
            ) : syncStatus === 'error' ? (
              <span>✗ Sync Failed</span>
            ) : (
              <span>🔄 Sync Data</span>
            )}
          </button>
        </div>
      </div>
    </nav>
  );
}
