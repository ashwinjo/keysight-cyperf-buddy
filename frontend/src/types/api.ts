// CVE data structures (match Phase 3 backend responses)
export interface CVEResponse {
  id: string;                      // CVE-XXXX-XXXXX
  cvss_v3_1_score: number;        // 0-10
  cvss_v4_0_score: number | null;
  description: string;
  published_date: string;          // ISO 8601
  references: string[];
  testable: boolean;               // From Cyperf sync
  attack_profile: string | null;
}

export interface BrowseListResponse {
  cves: CVEResponse[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface SyncStatusResponse {
  status: 'success' | 'failed' | 'never' | 'sync_triggered';
  last_successful_sync: string | null;  // ISO 8601, null if never synced
  last_attempted_sync: string | null;
  error_message: string | null;
}

// Table column sorting
export type SortDirection = 'asc' | 'desc' | null;
export interface SortState {
  column: 'cve_id' | 'cvss' | 'published_date' | null;
  direction: SortDirection;
}
