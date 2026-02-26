/**
 * WhatIsCyperfPage — comprehensive guide to Keysight CyPerf.
 *
 * Customer-focused overview with use cases, deployment options, and resource links.
 * Designed to inform potential buyers and practitioners about CyPerf's capabilities
 * in application performance, security testing, and network validation.
 */
export default function WhatIsCyperfPage() {
  return (
    <div className="space-y-8 animate-in">
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          What is Keysight CyPerf?
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Cloud-native application and security test solution that validates performance and security efficacy across hybrid and multi-cloud networks
        </p>
      </div>

      {/* Getting Started & Resources - Prominent CTA Section at Top */}
      <div className="space-y-6">
        <div className="text-center space-y-3 pb-4 border-b border-luxury-border">
          <h2 className="text-3xl font-display font-bold text-luxury-accent tracking-luxury">
            Ready to Get Started?
          </h2>
          <p className="text-luxury-text-secondary text-lg">
            Explore official resources, deployment options, and pre-built configurations
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Official Resources Card */}
          <div className="card-luxury border-2 border-luxury-accent/30 hover:border-luxury-accent transition-all p-6 space-y-4">
            <div className="space-y-2">
              <h3 className="text-2xl font-display font-bold text-luxury-accent tracking-luxury">
                📚 Official Resources
              </h3>
              <p className="text-sm text-luxury-text-secondary">
                Start with Keysight's official product information and community edition
              </p>
            </div>
            <ul className="space-y-3">
              <li>
                <a
                  href="https://www.keysight.com/us/en/products/network-test/cloud-test/cyperf.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-luxury-accent hover:text-luxury-accent-alt transition-colors font-semibold text-base block hover:translate-x-1 transition-transform"
                >
                  → CyPerf Official Product Page
                </a>
              </li>
              <li>
                <a
                  href="https://www.cyperf.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-luxury-accent hover:text-luxury-accent-alt transition-colors font-semibold text-base block hover:translate-x-1 transition-transform"
                >
                  → CyPerf Community Edition
                </a>
              </li>
            </ul>
          </div>

          {/* Deployment & Integration Card */}
          <div className="card-luxury border-2 border-luxury-accent/30 hover:border-luxury-accent transition-all p-6 space-y-4">
            <div className="space-y-2">
              <h3 className="text-2xl font-display font-bold text-luxury-accent tracking-luxury">
                🚀 Deployment & Integration
              </h3>
              <p className="text-sm text-luxury-text-secondary">
                Deploy CyPerf and integrate with your infrastructure
              </p>
            </div>
            <ul className="space-y-3">
              <li>
                <a
                  href="https://github.com/Keysight/cyperf/tree/main/deployment"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-luxury-accent hover:text-luxury-accent-alt transition-colors font-semibold text-base block hover:translate-x-1 transition-transform"
                >
                  → CyPerf Deployment Options
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Keysight/cyperf-api-wrapper"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-luxury-accent hover:text-luxury-accent-alt transition-colors font-semibold text-base block hover:translate-x-1 transition-transform"
                >
                  → CyPerf Python SDK
                </a>
              </li>
            </ul>
          </div>

          {/* Performance Benchmarks Card */}
          <div className="card-luxury border-2 border-luxury-accent/30 hover:border-luxury-accent transition-all p-6 space-y-4">
            <div className="space-y-2">
              <h3 className="text-2xl font-display font-bold text-luxury-accent tracking-luxury">
                ⚡ Pre-Built Configurations
              </h3>
              <p className="text-sm text-luxury-text-secondary">
                Leverage tested, ready-to-use performance benchmarks
              </p>
            </div>
            <ul className="space-y-3">
              <li>
                <a
                  href="https://github.com/Keysight/cyperf/tree/main/CyPerf-Performance-Benchmark"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-luxury-accent hover:text-luxury-accent-alt transition-colors font-semibold text-base block hover:translate-x-1 transition-transform"
                >
                  → CyPerf Performance Benchmarks
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Overview card */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Enterprise-Grade Network Testing at Scale
        </h2>
        <p className="text-luxury-text leading-relaxed">
          Keysight CyPerf is a cloud-native application and security test solution that uses lightweight agents to emulate realistic users, applications, and attacks across physical, virtual, and cloud environments. It gives visibility into end-user QoE, performance limits, and security efficacy of modern distributed networks (SD‑WAN, SASE, VPN, WAF, zero trust, etc.).
        </p>
        <p className="text-luxury-text leading-relaxed">
          CyPerf deploys software agents that act as clients and servers, generating authenticated and non‑authenticated application traffic (HTTP/HTTPS, APIs, SaaS, VoIP/video, etc.) plus interleaved attacks at scale—millions of concurrent connections and connections per second, depending on resources. A goal‑seeking algorithm lets you set objectives such as throughput, connections per second, concurrent users, or attacks per second and automatically drive the agents to the true limit of your infrastructure.
        </p>
      </div>

      {/* Core Capabilities */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Core Capabilities
        </h2>
        <ul className="space-y-3 text-luxury-text">
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">Hybrid & Multi-Cloud Support:</span> Test traffic through SD‑WAN, SASE, SSL VPN, IPsec, TLS inspection, load balancers, and WAFs—validate both performance and security impact in realistic topologies.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">Rich KPI Metrics:</span> Application throughput, max concurrency, latency, TLS performance, and threat detection metrics with drill-down per application, attack, and agent.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">Realistic Attack Emulation:</span> Generate OWASP-style attacks, DDoS patterns, exploits, and malware mixed with legitimate traffic to validate security controls.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">Goal-Seeking Algorithm:</span> Automatically drive test agents to the true performance/security limits of your infrastructure without manual adjustment.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">Cloud-Native Deployment:</span> Deploy lightweight test agents as containers or VMs in AWS, Azure, GCP, or on-premises with zero hardware requirements.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-luxury-accent font-bold shrink-0">—</span>
            <span>
              <span className="font-semibold">REST API & SDK:</span> Full automation support via REST APIs and Python SDK for CI/CD integration and DevSecOps workflows.
            </span>
          </li>
        </ul>
      </div>

      {/* Application Performance Use Cases */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Top 5 Application Performance Use Cases
        </h2>
        <div className="space-y-4">
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">SD‑WAN & SASE Performance Benchmarking</h3>
            <p className="text-sm text-luxury-text-secondary">
              Emulate distributed branch users accessing web apps, SaaS, and APIs through SD‑WAN and SASE services. Measure throughput, latency, concurrency, and QoE as policies change. Use dual objectives to find performance degradation break points.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">VPN Gateway & Remote Access Scalability</h3>
            <p className="text-sm text-luxury-text-secondary">
              Spin up tens of thousands of SSL VPN tunnels (AnyConnect, GlobalProtect, etc.) and run app traffic through them. Measure gateway scalability, concurrent tunnels, tunnel setup rate, and per-user performance under rekeying and failover.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">Cloud & Multi‑Cloud Application Benchmarking</h3>
            <p className="text-sm text-luxury-text-secondary">
              Deploy agents across different cloud regions and providers. Benchmark application performance across VPCs, internet gateways, and inter‑cloud links. Measure how instance size, auto‑scaling, and network constructs impact throughput and latency.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">Load Balancer & CDN Capacity Testing</h3>
            <p className="text-sm text-luxury-text-secondary">
              Emulate geographically distributed users hitting load balancers or CDN POPs. Validate SLAs, rate limiting, traffic policing, and measure how different traffic mixes and TLS settings affect POP capacity.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">Web & API Application QoE Validation</h3>
            <p className="text-sm text-luxury-text-secondary">
              Emulate realistic web interactions (browsing, logins, API calls, think time). Measure end-user experience including page load times. Use goal-seeking to determine maximum concurrent users while keeping QoE within acceptable thresholds.
            </p>
          </div>
        </div>
      </div>

      {/* Security Use Cases */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Top 5 Security Use Cases
        </h2>
        <div className="space-y-4">
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">WAF Evaluation with OWASP-Style Attacks</h3>
            <p className="text-sm text-luxury-text-secondary">
              Simulate legitimate web clients plus a mix of OWASP Top 10 attacks to validate WAF performance and security efficacy. Verify that attacks are blocked while good traffic flows with minimal latency impact.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">SASE & Secure Web Gateway Security Testing</h3>
            <p className="text-sm text-luxury-text-secondary">
              Send simultaneous legitimate application traffic and security attacks through SASE solutions or secure web gateways. Validate URL filtering, malware blocking, and data protection at scale. Measure threat detection rates vs. application KPIs.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">Zero Trust & Firewall Policy Validation</h3>
            <p className="text-sm text-luxury-text-secondary">
              Create digital twins of users, apps, and attacks in zero trust architectures. Interleave authenticated user sessions with targeted attacks to confirm that policies block lateral movement and privilege escalation.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">DDoS & Volumetric Attack Resilience</h3>
            <p className="text-sm text-luxury-text-secondary">
              Generate high‑scale traffic including DDoS patterns to stress test firewalls, load balancers, and cloud security controls. Set attack-rate objectives to identify where mitigation starts to fail.
            </p>
          </div>
          <div className="border-l-4 border-luxury-accent/40 pl-4 py-2">
            <h3 className="font-semibold text-luxury-text mb-1">IPS/IDS & Threat Detection Efficacy Testing</h3>
            <p className="text-sm text-luxury-text-secondary">
              Replay exploits, malware, and advanced threats mixed with normal traffic to validate detection and blocking by IPS/IDS systems. Use attack statistics to correlate which threats were detected, blocked, or missed.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}
