import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import SearchPage from './pages/SearchPage';
import BrowsePage from './pages/BrowsePage';
import BatchPage from './pages/BatchPage';
import CyperfAiCvesPage from './pages/CyperfAiCvesPage';
import CyperfAppTypesPage from './pages/CyperfAppTypesPage';
import CyperfAppsPage from './pages/CyperfAppsPage';
import WhatIsCyperfPage from './pages/WhatIsCyperfPage';
import Navigation from './components/layout/Navigation';
import StaleDataWarning from './components/layout/StaleDataWarning';
import StatusBar from './components/layout/StatusBar';

const queryClient = new QueryClient();

export default function App(): React.ReactNode {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Toaster
          position="top-right"
          theme="dark"
          richColors
          closeButton
          toastOptions={{
            style: {
              background: 'var(--luxury-bg, #0a0a0a)',
              border: '1px solid var(--luxury-border, #2a2a2a)',
              color: 'var(--luxury-text, #e5e5e5)',
            },
          }}
        />
        <div className="flex flex-col min-h-screen bg-luxury-bg text-luxury-text">
          <Navigation />
          <StaleDataWarning />
          <main className="flex-1 mx-auto max-w-7xl w-full px-8 py-8">
            <Routes>
              <Route path="/" element={<SearchPage />} />
              <Route path="/browse" element={<BrowsePage />} />
              <Route path="/batch" element={<BatchPage />} />
              <Route path="/ai-cves" element={<CyperfAiCvesPage />} />
              <Route path="/cyperf-app-types" element={<CyperfAppTypesPage />} />
              <Route path="/cyperf-apps" element={<CyperfAppsPage />} />
              <Route path="/what-is-cyperf" element={<WhatIsCyperfPage />} />
            </Routes>
          </main>
          <StatusBar />
        </div>
      </Router>
    </QueryClientProvider>
  );
}
