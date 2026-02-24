/**
 * Navigation component — premium luxury styling for CVE2Strike.
 *
 * Refined aesthetic with elegant typography, gold accents, and sophisticated
 * spacing. Uses display font for brand, subtle animations on interactions.
 */
import { useLocation } from 'react-router-dom';

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

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="sticky top-0 z-50 bg-luxury-bg border-b border-luxury-border shadow-elegant">
      <div className="mx-auto max-w-7xl px-8 py-6">
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
      </div>
    </nav>
  );
}
