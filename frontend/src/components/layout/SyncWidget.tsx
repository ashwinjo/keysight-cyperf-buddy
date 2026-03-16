/**
 * SyncWidget — fixed right-side collapsible panel.
 *
 * A small tab sticks out from the right edge of the screen.
 * Clicking it slides the full panel in/out without overlaying the page.
 *
 * Contains: last-sync timestamp, Sync Data button, Settings gear → SettingsPanel modal.
 * Manages its own endpoint + sync state (previously in Navigation).
 */
import { useState, useCallback, useEffect } from 'react';
import { ChevronLeft, Settings } from 'lucide-react';
import axios from 'axios';
import { SyncButton } from './SyncButton';
import { SettingsPanel } from './SettingsPanel';
import { ErrorBoundary } from '../ErrorBoundary';
import { useSyncStatus } from '../../hooks/useAPI';

export function SyncWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [endpoint, setEndpoint] = useState<string | undefined>(undefined);

  const { data: syncStatus } = useSyncStatus();
  const lastSyncAt = syncStatus?.last_successful_sync ?? null;

  const fetchEndpointConfig = useCallback(async () => {
    try {
      const res = await axios.get<{ endpoint: string; is_valid: boolean }>(
        '/admin/config/cyperf-endpoint'
      );
      setEndpoint(res.data.endpoint || undefined);
    } catch (err) {
      console.error('[SyncWidget] Failed to fetch CyPerf endpoint config:', err);
    }
  }, []);

  useEffect(() => {
    void fetchEndpointConfig();
    const interval = setInterval(() => void fetchEndpointConfig(), 30_000);
    return () => clearInterval(interval);
  }, [fetchEndpointConfig]);

  const handleEndpointSaved = (savedEndpoint: string) => {
    setEndpoint(savedEndpoint || undefined);
    setShowSettings(false);
  };

  return (
    <>
      {/* Fixed right-side widget */}
      <div className="fixed right-0 top-1/2 -translate-y-1/2 z-40">
        {/*
          The inner flex container translates as a unit.
          Closed: translated right by PANEL_W → only the 24px tab remains visible.
          Open:   translated to 0 → full panel visible.
        */}
        <div
          className={`flex items-stretch transition-transform duration-300 ease-in-out ${
            isOpen ? 'translate-x-0' : 'translate-x-[220px]'
          }`}
        >
          {/* Tab — always the leftmost element, stays at screen edge when closed */}
          <button
            onClick={() => setIsOpen((v) => !v)}
            aria-label={isOpen ? 'Close sync panel' : 'Open sync panel'}
            className="flex items-center justify-center w-6 min-h-[72px]
              bg-luxury-bg border border-luxury-border border-r-0 rounded-l-md
              text-luxury-text-secondary hover:text-luxury-accent
              transition-colors duration-200 cursor-pointer"
          >
            <ChevronLeft
              className={`h-3.5 w-3.5 transition-transform duration-300 ${isOpen ? '' : 'rotate-180'}`}
              aria-hidden="true"
            />
          </button>

          {/* Panel */}
          <div
            style={{ width: 220 }}
            className="bg-luxury-bg border border-luxury-border border-l-0 rounded-r-md
              p-4 space-y-4 shadow-elegant"
          >
            <p className="text-[10px] font-bold tracking-widest uppercase text-luxury-text-secondary/60 select-none">
              CyPerf Sync
            </p>

            <ErrorBoundary label="SyncWidgetButton">
              <SyncButton
                endpoint={endpoint}
                lastSyncAt={lastSyncAt}
                onSyncComplete={(success) => {
                  if (success) void fetchEndpointConfig();
                }}
              />
            </ErrorBoundary>

            <div className="border-t border-luxury-border/40 pt-3 flex items-center justify-between">
              <span className="text-[10px] text-luxury-text-secondary/60 truncate max-w-[140px]">
                {endpoint ?? 'No endpoint set'}
              </span>
              <button
                onClick={() => setShowSettings(true)}
                aria-label="Open CyPerf endpoint settings"
                title="CyPerf endpoint settings"
                className={`inline-flex items-center justify-center h-7 w-7 rounded-md shrink-0
                  text-luxury-text-secondary hover:text-luxury-text hover:bg-luxury-bg-subtle
                  transition-colors duration-200
                  ${!endpoint ? 'text-luxury-accent' : ''}`}
              >
                <Settings className={`h-4 w-4 ${!endpoint ? 'text-luxury-accent' : ''}`} aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Settings modal — rendered at root level to avoid z-index clipping */}
      <ErrorBoundary label="SyncWidgetSettings" fallback={<div />}>
        <SettingsPanel
          isOpen={showSettings}
          onOpenChange={setShowSettings}
          currentEndpoint={endpoint}
          onEndpointSaved={handleEndpointSaved}
        />
      </ErrorBoundary>
    </>
  );
}
