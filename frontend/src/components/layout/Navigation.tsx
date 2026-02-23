/**
 * Navigation component — persistent top nav bar with active page detection.
 *
 * Uses React Router v6 useLocation() to detect current path and apply
 * Keysight blue underline + white text to the active nav item.
 * Sticky positioning ensures nav remains visible during scroll.
 *
 * Browser back/forward works correctly because href links use React Router
 * history under the hood via BrowserRouter in App.tsx.
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
    <nav className="sticky top-0 z-50 border-b border-gray-700 bg-dark-950">
      <div className="mx-auto max-w-7xl px-6 py-4">
        <div className="flex gap-8">
          {NAV_ITEMS.map(({ path, label }) => (
            <a
              key={path}
              href={path}
              className={`text-sm font-medium transition-colors ${
                isActive(path)
                  ? 'text-white border-b-2 border-blue-500'
                  : 'text-gray-400 hover:text-gray-200 border-b-2 border-transparent'
              }`}
            >
              {label}
            </a>
          ))}
        </div>
      </div>
    </nav>
  );
}
