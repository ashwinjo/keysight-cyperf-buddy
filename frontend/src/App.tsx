import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import SearchPage from "./pages/SearchPage";
import BrowsePage from "./pages/BrowsePage";
import BatchPage from "./pages/BatchPage";

export default function App(): React.ReactNode {
  return (
    <Router>
      <div className="min-h-screen bg-dark-900">
        <nav className="border-b border-gray-700 bg-dark-950 p-4">
          <div className="mx-auto flex gap-6">
            <a href="/" className="text-white hover:text-gray-300">
              Search
            </a>
            <a href="/browse" className="text-white hover:text-gray-300">
              Browse
            </a>
            <a href="/batch" className="text-white hover:text-gray-300">
              Batch
            </a>
          </div>
        </nav>
        <main className="mx-auto max-w-7xl p-6">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/browse" element={<BrowsePage />} />
            <Route path="/batch" element={<BatchPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
