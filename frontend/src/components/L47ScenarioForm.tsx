/**
 * L47ScenarioForm Component
 *
 * 5-field controlled form for the L4-7 Test Advisor, mirroring the AshRAI
 * questionnaire structure:
 *   - testing_focus: select (Application Profile | Security / Attacks | Both)
 *   - application_metric: text input — shown when testing_focus includes apps
 *   - attacks_metric: text input — shown when testing_focus includes attacks
 *   - use_case: textarea (min 10 chars)
 *   - needs_automation: checkbox
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

type TestingFocus = 'Application Profile' | 'Security / Attacks' | 'Both';

const inputClass =
  'bg-luxury-bg border border-luxury-border text-luxury-text rounded-md px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-luxury-accent placeholder:text-luxury-text-secondary/50';

export const L47ScenarioForm: React.FC<L47ScenarioFormProps> = ({ onSubmit }) => {
  const [testingFocus, setTestingFocus] = useState<TestingFocus>('Application Profile');
  const [applicationMetric, setApplicationMetric] = useState('');
  const [attacksMetric, setAttacksMetric] = useState('');
  const [useCase, setUseCase] = useState('');
  const [needsAutomation, setNeedsAutomation] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const mutation = useGetL47Recommendations();

  const showAppMetric = testingFocus === 'Application Profile' || testingFocus === 'Both';
  const showAttacksMetric = testingFocus === 'Security / Attacks' || testingFocus === 'Both';

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setValidationErrors([]);

    const errors: string[] = [];

    if (showAppMetric && !applicationMetric.trim()) {
      errors.push('Application metric is required for Application Profile testing');
    }
    if (showAttacksMetric && !attacksMetric.trim()) {
      errors.push('Attacks metric is required for Security / Attacks testing');
    }
    if (!useCase.trim() || useCase.trim().length < 10) {
      errors.push('Use case must be at least 10 characters');
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    const request: L47ScenarioRequest = {
      testing_focus: testingFocus,
      use_case: useCase,
      needs_automation: needsAutomation,
      ...(showAppMetric && { application_metric: applicationMetric }),
      ...(showAttacksMetric && { attacks_metric: attacksMetric }),
    };

    mutation.mutate(request, { onSuccess: (data) => onSubmit(data) });
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
          onChange={(e) => {
            setTestingFocus(e.target.value as TestingFocus);
            setValidationErrors([]);
          }}
          className={inputClass}
        >
          <option value="Application Profile">Application Profile</option>
          <option value="Security / Attacks">Security / Attacks</option>
          <option value="Both">Both</option>
        </select>
      </div>

      {/* Application Metric — conditional */}
      {showAppMetric && (
        <div className="space-y-2">
          <label
            htmlFor="application_metric"
            className="block text-sm font-semibold text-luxury-text tracking-luxury"
          >
            Application Metric <span className="text-red-400">*</span>
          </label>
          <input
            id="application_metric"
            type="text"
            placeholder="e.g., throughput, concurrent sessions, latency"
            value={applicationMetric}
            onChange={(e) => setApplicationMetric(e.target.value)}
            className={inputClass}
          />
        </div>
      )}

      {/* Attacks Metric — conditional */}
      {showAttacksMetric && (
        <div className="space-y-2">
          <label
            htmlFor="attacks_metric"
            className="block text-sm font-semibold text-luxury-text tracking-luxury"
          >
            Attacks Metric <span className="text-red-400">*</span>
          </label>
          <input
            id="attacks_metric"
            type="text"
            placeholder="e.g., attack throughput, DDoS packets per second, CVE coverage"
            value={attacksMetric}
            onChange={(e) => setAttacksMetric(e.target.value)}
            className={inputClass}
          />
        </div>
      )}

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
          className={`${inputClass} resize-none`}
        />
      </div>

      {/* Needs Automation */}
      <div className="flex items-center gap-3">
        <input
          id="needs_automation"
          type="checkbox"
          checked={needsAutomation}
          onChange={(e) => setNeedsAutomation(e.target.checked)}
          className="h-4 w-4 rounded border-luxury-border bg-luxury-bg accent-luxury-accent cursor-pointer"
        />
        <label
          htmlFor="needs_automation"
          className="text-sm font-semibold text-luxury-text tracking-luxury cursor-pointer"
        >
          I need automation support for this test workflow
        </label>
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
              className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"
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
