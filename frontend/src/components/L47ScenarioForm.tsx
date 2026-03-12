/**
 * L47ScenarioForm Component
 *
 * 4-field controlled form for the L4-7 Test Advisor.
 * Submits to the Phase 6 agent service via useGetL47Recommendations mutation.
 *
 * Fields:
 *   - testing_focus: select (app_performance | security_attacks | both)
 *   - use_case: textarea (min 10 chars)
 *   - objectives: textarea (min 10 chars)
 *   - timeline: text input (min 5 chars)
 *
 * Dark luxury-* theme throughout. No light-theme CSS classes.
 */

import React, { useState } from 'react';
import {
  useGetL47Recommendations,
  type L47ScenarioRequest,
  type L47RecommendationResponse,
} from '../hooks/useAPI';

interface L47ScenarioFormProps {
  onSubmit: (response: L47RecommendationResponse) => void;
}

type TestingFocus = 'app_performance' | 'security_attacks' | 'both';

export const L47ScenarioForm: React.FC<L47ScenarioFormProps> = ({ onSubmit }) => {
  const [testingFocus, setTestingFocus] = useState<TestingFocus>('app_performance');
  const [useCase, setUseCase] = useState('');
  const [objectives, setObjectives] = useState('');
  const [timeline, setTimeline] = useState('');
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const mutation = useGetL47Recommendations();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setValidationErrors([]);

    const errors: string[] = [];

    if (!useCase.trim() || useCase.trim().length < 10) {
      errors.push('Use case must be at least 10 characters');
    }

    if (!objectives.trim() || objectives.trim().length < 10) {
      errors.push('Objectives must be at least 10 characters');
    }

    if (!timeline.trim() || timeline.trim().length < 5) {
      errors.push('Timeline must be at least 5 characters');
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    const request: L47ScenarioRequest = {
      testing_focus: testingFocus,
      use_case: useCase,
      objectives: objectives,
      timeline: timeline,
    };

    mutation.mutate(request, {
      onSuccess: (data) => {
        onSubmit(data);
      },
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Testing Focus */}
      <div className="space-y-2">
        <label
          htmlFor="testing_focus"
          className="block text-sm font-semibold text-luxury-text tracking-luxury"
        >
          Testing Focus <span className="text-red-400">*</span>
        </label>
        <select
          id="testing_focus"
          value={testingFocus}
          onChange={(e) => setTestingFocus(e.target.value as TestingFocus)}
          className="bg-luxury-bg border border-luxury-border text-luxury-text rounded-md px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-luxury-accent"
        >
          <option value="app_performance">Application Performance</option>
          <option value="security_attacks">Security / Attacks</option>
          <option value="both">Both</option>
        </select>
      </div>

      {/* Use Case */}
      <div className="space-y-2">
        <label
          htmlFor="use_case"
          className="block text-sm font-semibold text-luxury-text tracking-luxury"
        >
          Use Case <span className="text-red-400">*</span>
        </label>
        <textarea
          id="use_case"
          placeholder="e.g., Validate DUT throughput under realistic HTTP/2 video streaming traffic from CDN clients"
          value={useCase}
          onChange={(e) => setUseCase(e.target.value)}
          rows={4}
          className="bg-luxury-bg border border-luxury-border text-luxury-text rounded-md px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-luxury-accent resize-none placeholder:text-luxury-text-secondary/50"
        />
      </div>

      {/* Objectives */}
      <div className="space-y-2">
        <label
          htmlFor="objectives"
          className="block text-sm font-semibold text-luxury-text tracking-luxury"
        >
          Objectives <span className="text-red-400">*</span>
        </label>
        <textarea
          id="objectives"
          placeholder="e.g., Measure max concurrent sessions, validate 99th percentile latency < 50 ms under 10 Gbps load"
          value={objectives}
          onChange={(e) => setObjectives(e.target.value)}
          rows={4}
          className="bg-luxury-bg border border-luxury-border text-luxury-text rounded-md px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-luxury-accent resize-none placeholder:text-luxury-text-secondary/50"
        />
      </div>

      {/* Timeline */}
      <div className="space-y-2">
        <label
          htmlFor="timeline"
          className="block text-sm font-semibold text-luxury-text tracking-luxury"
        >
          Timeline <span className="text-red-400">*</span>
        </label>
        <input
          id="timeline"
          type="text"
          placeholder="e.g., 2-week sprint, end of Q2, before production cutover"
          value={timeline}
          onChange={(e) => setTimeline(e.target.value)}
          className="bg-luxury-bg border border-luxury-border text-luxury-text rounded-md px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-luxury-accent placeholder:text-luxury-text-secondary/50"
        />
      </div>

      {/* Client Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="bg-red-900/30 border border-red-700/40 rounded-md p-4">
          <p className="text-red-300 font-semibold text-sm mb-2">Please fix the following:</p>
          <ul className="list-disc list-inside space-y-1">
            {validationErrors.map((error, idx) => (
              <li key={idx} className="text-red-300 text-sm">
                {error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Server / Mutation Error */}
      {mutation.error && (
        <div className="bg-red-900/30 border border-red-700/40 rounded-md p-4">
          <p className="text-red-300 font-semibold text-sm">
            {mutation.error instanceof Error
              ? String(mutation.error.message)
              : 'Failed to get recommendations'}
          </p>
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="bg-luxury-accent hover:bg-luxury-accent/90 text-white font-semibold px-6 py-2 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full"
      >
        {mutation.isPending ? (
          <span className="flex items-center justify-center gap-2">
            <span
              className="animate-spin rounded-full h-4 w-4 border-2 border-luxury-accent border-t-transparent"
              aria-hidden="true"
            />
            Analyzing scenario...
          </span>
        ) : (
          'Get Recommendations'
        )}
      </button>
    </form>
  );
};
