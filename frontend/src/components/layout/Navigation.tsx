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
 * Right side:
 *   - SyncButton: triggers POST /admin/sync-cyperf-now; shows last-sync timestamp
 *   - Settings gear icon: opens SettingsPanel modal for endpoint configuration
 *
 * Endpoint config is fetched on mount and refreshed every 30 s.
 * Last sync timestamp is sourced from useSyncStatus (same hook used by StatusBar).
 *
 * Dropdowns toggle on click. Clicking outside closes them.
 * Uses useRef + global click listener for outside-click dismissal.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { ChevronDown, Settings } from 'lucide-react';
import axios from 'axios';
import { SyncButton } from './SyncButton';
import { SettingsPanel } from './SettingsPanel';
import { ErrorBoundary } from '../ErrorBoundary';
import { useSyncStatus } from '../../hooks/useAPI';

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
  const [showSettings, setShowSettings] = useState(false);
  const [endpoint, setEndpoint] = useState<string | undefined>(undefined);
  const navRef = useRef<HTMLDivElement>(null);

  // Use the existing hook so we don't add a second sync-status fetch
  const { data: syncStatus } = useSyncStatus();
  const lastSyncAt = syncStatus?.last_successful_sync ?? null;

  const isActive = (path: string) => location.pathname === path;
  const isGroupActive = (children: NavLink[]) =>
    children.some((c) => location.pathname === c.path);

  // Fetch current endpoint configuration from backend
  const fetchEndpointConfig = useCallback(async () => {
    try {
      const res = await axios.get<{ endpoint: string; is_valid: boolean }>(
        '/api/admin/config/cyperf-endpoint'
      );
      // Backend always returns HTTP 200 even if no endpoint configured (empty string)
      setEndpoint(res.data.endpoint || undefined);
    } catch (err) {
      // Non-fatal: backend unreachable — keep whatever was previously set
      // SyncButton will be disabled if endpoint remains undefined
      console.error('[Navigation] Failed to fetch CyPerf endpoint config:', err);
    }
  }, []);

  // Fetch on mount, then poll every 30 seconds
  useEffect(() => {
    void fetchEndpointConfig();
    const interval = setInterval(() => void fetchEndpointConfig(), 30_000);
    return () => clearInterval(interval);
  }, [fetchEndpointConfig]);

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

  const handleEndpointSaved = (savedEndpoint: string) => {
    // Immediately update state so SyncButton becomes enabled without waiting for poll
    setEndpoint(savedEndpoint || undefined);
    setShowSettings(false);
  };

  return (
    <nav className="sticky top-0 z-50 bg-luxury-bg border-b border-luxury-border shadow-elegant">
      <div className="mx-auto max-w-7xl px-8 py-6" ref={navRef}>
        <div className="flex items-center justify-between">
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
                        aria-hidden="true"
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

          {/* Right: Sync button + Settings gear (wrapped in ErrorBoundary) */}
          <ErrorBoundary label="NavbarControls">
            <div className="flex items-center gap-3">
              <SyncButton
                endpoint={endpoint}
                lastSyncAt={lastSyncAt}
                onSyncComplete={(success) => {
                  if (success) {
                    // Refresh endpoint config in case sync updated something
                    void fetchEndpointConfig();
                  }
                }}
              />

              <button
                onClick={() => setShowSettings(true)}
                aria-label="Open CyPerf endpoint settings"
                title="CyPerf endpoint settings"
                className={`inline-flex items-center justify-center h-8 w-8 rounded-md
                  text-luxury-text-secondary hover:text-luxury-text hover:bg-luxury-bg-subtle
                  transition-colors duration-200
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-luxury-accent
                  focus-visible:ring-offset-2 focus-visible:ring-offset-luxury-bg
                  ${!endpoint ? 'text-luxury-accent' : ''}`}
              >
                <Settings
                  className={`h-4 w-4 ${!endpoint ? 'text-luxury-accent' : ''}`}
                  aria-hidden="true"
                />
              </button>
            </div>
          </ErrorBoundary>
        </div>
      </div>

      {/* Settings modal (rendered outside nav div to avoid z-index issues) */}
      <ErrorBoundary label="SettingsPanel" fallback={<div />}>
        <SettingsPanel
          isOpen={showSettings}
          onOpenChange={setShowSettings}
          currentEndpoint={endpoint}
          onEndpointSaved={handleEndpointSaved}
        />
      </ErrorBoundary>
    </nav>
  );
}
