import { useLocation } from 'react-router-dom';

export default function Navigation() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { path: '/', label: 'Search' },
    { path: '/browse', label: 'Browse' },
    { path: '/batch', label: 'Batch' },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-700 bg-dark-950">
      <div className="mx-auto max-w-7xl px-6 py-4">
        <div className="flex gap-8">
          {navItems.map(({ path, label }) => (
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
