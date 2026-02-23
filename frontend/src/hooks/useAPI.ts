import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { CVEResponse, SyncStatusResponse, BrowseListResponse } from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Hook 1: Fetch single CVE by ID
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
    staleTime: 1000 * 60 * 5,  // 5 minutes
  });
};

// Hook 2: Fetch paginated latest CVEs
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

// Hook 3: Fetch sync status for footer/warning
export const useSyncStatus = () => {
  return useQuery({
    queryKey: ['sync', 'status'],
    queryFn: async () => {
      const res = await axios.get<SyncStatusResponse>(`${API_BASE}/admin/sync-status`);
      return res.data;
    },
    staleTime: 1000 * 60,           // 1 minute (frequently updated)
    refetchInterval: 1000 * 60 * 5, // Refetch every 5 minutes
  });
};
