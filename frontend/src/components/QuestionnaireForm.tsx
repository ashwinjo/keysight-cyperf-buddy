/**
 * QuestionnaireForm Component
 *
 * Form for collecting Cyperf testing requirements and submitting to
 * /api/ashrai/recommend endpoint. Handles conditional field visibility
 * and validation before submission.
 */

import React, { useState } from 'react';
import { useGetRecommendations, type QuestionnaireRequest } from '../hooks/useAPI';
import { Button } from './ui/button';
import { Input } from './ui/input';

interface QuestionnaireFormProps {
  onSubmit?: (response: any) => void;
}

type TestingFocus = 'Application Profile' | 'Security / Attacks' | 'Both';

export const QuestionnaireForm: React.FC<QuestionnaireFormProps> = ({ onSubmit }) => {
  const [testingFocus, setTestingFocus] = useState<TestingFocus>('Application Profile');
  const [applicationMetric, setApplicationMetric] = useState('');
  const [attacksMetric, setAttacksMetric] = useState('');
  const [useCase, setUseCase] = useState('');
  const [needsAutomation, setNeedsAutomation] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const mutation = useGetRecommendations();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setValidationErrors([]);

    // Client-side validation
    const errors: string[] = [];

    if (!useCase.trim() || useCase.trim().length < 5) {
      errors.push('Use case must be at least 5 characters');
    }

    if (testingFocus === 'Application Profile' && !applicationMetric.trim()) {
      errors.push('Application metric is required for Application Profile testing');
    }

    if (testingFocus === 'Security / Attacks' && !attacksMetric.trim()) {
      errors.push('Attacks metric is required for Security / Attacks testing');
    }

    if (testingFocus === 'Both') {
      if (!applicationMetric.trim()) {
        errors.push('Application metric is required');
      }
      if (!attacksMetric.trim()) {
        errors.push('Attacks metric is required');
      }
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    // Build request
    const request: QuestionnaireRequest = {
      testing_focus: testingFocus,
      application_metric: applicationMetric || null,
      attacks_metric: attacksMetric || null,
      use_case: useCase,
      needs_automation: needsAutomation,
    };

    // Submit mutation
    mutation.mutate(request, {
      onSuccess: (data) => {
        onSubmit?.(data);
      },
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl mx-auto">
      {/* Testing Focus */}
      <div className="space-y-3">
        <label className="text-base font-semibold text-gray-700">
          1. Testing Focus <span className="text-red-500">*</span>
        </label>
        <div className="space-y-2">
          {(['Application Profile', 'Security / Attacks', 'Both'] as const).map((option) => (
            <label key={option} className="flex items-center space-x-3 cursor-pointer">
              <input
                type="radio"
                name="testing_focus"
                value={option}
                checked={testingFocus === option}
                onChange={(e) => setTestingFocus(e.target.value as TestingFocus)}
                className="h-4 w-4 text-blue-600"
              />
              <span className="text-gray-700">{option}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Application Metric (conditional) */}
      {(testingFocus === 'Application Profile' || testingFocus === 'Both') && (
        <div className="space-y-2">
          <label htmlFor="app_metric" className="text-base font-semibold text-gray-700">
            2. For Application Testing, What is Your Metric? <span className="text-red-500">*</span>
          </label>
          <Input
            id="app_metric"
            type="text"
            placeholder="e.g., connections per second, requests per second"
            value={applicationMetric}
            onChange={(e) => setApplicationMetric(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
      )}

      {/* Attacks Metric (conditional) */}
      {(testingFocus === 'Security / Attacks' || testingFocus === 'Both') && (
        <div className="space-y-2">
          <label htmlFor="attacks_metric" className="text-base font-semibold text-gray-700">
            {testingFocus === 'Both' ? '3. ' : '2. '}For Attacks / Strikes Testing, What is Your Metric?{' '}
            <span className="text-red-500">*</span>
          </label>
          <Input
            id="attacks_metric"
            type="text"
            placeholder="e.g., attacks per second, packets per second"
            value={attacksMetric}
            onChange={(e) => setAttacksMetric(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
      )}

      {/* Use Case */}
      <div className="space-y-2">
        <label htmlFor="use_case" className="text-base font-semibold text-gray-700">
          {testingFocus === 'Both' ? '4. ' : '3. '}Your Use Case in a Little More Detail{' '}
          <span className="text-red-500">*</span>
        </label>
        <textarea
          id="use_case"
          placeholder="e.g., I want to do stateful video traffic testing for a CDN platform"
          value={useCase}
          onChange={(e) => setUseCase(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md resize-none"
          rows={4}
        />
      </div>

      {/* Automation */}
      <div className="space-y-3">
        <label htmlFor="automation" className="text-base font-semibold text-gray-700">
          {testingFocus === 'Both' ? '5. ' : '4. '}Do You Need Cyperf Automation?{' '}
          <span className="text-red-500">*</span>
        </label>
        <div className="flex items-center space-x-3">
          <input
            id="automation"
            type="checkbox"
            checked={needsAutomation}
            onChange={(e) => setNeedsAutomation(e.target.checked)}
            className="h-4 w-4 text-blue-600 rounded"
          />
          <span className="text-gray-700">Yes, I need test automation</span>
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800 font-semibold text-sm mb-2">Please fix the following:</p>
          <ul className="list-disc list-inside space-y-1">
            {validationErrors.map((error, idx) => (
              <li key={idx} className="text-red-700 text-sm">
                {error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Server Errors */}
      {mutation.error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800 font-semibold text-sm">
            {mutation.error instanceof Error ? mutation.error.message : 'Failed to get recommendations'}
          </p>
        </div>
      )}

      {/* Submit Button */}
      <Button
        type="submit"
        disabled={mutation.isPending}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-md font-semibold"
      >
        {mutation.isPending ? 'Getting Recommendations...' : 'Get Recommendations'}
      </Button>
    </form>
  );
};
