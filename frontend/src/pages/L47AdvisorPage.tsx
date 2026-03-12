/**
 * L47AdvisorPage
 *
 * Two-state page for the L4-7 Test Advisor:
 *   - Form state  (result === null): renders L47ScenarioForm wrapped in a card-luxury panel
 *   - Results state (result !== null): renders ranked recommendation cards (up to 3)
 *
 * Dark luxury-* theme throughout. No light-theme CSS classes.
 */

import React, { useState } from 'react';
import { L47ScenarioForm } from '../components/L47ScenarioForm';
import { type L47RecommendationResponse } from '../hooks/useAPI';

const profileTypeBadge: Record<string, string> = {
  application: 'bg-blue-900/40 text-blue-300 border border-blue-700/40',
  strike: 'bg-red-900/40 text-red-300 border border-red-700/40',
};

export const L47AdvisorPage: React.FC = () => {
  const [result, setResult] = useState<L47RecommendationResponse | null>(null);

  return (
    <div className="space-y-8">
      {/* Page header — always visible */}
      <div className="space-y-2">
        <h1 className="text-4xl font-display font-bold text-luxury-text tracking-luxury">
          L4-7 Test Advisor
        </h1>
        <p className="text-luxury-text-secondary">
          Describe your test scenario to get ranked Cyperf profile recommendations
        </p>
      </div>

      {/* Form state */}
      {result === null && (
        <div className="card-luxury">
          <L47ScenarioForm onSubmit={(data) => setResult(data)} />
        </div>
      )}

      {/* Results state */}
      {result !== null && (
        <div className="space-y-6">
          {result.recommendations.length === 0 ? (
            /* Empty recommendations — render agent message */
            <div className="card-luxury space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-luxury-text-secondary text-sm">Agent response:</span>
              </div>
              <p className="text-luxury-text leading-relaxed">{result.message}</p>
              <button
                onClick={() => setResult(null)}
                className="text-sm text-luxury-text-secondary hover:text-luxury-text underline transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : (
            <>
              {/* Ranked recommendation cards */}
              <div className="space-y-4">
                {result.recommendations.slice(0, 3).map((rec) => (
                  <div key={rec.rank} className="card-luxury flex flex-col gap-3">
                    {/* Card header: rank + profile name + badge */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-baseline gap-3">
                        <span className="text-2xl font-display font-bold text-luxury-accent">
                          #{rec.rank}
                        </span>
                        <span className="text-lg font-semibold text-luxury-text">
                          {rec.profile_name}
                        </span>
                      </div>
                      <span
                        className={`text-xs font-semibold px-2.5 py-1 rounded-full whitespace-nowrap capitalize ${
                          profileTypeBadge[rec.profile_type] ??
                          'bg-luxury-bg-subtle text-luxury-text-secondary border border-luxury-border'
                        }`}
                      >
                        {rec.profile_type}
                      </span>
                    </div>

                    {/* Rationale */}
                    <p className="text-luxury-text-secondary text-sm leading-relaxed">
                      {rec.rationale}
                    </p>
                  </div>
                ))}
              </div>

              {/* Start Over */}
              <div className="flex justify-center pt-2">
                <button
                  onClick={() => setResult(null)}
                  className="text-sm text-luxury-text-secondary hover:text-luxury-text underline transition-colors"
                >
                  Start Over
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
