/**
 * WhatIsCyperfPage — static informational page about Keysight Cyperf.
 *
 * No data fetching. Provides context on what Cyperf is, its purpose within
 * the CVE²Strike workflow, and links to official Keysight documentation.
 */
export default function WhatIsCyperfPage() {
  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          What is Cyperf?
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Keysight's cloud-native network security and performance test platform
        </p>
      </div>

      {/* Overview card */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Overview
        </h2>
        <p className="text-luxury-text leading-relaxed">
          Keysight CyPerf is a cloud-native application and security performance testing
          solution designed to emulate real-world attack traffic at scale. It enables
          security teams to validate the effectiveness of firewalls, IDS/IPS, and other
          network security controls against known CVEs and emerging threat vectors.
        </p>
        <p className="text-luxury-text leading-relaxed">
          CyPerf supports multi-cloud deployments (AWS, Azure, GCP) and on-premises
          environments, making it suitable for both lab validation and continuous security
          regression testing in CI/CD pipelines.
        </p>
      </div>

      {/* Key capabilities */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Key Capabilities
        </h2>
        <ul className="space-y-3 text-luxury-text">
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">CVE Strike Testing:</span> Execute realistic
              exploit replays for thousands of CVEs using Cyperf's built-in strike library,
              verifiable against live security infrastructure.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">Application Simulation:</span> Emulate
              thousands of concurrent users and application flows to stress-test network
              capacity alongside security controls.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">AI-Generated CVEs:</span> CyPerf's AI engine
              synthesizes novel attack patterns derived from real CVE data, extending
              test coverage beyond the static strike library.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">Cloud-Native Agents:</span> Deploy lightweight
              test agents as containers or VMs in any cloud or on-premises environment
              with zero hardware requirements.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">REST API Automation:</span> Full REST API
              coverage for orchestrating test runs from CI/CD systems, enabling automated
              security regression in DevSecOps pipelines.
            </span>
          </li>
        </ul>
      </div>

      {/* How it connects to CVE²Strike */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          CyPerf + CVE²Strike
        </h2>
        <p className="text-luxury-text leading-relaxed">
          CVE²Strike queries Keysight CyPerf's strike library in real-time to determine
          which CVEs are currently testable. The sync job polls the CyPerf controller API,
          maps CVE IDs to available strike profiles, and surfaces that testability data
          directly in the search and browse views.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 pt-2">
          <div className="p-4 bg-luxury-bg rounded border border-luxury-border/60 space-y-1">
            <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">Non-AI CVEs</p>
            <p className="text-sm text-luxury-text leading-snug">
              CVEs mapped to static Cyperf strike profiles. Validated, deterministic
              exploit replays.
            </p>
          </div>
          <div className="p-4 bg-luxury-bg rounded border border-luxury-border/60 space-y-1">
            <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">AI CVEs</p>
            <p className="text-sm text-luxury-text leading-snug">
              Synthetically generated attack variants produced by Cyperf's AI engine.
              Extends coverage to CVEs without static strikes.
            </p>
          </div>
          <div className="p-4 bg-luxury-bg rounded border border-luxury-border/60 space-y-1">
            <p className="text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold">NVD Integration</p>
            <p className="text-sm text-luxury-text leading-snug">
              Enriches every CVE with CVSS scores, descriptions, and references from
              NIST's National Vulnerability Database.
            </p>
          </div>
        </div>
      </div>

      {/* External links */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Learn More
        </h2>
        <ul className="space-y-3">
          <li>
            <a
              href="https://www.keysight.com/us/en/products/network-test/protocol-load-test/keysight-cyperf.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-luxury-accent hover:text-luxury-accent-alt transition-colors text-sm font-semibold"
            >
              Keysight CyPerf Product Page →
            </a>
          </li>
          <li>
            <a
              href="https://support.keysight.com/s/cyperf"
              target="_blank"
              rel="noopener noreferrer"
              className="text-luxury-accent hover:text-luxury-accent-alt transition-colors text-sm font-semibold"
            >
              CyPerf Support & Documentation →
            </a>
          </li>
          <li>
            <a
              href="https://www.keysight.com/us/en/home.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-luxury-accent hover:text-luxury-accent-alt transition-colors text-sm font-semibold"
            >
              Keysight Technologies →
            </a>
          </li>
        </ul>
      </div>
    </div>
  );
}
