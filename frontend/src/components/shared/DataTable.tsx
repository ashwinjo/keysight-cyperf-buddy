import { CVEResponse, SortState } from '../../types/api';
import Badge from './Badge';

interface DataTableProps {
  data: CVEResponse[];
  isLoading: boolean;
  onSort: (column: SortState['column']) => void;
  sortState: SortState;
}

export default function DataTable({ data, isLoading, onSort, sortState }: DataTableProps) {
  const getSortIcon = (column: SortState['column']) => {
    if (sortState.column !== column) return ' \u2195';
    return sortState.direction === 'asc' ? ' \u2191' : ' \u2193';
  };

  const handleHeaderClick = (column: SortState['column']) => {
    onSort(column);
  };

  if (isLoading) {
    return <div className="p-8 text-center text-luxury-text-secondary">Loading CVEs...</div>;
  }

  if (data.length === 0) {
    return <div className="p-8 text-center text-luxury-text-secondary">No CVEs found</div>;
  }

  return (
    <div className="card-luxury overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-luxury-bg border-b border-luxury-border">
          <tr>
            <th
              onClick={() => handleHeaderClick('cve_id')}
              className="px-6 py-4 text-left font-semibold text-luxury-accent text-xs tracking-luxury uppercase cursor-pointer hover:bg-luxury-bg-subtle transition"
            >
              CVE ID {getSortIcon('cve_id')}
            </th>
            <th
              onClick={() => handleHeaderClick('published_date')}
              className="px-6 py-4 text-left font-semibold text-luxury-accent text-xs tracking-luxury uppercase cursor-pointer hover:bg-luxury-bg-subtle transition"
            >
              Published {getSortIcon('published_date')}
            </th>
            <th className="px-6 py-4 text-left font-semibold text-luxury-accent text-xs tracking-luxury uppercase">
              Can Cyperf Test this ?
            </th>
            <th className="px-6 py-4 text-left font-semibold text-luxury-accent text-xs tracking-luxury uppercase">
              Cyperf Profiles
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-luxury-border">
          {data.map((cve) => (
            <tr key={cve.id} className="hover:bg-luxury-bg transition-colors duration-150">
              <td className="px-6 py-4 font-mono text-luxury-accent text-xs">{cve.id}</td>
              <td className="px-6 py-4 text-luxury-text-secondary text-sm">
                {new Date(cve.published_date).toLocaleDateString()}
              </td>
              <td className="px-6 py-4">
                <Badge testable={cve.testable} />
              </td>
              <td className="px-6 py-4 text-luxury-text text-xs max-w-xs">
                {cve.attack_profiles && cve.attack_profiles.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {cve.attack_profiles.map((profile, idx) => (
                      <span key={idx} className="inline-block bg-luxury-bg px-2.5 py-1.5 rounded border border-luxury-border/50 text-luxury-text-secondary hover:text-luxury-text transition">
                        {profile}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-luxury-text-secondary/60">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
