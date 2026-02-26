/**
 * Navigation component — CyperfBuddy.
 *
 * Two grouped dropdown menus:
 *   - Cyperf Strike DB  → CVE's Strikes (/browse), AI Strikes (/ai-cves)
 *   - Cyperf Applications DB → App Types (/cyperf-app-types), Apps (/cyperf-apps)
 *
 * One standalone link: CVE Search (/)
 * One standalone link: What is Cyperf (/what-is-cyperf)
 *
 * Dropdowns toggle on click. Clicking outside closes them.
 * Uses useRef + global click listener for outside-click dismissal.
 */
import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import axios from 'axios';

interface NavLink {
  path: string;
  label: string;
}

interface NavGroup {
  label: string;
  children: NavLink[];
}

type NavEntry =
  | { type: 'link'; path: string; label: string }
  | { type: 'group'; label: string; children: NavLink[] };

const NAV_STRUCTURE: NavEntry[] = [
  { type: 'link', path: '/', label: 'CVE Search' },
  {
    type: 'group',
    label: 'Cyperf Strike DB',
    children: [
      { path: '/browse', label: "CVE's Strikes" },
      { path: '/ai-cves', label: 'AI Strikes' },
    ],
  },
  {
    type: 'group',
    label: 'Cyperf Applications DB',
    children: [
      { path: '/cyperf-app-types', label: 'App Types' },
      { path: '/cyperf-apps', label: 'Apps' },
    ],
  },
  { type: 'link', path: '/what-is-cyperf', label: 'What is Cyperf' },
];

export default function Navigation() {
  const location = useLocation();
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const navRef = useRef<HTMLDivElement>(null);

  const isActive = (path: string) => location.pathname === path;
  const isGroupActive = (children: NavLink[]) =>
    children.some((c) => location.pathname === c.path);

  // Close dropdown when clicking outside the nav
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenGroup(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdown on route change
  useEffect(() => {
    setOpenGroup(null);
  }, [location.pathname]);

  const toggleGroup = (label: string) => {
    setOpenGroup((prev) => (prev === label ? null : label));
  };

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncStatus('idle');
    try {
      await axios.post('/api/admin/sync-cyperf');
      setSyncStatus('success');
      setTimeout(() => setSyncStatus('idle'), 3000);
    } catch {
      setSyncStatus('error');
      setTimeout(() => setSyncStatus('idle'), 5000);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <nav className="sticky top-0 z-50 bg-luxury-bg border-b border-luxury-border shadow-elegant">
      <div className="mx-auto max-w-7xl px-8 py-6" ref={navRef}>
        <div className="flex items-baseline justify-between">
          {/* Left: Brand + Nav */}
          <div className="flex items-baseline gap-16">
            {/* Brand */}
            <a
              href="/"
              className="font-display text-3xl font-bold text-keysight-red tracking-luxury whitespace-nowrap
                         transition-all duration-300 hover:text-red-600"
            >
              CyperfBuddy
            </a>

            {/* Nav items */}
            <div className="flex items-center gap-10">
              {NAV_STRUCTURE.map((entry) => {
                if (entry.type === 'link') {
                  return (
                    <a
                      key={entry.path}
                      href={entry.path}
                      className={`text-sm font-semibold tracking-luxury transition-all duration-200 relative
                        after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0
                        after:bg-luxury-accent after:transition-all after:duration-300
                        ${
                          isActive(entry.path)
                            ? 'text-luxury-accent after:w-full'
                            : 'text-luxury-text-secondary hover:text-luxury-text'
                        }`}
                    >
                      {entry.label}
                    </a>
                  );
                }

                // type === 'group'
                const group = entry as NavGroup & { type: 'group' };
                const isOpen = openGroup === group.label;
                const active = isGroupActive(group.children);

                return (
                  <div key={group.label} className="relative">
                    <button
                      onClick={() => toggleGroup(group.label)}
                      className={`inline-flex items-center gap-1 text-sm font-semibold tracking-luxury
                        transition-all duration-200 relative
                        after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0
                        after:bg-luxury-accent after:transition-all after:duration-300
                        ${
                          active
                            ? 'text-luxury-accent after:w-full'
                            : 'text-luxury-text-secondary hover:text-luxury-text'
                        }`}
                      aria-expanded={isOpen}
                      aria-haspopup="true"
                    >
                      {group.label}
                      <ChevronDown
                        className={`h-3.5 w-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                      />
                    </button>

                    {isOpen && (
                      <div
                        className="absolute top-full left-0 mt-2 min-w-[180px] rounded-md
                          border border-luxury-border bg-luxury-bg shadow-elegant py-1 z-50"
                      >
                        {group.children.map((child) => (
                          <a
                            key={child.path}
                            href={child.path}
                            className={`block px-4 py-2 text-sm font-semibold tracking-luxury
                              transition-colors duration-150
                              ${
                                isActive(child.path)
                                  ? 'text-luxury-accent bg-luxury-bg-subtle'
                                  : 'text-luxury-text-secondary hover:text-luxury-text hover:bg-luxury-bg-subtle'
                              }`}
                          >
                            {child.label}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Sync button */}
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className={`px-5 py-2 rounded-md text-xs font-semibold tracking-luxury uppercase transition-all duration-200
              ${
                syncStatus === 'success'
                  ? 'bg-green-50 text-green-700 border border-green-300'
                  : syncStatus === 'error'
                    ? 'bg-red-50 text-keysight-red border border-red-300'
                    : 'bg-red-50 text-keysight-red border border-red-200 hover:bg-red-100'
              }
              ${isSyncing ? 'opacity-75 cursor-wait' : 'hover:border-keysight-red cursor-pointer'}`}
            title="Trigger manual Cyperf sync to refresh CVE strike data"
          >
            {isSyncing ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Syncing...
              </span>
            ) : syncStatus === 'success' ? (
              <span>Synced</span>
            ) : syncStatus === 'error' ? (
              <span>Sync Failed</span>
            ) : (
              <span>Sync Data</span>
            )}
          </button>
        </div>
      </div>
    </nav>
  );
}
