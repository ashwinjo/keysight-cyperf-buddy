import { useState } from 'react';
import { useSearchCVE } from '../hooks/useAPI';
import { SortState, ContactContext } from '../types/api';
import SearchForm from '../components/pages/SearchForm';
import DataTable from '../components/shared/DataTable';
import { ContactFormSidebar } from '../components/contact/ContactFormSidebar';

export default function SearchPage() {
  const [searchInput, setSearchInput] = useState<string | null>(null);
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: null });
  const [contactSidebarOpen, setContactSidebarOpen] = useState(false);
  const [contactContext, setContactContext] = useState<ContactContext>('discuss');

  const { data: cveResult, isLoading } = useSearchCVE(searchInput);

  const openSidebar = (ctx: ContactContext) => {
    setContactContext(ctx);
    setContactSidebarOpen(true);
  };

  // Convert single CVE result to array for DataTable
  const tableData = cveResult ? [cveResult] : [];

  const handleSort = (column: SortState['column']) => {
    if (sortState.column === column) {
      // Toggle direction or clear sort
      const nextDirection = sortState.direction === 'asc' ? 'desc' : null;
      setSortState({
        column: nextDirection ? column : null,
        direction: nextDirection,
      });
    } else {
      // Start new sort (ascending)
      setSortState({ column, direction: 'asc' });
    }
  };

  const exampleCVEs = [
    { id: 'CVE-2024-1234', name: 'Log4j RCE' },
    { id: 'CVE-2021-44228', name: 'Apache Log4Shell' },
    { id: 'CVE-2023-26360', name: 'Adobe ColdFusion' },
    { id: 'CVE-2024-0519', name: 'Critical Vulnerability' },
  ];

  const handleExampleClick = (cveId: string) => {
    setSearchInput(cveId);
  };

  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          Search CVEs
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Find CVEs by ID and explore vulnerability details
        </p>
      </div>

      <SearchForm
        onSearch={setSearchInput}
        isLoading={isLoading}
      />

      {/* Example CVEs */}
      <div className="card-luxury space-y-4">
        <div>
          <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold mb-4">
            Try these examples
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {exampleCVEs.map((cve) => (
              <button
                key={cve.id}
                onClick={() => handleExampleClick(cve.id)}
                className="p-3 text-left rounded border border-luxury-border/50 bg-luxury-bg hover:bg-luxury-accent/10 hover:border-luxury-accent/30 transition-all duration-200 group"
              >
                <p className="font-mono text-sm font-semibold text-luxury-accent group-hover:text-luxury-accent-alt">
                  {cve.id}
                </p>
                <p className="text-xs text-luxury-text-secondary mt-1">{cve.name}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {searchInput && (
        <div className="p-4 bg-luxury-bg-subtle border border-luxury-accent/30 rounded-lg text-luxury-text-secondary text-sm space-y-1 shadow-elegant">
          <p className="text-xs tracking-luxury uppercase text-luxury-accent/70">Searching for</p>
          <p className="font-mono font-semibold text-luxury-accent">{searchInput}</p>
        </div>
      )}

      <DataTable
        data={tableData}
        isLoading={isLoading}
        sortState={sortState}
        onSort={handleSort}
      />

      {cveResult && (
        <div className="card-luxury space-y-6">
          <div>
            <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury mb-4">
              CVE Details
            </h2>
          </div>
          <div className="space-y-4 text-sm">
            <div className="space-y-1">
              <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">CNA (Numbering Authority)</p>
              <p className="text-luxury-text">{cveResult.cna ? <span className="text-luxury-accent font-semibold">{cveResult.cna}</span> : <span className="text-luxury-text-secondary italic">Not specified</span>}</p>
            </div>

            <div className="space-y-1">
              <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">Description</p>
              <p className="text-luxury-text leading-relaxed">{cveResult.description}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1 p-3 bg-luxury-bg rounded border border-luxury-border/50">
                <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">CVSS v3.1</p>
                <p className="text-lg font-semibold text-luxury-accent">{cveResult.cvss_v3_1_score}</p>
              </div>
              {cveResult.cvss_v4_0_score && (
                <div className="space-y-1 p-3 bg-luxury-bg rounded border border-luxury-border/50">
                  <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">CVSS v4.0</p>
                  <p className="text-lg font-semibold text-luxury-accent">{cveResult.cvss_v4_0_score}</p>
                </div>
              )}
            </div>

            {cveResult.references && cveResult.references.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-luxury-border">
                <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">References</p>
                <ul className="space-y-2">
                  {cveResult.references.map((ref: string, i: number) => (
                    <li key={i}>
                      <a
                        href={ref}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-luxury-accent hover:text-luxury-accent-alt transition-colors break-all text-xs"
                      >
                        {ref}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {cveResult.attack_profiles && cveResult.attack_profiles.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-luxury-border">
                <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">Cyperf Test Profiles</p>
                <ul className="space-y-1">
                  {cveResult.attack_profiles.map((profile: string, i: number) => (
                    <li key={i} className="text-luxury-text px-2 py-1 bg-luxury-bg rounded border border-luxury-border/50 text-xs">
                      {profile}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="pt-4 border-t border-luxury-border flex gap-3">
              {cveResult.testable ? (
                <button
                  onClick={() => openSidebar('discuss')}
                  className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-semibold rounded transition-colors"
                >
                  Let's Discuss
                </button>
              ) : (
                <button
                  onClick={() => openSidebar('feature_request')}
                  className="px-4 py-2 bg-luxury-bg-subtle hover:bg-luxury-accent/10 border border-luxury-accent/40 text-luxury-accent text-sm font-semibold rounded transition-colors"
                >
                  Request Feature
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {cveResult && (
        <ContactFormSidebar
          isOpen={contactSidebarOpen}
          onClose={() => setContactSidebarOpen(false)}
          cveId={cveResult.id}
          testable={cveResult.testable}
          context={contactContext}
          cvssScore={cveResult.cvss_v3_1_score ?? null}
          attackProfiles={cveResult.attack_profiles}
        />
      )}
    </div>
  );
}
