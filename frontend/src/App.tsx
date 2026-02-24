import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SearchPage from './pages/SearchPage';
import BrowsePage from './pages/BrowsePage';
import BatchPage from './pages/BatchPage';
import Navigation from './components/layout/Navigation';
import StaleDataWarning from './components/layout/StaleDataWarning';
import StatusBar from './components/layout/StatusBar';

const queryClient = new QueryClient();

export default function App(): React.ReactNode {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="flex flex-col min-h-screen bg-luxury-bg text-luxury-text">
          <Navigation />
          <StaleDataWarning />
          <main className="flex-1 mx-auto max-w-7xl w-full px-8 py-8">
            <Routes>
              <Route path="/" element={<SearchPage />} />
              <Route path="/browse" element={<BrowsePage />} />
              <Route path="/batch" element={<BatchPage />} />
            </Routes>
          </main>
          <StatusBar />
        </div>
      </Router>
    </QueryClientProvider>
  );
}
