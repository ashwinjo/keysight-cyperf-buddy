/**
 * TypeScript types for Cyperf CVE Tracker API responses.
 *
 * These types mirror the Pydantic models defined in the Phase 3 FastAPI backend.
 * Keep in sync with: backend/app/schemas.py
 *
 * API endpoints:
 *   GET /cve/search?id=CVE-XXXX → CVEResponse
 *   GET /cve/latest              → BrowseListResponse
 *   GET /admin/sync-status       → SyncStatusResponse
 */

// CVE data structures (match Phase 3 backend responses)
export interface CVEResponse {
  id: string;                          // CVE-XXXX-XXXXX
  cvss_v3_1_score: number;            // 0-10
  cvss_v4_0_score: number | null;
  description: string;
  published_date: string;              // ISO 8601
  references: string[];
  cna: string | null;                  // CVE Numbering Authority (CNA)
  testable: boolean;                   // Set by Cyperf sync job (live comparison)
  attack_profiles: string[];           // All Cyperf strike names for this CVE
}

// AI CVE entry from the ai_cves table (Cyperf AI-generated attack variants)
// description, severity, and cvss_score are returned as null by the backend
// until enrichment from a secondary source is implemented. id maps to
// AICve.cve_id (synthetic NoCVE_cyperf<uuid5> identifier, not the uuid4 PK).
export interface AiCVEResponse {
  id: string;                        // NoCVE_cyperf<uuid5> synthetic ID (not a real CVE ID)
  description: string | null;        // Not stored in ai_cves — always null for now
  severity: string | null;           // Not stored in ai_cves — always null for now
  cvss_score: number | null;         // Not stored in ai_cves — always null for now
  ai_strike_name: string | null;     // Cyperf AI strike name (maps to AICve.strike_name)
  generated_at: string | null;       // ISO 8601 timestamp (maps to AICve.created_at)
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

// Table column sorting — used by DataTable and page components
export type SortDirection = 'asc' | 'desc' | null;

export interface SortState {
  column: 'cve_id' | 'cvss' | 'published_date' | null;
  direction: SortDirection;
}

// Contact form types (Phase 4.1 - Sales Funnel)
export type ContactContext = 'discuss' | 'feature_request';

export interface ContactFormRequest {
  first_name: string;
  last_name: string;
  company: string;
  email: string;
  cve_id: string;
  context: ContactContext;
  testable: boolean;
  cvss_score: number | null;
  attack_profiles: string[];
}

export interface ContactFormResponse {
  success: boolean;
  message: string;
  preview: string;
}
