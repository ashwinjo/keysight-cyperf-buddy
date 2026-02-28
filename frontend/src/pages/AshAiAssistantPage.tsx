/**
 * AshAI Assistant Page
 *
 * Landing page for the AshRAI Cyperf testing recommendation system.
 * Displays questionnaire form and generated recommendations.
 */

import React, { useState } from 'react';
import { QuestionnaireForm } from '../components/QuestionnaireForm';
import { type RecommendationResponse } from '../hooks/useAPI';

export const AshAiAssistantPage: React.FC = () => {
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [showForm, setShowForm] = useState(true);

  const handleFormSubmit = (response: RecommendationResponse) => {
    setRecommendations(response);
    setShowForm(false);
  };

  const handleReset = () => {
    setRecommendations(null);
    setShowForm(true);
  };

  if (showForm && !recommendations) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white py-12 px-4">
        <div className="max-w-3xl mx-auto space-y-8">
          {/* Header */}
          <div className="text-center space-y-3">
            <h1 className="text-4xl font-bold text-gray-900">AshRAI Testing Assistant</h1>
            <p className="text-lg text-gray-600">
              Get personalized Cyperf testing recommendations based on your use case
            </p>
          </div>

          {/* Form */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <QuestionnaireForm onSubmit={handleFormSubmit} />
          </div>
        </div>
      </div>
    );
  }

  if (recommendations && !showForm) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white py-12 px-4">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Header with Reset */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h1 className="text-3xl font-bold text-gray-900">Your Recommendations</h1>
              <p className="text-gray-600">{recommendations.message}</p>
            </div>
            <button
              onClick={handleReset}
              className="px-4 py-2 text-blue-600 hover:text-blue-700 font-semibold border border-blue-200 rounded-md hover:bg-blue-50"
            >
              Start Over
            </button>
          </div>

          {/* Testing Focus Summary */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <p className="text-sm text-gray-600">Testing Focus:</p>
            <p className="text-2xl font-bold text-blue-900">{recommendations.testing_focus}</p>
          </div>

          {/* Recommendations by Category */}
          <div className="space-y-6">
            {/* High Priority */}
            {recommendations.recommendations.filter((r) => r.priority === 'high').length > 0 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-red-500"></span> High Priority
                </h2>
                <div className="grid gap-4">
                  {recommendations.recommendations
                    .filter((r) => r.priority === 'high')
                    .map((rec, idx) => (
                      <RecommendationCard key={idx} recommendation={rec} />
                    ))}
                </div>
              </div>
            )}

            {/* Medium Priority */}
            {recommendations.recommendations.filter((r) => r.priority === 'medium').length > 0 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-yellow-500"></span> Medium Priority
                </h2>
                <div className="grid gap-4">
                  {recommendations.recommendations
                    .filter((r) => r.priority === 'medium')
                    .map((rec, idx) => (
                      <RecommendationCard key={idx} recommendation={rec} />
                    ))}
                </div>
              </div>
            )}

            {/* Low Priority */}
            {recommendations.recommendations.filter((r) => r.priority === 'low').length > 0 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-gray-400"></span> Low Priority
                </h2>
                <div className="grid gap-4">
                  {recommendations.recommendations
                    .filter((r) => r.priority === 'low')
                    .map((rec, idx) => (
                      <RecommendationCard key={idx} recommendation={rec} />
                    ))}
                </div>
              </div>
            )}
          </div>

          {/* Next Steps */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-6 space-y-4">
            <h2 className="text-xl font-bold text-green-900">Next Steps</h2>
            <ol className="space-y-2">
              {recommendations.next_steps.map((step, idx) => (
                <li key={idx} className="text-green-800">
                  {step}
                </li>
              ))}
            </ol>
          </div>

          {/* Actions */}
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleReset}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md"
            >
              Get Different Recommendations
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

/**
 * Individual recommendation card component
 */
interface RecommendationCardProps {
  recommendation: {
    title: string;
    description: string;
    priority: 'high' | 'medium' | 'low';
    category: 'configuration' | 'metrics' | 'automation' | 'topology' | 'validation';
  };
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({ recommendation }) => {
  const categoryColors: Record<string, string> = {
    configuration: 'bg-purple-100 text-purple-800',
    metrics: 'bg-blue-100 text-blue-800',
    automation: 'bg-green-100 text-green-800',
    topology: 'bg-orange-100 text-orange-800',
    validation: 'bg-indigo-100 text-indigo-800',
  };

  return (
    <div className="border border-gray-200 rounded-lg p-6 bg-white hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-bold text-gray-900 text-lg">{recommendation.title}</h3>
        <span
          className={`text-xs font-semibold px-3 py-1 rounded-full whitespace-nowrap ml-4 ${
            categoryColors[recommendation.category] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {recommendation.category}
        </span>
      </div>
      <p className="text-gray-700">{recommendation.description}</p>
    </div>
  );
};
