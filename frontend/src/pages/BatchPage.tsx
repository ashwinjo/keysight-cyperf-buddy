export default function BatchPage(): React.ReactNode {
  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text tracking-luxury">
          Batch Testing
        </h1>
        <p className="text-luxury-text-secondary tracking-tight mt-2">
          Submit multiple CVEs for batch testability analysis
        </p>
      </div>

      <div className="card-luxury">
        <div className="flex items-center justify-center py-16 text-center">
          <div className="space-y-4">
            <div className="text-5xl mb-4">⏳</div>
            <p className="text-luxury-text-secondary tracking-tight">
              This feature will be available in Phase 5
            </p>
            <p className="text-sm text-luxury-text-secondary/70 tracking-tight">
              You can currently search for CVEs individually or browse the complete database
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
