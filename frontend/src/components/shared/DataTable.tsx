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
    return <div className="p-4 text-center text-gray-400">Loading CVEs...</div>;
  }

  if (data.length === 0) {
    return <div className="p-4 text-center text-gray-400">No CVEs found</div>;
  }

  return (
    <div className="overflow-x-auto border border-gray-700 rounded">
      <table className="w-full text-sm">
        <thead className="bg-dark-950 border-b border-gray-700">
          <tr>
            <th
              onClick={() => handleHeaderClick('cve_id')}
              className="px-4 py-2 text-left font-semibold text-gray-300 cursor-pointer hover:bg-gray-800 transition"
            >
              CVE ID
              {getSortIcon('cve_id')}
            </th>
            <th className="px-4 py-2 text-left font-semibold text-gray-300">
              CNA
            </th>
            <th
              onClick={() => handleHeaderClick('cvss')}
              className="px-4 py-2 text-left font-semibold text-gray-300 cursor-pointer hover:bg-gray-800 transition"
            >
              CVSS Score
              {getSortIcon('cvss')}
            </th>
            <th
              onClick={() => handleHeaderClick('published_date')}
              className="px-4 py-2 text-left font-semibold text-gray-300 cursor-pointer hover:bg-gray-800 transition"
            >
              Published
              {getSortIcon('published_date')}
            </th>
            <th className="px-4 py-2 text-left font-semibold text-gray-300">
              Can Cyperf Test?
            </th>
            <th className="px-4 py-2 text-left font-semibold text-gray-300">
              Cyperf Strikes
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((cve) => (
            <tr key={cve.id} className="border-b border-gray-700 hover:bg-gray-900 transition">
              <td className="px-4 py-2 font-mono text-gray-200">{cve.id}</td>
              <td className="px-4 py-2 text-gray-300 text-sm">
                {cve.cna ? <span className="text-blue-400">{cve.cna}</span> : <span className="text-gray-500">—</span>}
              </td>
              <td className="px-4 py-2 text-gray-300">{cve.cvss_v3_1_score}</td>
              <td className="px-4 py-2 text-gray-400">
                {new Date(cve.published_date).toLocaleDateString()}
              </td>
              <td className="px-4 py-2">
                <Badge testable={cve.testable} />
              </td>
              <td className="px-4 py-2 text-gray-400 text-xs max-w-xs">
                {cve.attack_profiles && cve.attack_profiles.length > 0 ? (
                  <div className="flex flex-col gap-1">
                    {cve.attack_profiles.map((profile, idx) => (
                      <span key={idx} className="block bg-gray-800 px-2 py-1 rounded text-gray-300">
                        {profile}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-gray-500">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
