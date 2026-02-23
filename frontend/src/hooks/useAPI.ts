/**
 * Custom React Query hooks for Cyperf CVE Tracker API calls.
 *
 * All hooks use @tanstack/react-query for caching, deduplication, and
 * background refetch. API base URL is configurable via VITE_API_URL env var
 * (defaults to http://localhost:8000 for local development).
 *
 * Hooks:
 *   useSearchCVE    - Fetch single CVE by ID (GET /cve/search?id=...)
 *   useLatestCVEs   - Paginated CVE browse (GET /cve/latest)
 *   useSyncStatus   - Cyperf sync timestamp (GET /admin/sync-status)
 */
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { CVEResponse, SyncStatusResponse, BrowseListResponse } from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Hook 1: Fetch single CVE by ID
// Only fires when cveId is non-null (enabled: !!cveId)
export const useSearchCVE = (cveId: string | null) => {
  return useQuery({
    queryKey: ['cve', 'search', cveId],
    queryFn: async () => {
      const res = await axios.get<CVEResponse>(`${API_BASE}/cve/search`, {
        params: { id: cveId }
      });
      return res.data;
    },
    enabled: !!cveId,
    staleTime: 1000 * 60 * 5,  // 5 minutes — CVE data is stable
  });
};

// Hook 2: Fetch paginated latest CVEs
// Supports testability filter for Browse page "Show testable only" toggle
export const useLatestCVEs = (page = 1, pageSize = 25, onlyTestable = false) => {
  return useQuery({
    queryKey: ['cve', 'latest', page, pageSize, onlyTestable],
    queryFn: async () => {
      const res = await axios.get<BrowseListResponse>(`${API_BASE}/cve/latest`, {
        params: { page, page_size: pageSize, only_testable: onlyTestable }
      });
      return res.data;
    },
    staleTime: 1000 * 60 * 5,  // 5 minutes
  });
};

// Hook 3: Fetch sync status for StatusBar footer and StaleDataWarning banner
// Short staleTime + auto-refetch to keep warning banner accurate
export const useSyncStatus = () => {
  return useQuery({
    queryKey: ['sync', 'status'],
    queryFn: async () => {
      const res = await axios.get<SyncStatusResponse>(`${API_BASE}/admin/sync-status`);
      return res.data;
    },
    staleTime: 1000 * 60,           // 1 minute (sync status changes frequently)
    refetchInterval: 1000 * 60 * 5, // Auto-refetch every 5 minutes
  });
};
