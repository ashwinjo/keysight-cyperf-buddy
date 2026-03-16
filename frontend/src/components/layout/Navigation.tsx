/**
 * Navigation component — CyperfBuddy.
 *
 * Two grouped dropdown menus:
 *   - ATI Profiles → CVE's Strikes (/browse), AI Strikes (/ai-cves), Apps (/cyperf-apps)
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
import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';

interface NavLink {
  path: string;
  label: string;
}

interface NavGroup {
  label: string;
  children: NavLink[];
}

interface NavSection {
  sectionLabel: string;
  items: NavLink[];
}

type NavEntry =
  | { type: 'link'; path: string; label: string }
  | { type: 'group'; label: string; children: NavLink[] }
  | { type: 'sectioned-group'; label: string; sections: NavSection[] };

const NAV_STRUCTURE: NavEntry[] = [
  { type: 'link', path: '/', label: 'NIST NVD - CVE Search' },
  {
    type: 'sectioned-group',
    label: 'Cyperf ATI Profile',
    sections: [
      {
        sectionLabel: 'Cyperf Strike',
        items: [
          { path: '/browse', label: "CVE's Strikes" },
          { path: '/ai-cves', label: 'AI Strikes' },
        ],
      },
      {
        sectionLabel: 'Cyperf Application',
        items: [
          { path: '/cyperf-apps', label: 'Apps' },
        ],
      },
    ],
  },
  { type: 'link', path: '/l47-advisor', label: 'L4-7 Advisor' },
  { type: 'link', path: '/cyperf-deployment', label: 'Cyperf Deployment' },
  { type: 'link', path: '/what-is-cyperf', label: 'Cyperf Automation' },
];

export default function Navigation() {
  const location = useLocation();
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const navRef = useRef<HTMLDivElement>(null);

  const isActive = (path: string) => location.pathname === path;
  const isGroupActive = (children: NavLink[]) =>
    children.some((c) => location.pathname === c.path);
  const isSectionedGroupActive = (sections: NavSection[]) =>
    sections.some((s) => s.items.some((item) => location.pathname === item.path));

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

  return (
    <nav className="sticky top-0 z-50 bg-luxury-bg border-b border-luxury-border shadow-elegant">
      <div className="mx-auto max-w-7xl px-8 py-6" ref={navRef}>
        <div className="flex items-center">
          <div className="flex items-baseline gap-16">
            {/* Brand */}
            <a
              href="/"
              className="font-display text-3xl font-bold text-luxury-accent tracking-luxury whitespace-nowrap
                         transition-all duration-300 hover:text-luxury-accent-alt"
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

                // type === 'sectioned-group'
                if (entry.type === 'sectioned-group') {
                  const sg = entry;
                  const isOpen = openGroup === sg.label;
                  const active = isSectionedGroupActive(sg.sections);

                  return (
                    <div key={sg.label} className="relative">
                      <button
                        onClick={() => toggleGroup(sg.label)}
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
                        {sg.label}
                        <ChevronDown
                          className={`h-3.5 w-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                          aria-hidden="true"
                        />
                      </button>

                      {isOpen && (
                        <div
                          className="absolute top-full left-0 mt-2 min-w-[200px] rounded-md
                            border border-luxury-border bg-luxury-bg shadow-elegant py-1 z-50"
                        >
                          {sg.sections.map((section, idx) => (
                            <div key={section.sectionLabel}>
                              {idx > 0 && (
                                <div className="my-1 border-t border-luxury-border/40" />
                              )}
                              <div className="px-4 py-1.5 text-xs font-bold tracking-widest uppercase text-luxury-text-secondary/60 select-none">
                                {section.sectionLabel}
                              </div>
                              {section.items.map((item) => (
                                <a
                                  key={item.path}
                                  href={item.path}
                                  className={`block px-4 py-2 text-sm font-semibold tracking-luxury
                                    transition-colors duration-150
                                    ${
                                      isActive(item.path)
                                        ? 'text-luxury-accent bg-luxury-bg-subtle'
                                        : 'text-luxury-text-secondary hover:text-luxury-text hover:bg-luxury-bg-subtle'
                                    }`}
                                >
                                  {item.label}
                                </a>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
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

        </div>
      </div>
    </nav>
  );
}
