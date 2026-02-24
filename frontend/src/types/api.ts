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
export interface AiCVEResponse {
  id: string;                        // CVE-XXXX-XXXXX (source CVE)
  description: string;               // AI-generated or source CVE description
  severity: string | null;           // e.g. "HIGH", "CRITICAL" — from ai_cves record
  cvss_score: number | null;         // Optional CVSS score if available
  ai_strike_name: string | null;     // AI-generated strike identifier
  generated_at: string | null;       // ISO 8601 timestamp when AI entry was created
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
