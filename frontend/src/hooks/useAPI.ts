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
import { CVEResponse, SyncStatusResponse, BrowseListResponse, AiCVEResponse } from '../types/api';

// Use /api proxy (configured in vite.config.ts to proxy to http://localhost:8000)
// This avoids CORS issues when running in the browser
const API_BASE = '/api';

// Hook 1: Fetch single CVE by ID
// Only fires when cveId is non-null (enabled: !!cveId)
export const useSearchCVE = (cveId: string | null) => {
  return useQuery({
    queryKey: ['cve', 'search', cveId],
    queryFn: async () => {
      const res = await axios.get<any>(`${API_BASE}/cve/search`, {
        params: { id: cveId }
      });
      // Backend returns { results: [...], total, query, search_type }
      // Extract the first result and normalize field names
      if (res.data.results && res.data.results.length > 0) {
        const backendCve = res.data.results[0];
        return {
          id: backendCve.id,
          cvss_v3_1_score: backendCve.cvss_v3_score,
          cvss_v4_0_score: backendCve.cvss_v4_score,
          description: backendCve.description,
          published_date: backendCve.published_date,
          references: backendCve.reference_urls || [],
          cna: backendCve.cna,
          testable: backendCve.testable,
          attack_profiles: backendCve.attack_profiles || [],
        };
      }
      return null;
    },
    enabled: !!cveId,
    staleTime: 1000 * 60 * 5,  // 5 minutes — CVE data is stable
  });
};

// Hook 2: Fetch paginated latest CVEs with Cyperf strike data
// Loads all CVEs from database with testability status based on Cyperf strikes
export const useLatestCVEs = (page = 1, pageSize = 25) => {
  return useQuery({
    queryKey: ['cve', 'latest', page, pageSize],
    queryFn: async () => {
      const res = await axios.get<any>(`${API_BASE}/cve/latest`, {
        params: { page, limit: pageSize }
      });
      // Backend returns results array directly with CVEDetail objects
      // Each CVEDetail includes testable flag and attack_profiles from database
      const normalizedCves = (res.data.results || []).map((backendCve: any) => ({
        id: backendCve.id,
        cvss_v3_1_score: backendCve.cvss_v3_score,
        cvss_v4_0_score: backendCve.cvss_v4_score,
        description: backendCve.description,
        published_date: backendCve.published_date,
        references: backendCve.reference_urls || [],
        cna: backendCve.cna,
        testable: backendCve.testable || false,
        attack_profiles: backendCve.attack_profiles || [],
      }));
      return {
        cves: normalizedCves,
        total: res.data.total,
        page: res.data.page,
        page_size: res.data.page_size,
        has_next: false, // Backend doesn't return has_next currently
      };
    },
    staleTime: 1000 * 60 * 5,  // 5 minutes
  });
};

// Hook 3: Fetch AI-generated strikes from the ai_cves table
// Returns only AI strikes (those with URL references and <3 refs).
// Filters to only AI-type strikes, excluding other non-CVE entities.
// Fetches up to 10000 records per API limit.
// Endpoint may not yet be implemented — axios will throw a 404/500 which react-query
// surfaces as an error state.
export const useAiCVEs = () => {
  return useQuery({
    queryKey: ['cve', 'ai-cves'],
    queryFn: async () => {
      const res = await axios.get<{ results: AiCVEResponse[]; total: number }>(
        `${API_BASE}/ai-cves`,
        {
          params: {
            limit: 10000,  // Backend max limit
            ai_only: true, // Filter to only AI strikes with URL refs
          },
        }
      );
      return res.data.results || [];
    },
    staleTime: 1000 * 60 * 5,  // 5 minutes
    retry: 1,                   // Single retry — surface errors fast if endpoint absent
  });
};

// Hook 4: Fetch sync status for StatusBar footer and StaleDataWarning banner
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

// Hook 5: Fetch Cyperf application types
export const useCyperfApplicationTypes = () => {
  return useQuery({
    queryKey: ['cyperf', 'application-types'],
    queryFn: async () => {
      const res = await axios.get<{ results: Array<{ id: string; name: string; description?: string }>; total: number }>(
        `${API_BASE}/cyperf-applications/types`
      );
      return res.data.results || [];
    },
    staleTime: 1000 * 60 * 5,  // 5 minutes
  });
};

// Hook 6: Fetch Cyperf applications
export const useCyperfApplications = () => {
  return useQuery({
    queryKey: ['cyperf', 'applications'],
    queryFn: async () => {
      const res = await axios.get<{ results: Array<{ id: string; name: string; description?: string }>; total: number }>(
        `${API_BASE}/cyperf-applications`
      );
      return res.data.results || [];
    },
    staleTime: 1000 * 60 * 5,  // 5 minutes
  });
};
