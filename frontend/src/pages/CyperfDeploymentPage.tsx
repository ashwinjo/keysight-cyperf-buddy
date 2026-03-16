/**
 * CyperfDeploymentPage — First-time deployment guide for Keysight CyPerf Release 7.0.
 *
 * Covers architecture overview, VMware/KVM/bare-metal deployment paths,
 * agent connection steps, hardware requirements, update procedures,
 * and troubleshooting reference.
 */
export default function CyperfDeploymentPage() {
  return (
    <div className="space-y-8 animate-in">

      {/* Hero */}
      <div>
        <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
          CyPerf Deployment Guide
        </h1>
        <p className="text-luxury-text-secondary tracking-tight">
          Release 7.0 · First-time deployment reference — on-prem (VMware / KVM / bare metal) and cloud (AWS / Azure / GCP)
        </p>
      </div>

      {/* What is CyPerf — quick framing */}
      <div className="card-luxury space-y-3">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">What Is CyPerf?</h2>
        <p className="text-luxury-text leading-relaxed">
          CyPerf is a software-based network test platform that simulates real-world traffic — including attacks,
          encrypted sessions, and application traffic — so you can stress-test network devices and security
          infrastructure before they face the real thing.
        </p>
        <p className="text-luxury-text-secondary text-sm">
          Think of it as a <span className="text-luxury-accent font-semibold">traffic generation engine you control entirely through a browser</span>.
        </p>
      </div>

      {/* Architecture: three components */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">Architecture: Three Moving Parts</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              icon: '🖥️',
              title: 'Controller',
              desc: 'Web UI — your command center for building and running tests.',
              where: 'On-prem VM or cloud',
            },
            {
              icon: '⚡',
              title: 'Traffic Agent',
              desc: 'The engine that actually generates test traffic.',
              where: 'On-prem VM, cloud, or bare metal',
            },
            {
              icon: '🔗',
              title: 'Controller Proxy',
              desc: 'A bridge for hybrid setups where agents and controller are in different networks.',
              where: 'On-prem VM or cloud',
            },
          ].map(({ icon, title, desc, where }) => (
            <div
              key={title}
              className="border border-luxury-border rounded-md p-4 space-y-2 hover:border-luxury-accent/40 transition-colors"
            >
              <div className="text-2xl">{icon}</div>
              <h3 className="font-semibold text-luxury-text">{title}</h3>
              <p className="text-sm text-luxury-text-secondary">{desc}</p>
              <p className="text-xs text-luxury-accent font-medium">{where}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-luxury-text-secondary border-l-2 border-luxury-accent/30 pl-3">
          First time? You need at minimum a <strong className="text-luxury-text">Controller</strong> and at least{' '}
          <strong className="text-luxury-text">two Agents</strong> — one client-side, one server-side.
        </p>
      </div>

      {/* Deployment paths overview */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">Step 1: Choose Your Deployment Path</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-luxury-border">
                <th className="text-left py-2 pr-6 text-luxury-text-secondary font-semibold tracking-luxury">Environment</th>
                <th className="text-left py-2 text-luxury-text-secondary font-semibold tracking-luxury">Deployment Method</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-luxury-border/40">
              {[
                ['VMware ESXi', 'OVA (recommended for on-prem)'],
                ['KVM / Linux', 'QCOW2 image'],
                ['AWS / Azure / GCP', 'Cloud templates (CloudFormation, ARM, Deployment Manager)'],
                ['Kubernetes', 'Helm / K8s manifests'],
                ['Docker', 'Container deployment'],
                ['Bare metal Linux', 'COTS .deb installer'],
              ].map(([env, method]) => (
                <tr key={env} className="hover:bg-luxury-bg-subtle transition-colors">
                  <td className="py-2.5 pr-6 text-luxury-text font-medium">{env}</td>
                  <td className="py-2.5 text-luxury-text-secondary">{method}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Option A: VMware */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Option A: VMware (OVA) — Most Common On-Prem Path
        </h2>

        <div className="space-y-4">
          <h3 className="font-semibold text-luxury-text">Deploy the Controller</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {[
              ['CPU', '8 cores'],
              ['RAM', '16 GB'],
              ['Storage', '100 GB SSD (thin) / 250 GB (thick)'],
              ['NIC', '1 (management)'],
            ].map(([label, val]) => (
              <div key={label} className="border border-luxury-border/60 rounded p-3">
                <div className="text-luxury-text-secondary text-xs mb-1">{label}</div>
                <div className="text-luxury-text font-semibold">{val}</div>
              </div>
            ))}
          </div>

          <ol className="space-y-2 text-sm text-luxury-text list-decimal list-inside">
            <li>Download the Controller OVA from your Keysight support link.</li>
            <li>Deploy the OVA via ESXi or vSphere client.</li>
            <li>Confirm the management NIC is connected before powering on.</li>
            <li>Power on — the VM will pull an IP via DHCP by default.</li>
            <li>Navigate to <code className="text-luxury-accent bg-luxury-bg-subtle px-1 rounded">https://&lt;controller-ip&gt;</code> in your browser.</li>
            <li>
              Log in with defaults:{' '}
              <code className="text-luxury-accent bg-luxury-bg-subtle px-1 rounded">admin</code> /{' '}
              <code className="text-luxury-accent bg-luxury-bg-subtle px-1 rounded">CyPerf&amp;Keysight#1</code>
            </li>
          </ol>

          <div className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-sm space-y-1">
            <p className="font-semibold text-luxury-text">Want a static IP instead of DHCP?</p>
            <p className="text-luxury-text-secondary">Connect to the VM console and run:</p>
            <pre className="text-luxury-accent text-xs mt-1 overflow-x-auto">
              kcos networking ip set mgmt0 &lt;YOUR_IP&gt;/&lt;PREFIX&gt; &lt;GATEWAY_IP&gt;{'\n'}
              # Example:{'\n'}
              kcos networking ip set mgmt0 10.38.166.89/24 10.38.166.1
            </pre>
          </div>
        </div>

        <div className="space-y-4 border-t border-luxury-border/40 pt-4">
          <h3 className="font-semibold text-luxury-text">Deploy the Traffic Agent</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {[
              ['CPU', '4 cores'],
              ['RAM', '8 GB'],
              ['Storage', '100 GB SSD'],
              ['NICs', '2 (management + test)'],
            ].map(([label, val]) => (
              <div key={label} className="border border-luxury-border/60 rounded p-3">
                <div className="text-luxury-text-secondary text-xs mb-1">{label}</div>
                <div className="text-luxury-text font-semibold">{val}</div>
              </div>
            ))}
          </div>

          <ol className="space-y-2 text-sm text-luxury-text list-decimal list-inside">
            <li>Download the Agent OVA.</li>
            <li>In vSphere: Deploy OVF/OVA → name the VM and select your OVA.</li>
            <li>Select your datastore.</li>
            <li>
              <strong>Network mapping (critical):</strong>
              <ul className="mt-1 ml-4 space-y-1 text-luxury-text-secondary list-disc">
                <li><code className="text-luxury-accent bg-luxury-bg-subtle px-1 rounded">VM Network</code> → management vSwitch</li>
                <li><code className="text-luxury-accent bg-luxury-bg-subtle px-1 rounded">Test_net1</code> → test traffic vSwitch</li>
              </ul>
            </li>
            <li>Choose Thin disk provisioning and finish deployment.</li>
            <li>Power on.</li>
          </ol>

          <div className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-sm space-y-1">
            <p className="font-semibold text-luxury-text">After boot — configure networking via netplan:</p>
            <p className="text-luxury-text-secondary text-xs">
              SSH in with <code className="text-luxury-accent">cyperf@&lt;agent-ip&gt;</code> (password: <code className="text-luxury-accent">cyperf</code>),
              then edit <code className="text-luxury-accent">/etc/netplan/01-netcfg.yaml</code>.
            </p>
            <p className="text-xs text-amber-400/80 mt-2">
              Key rule: if management and test are on the same subnet, management MUST have a lower metric (100) than test (200).
            </p>
          </div>
        </div>
      </div>

      {/* Option B: KVM */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Option B: KVM (QCOW2)
        </h2>
        <p className="text-sm text-luxury-text-secondary">
          Supported host OS: <strong className="text-luxury-text">Ubuntu 22.04 or Ubuntu 24.04</strong>
        </p>

        <div className="space-y-2">
          <p className="text-sm text-luxury-text font-semibold">1. Install prerequisites:</p>
          <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
{`sudo apt update
sudo apt -y install qemu-kvm libvirt-daemon-system libvirt-clients \\
  bridge-utils qemu-guest-agent virt-manager vim cifs-utils`}
          </pre>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-luxury-text font-semibold">2. Launch Controller VM:</p>
          <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
{`sudo virt-install \\
  --connect qemu:///system --virt-type kvm \\
  --name cyperf-controller --ram 16384 --vcpus=8 \\
  --osinfo detect=on,require=off \\
  --disk path=/var/lib/libvirt/cyperf-mdw.qcow2,format=qcow2 \\
  --import --network bridge=br0,model=virtio --noautoconsole`}
          </pre>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-luxury-text font-semibold">3. Launch Agent VM:</p>
          <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
{`sudo virt-install \\
  --connect qemu:///system --virt-type kvm \\
  --name cyperf-agent1 --ram 8192 --vcpus=4 \\
  --osinfo detect=on,require=off \\
  --disk path=/var/lib/libvirt/cyperf-agent1.qcow2,format=qcow2 \\
  --import --network bridge=br0 --network network=default --noautoconsole`}
          </pre>
          <p className="text-xs text-luxury-text-secondary">
            Tip: if the KVM agent login console doesn't appear, press <kbd className="bg-luxury-border px-1 rounded text-luxury-text">Ctrl+Alt+F4</kbd>.
          </p>
        </div>
      </div>

      {/* Option C: Bare Metal */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Option C: Bare Metal Linux (COTS Installer)
        </h2>
        <p className="text-sm text-luxury-text-secondary">
          Supported OS: <strong className="text-luxury-text">Debian 12 Server</strong>
        </p>
        <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
          sudo apt install /path/to/cyperf-agent-installer.deb
        </pre>
        <p className="text-sm text-luxury-text-secondary">
          Existing <code className="text-luxury-accent">portmanager</code> config is preserved if present; otherwise defaults are used.
        </p>
      </div>

      {/* Step 2: Connect agents */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Step 2: Connect Agents to the Controller
        </h2>

        <div className="space-y-3">
          <div className="space-y-1">
            <p className="text-sm text-luxury-text font-semibold">Quickest (trusts fingerprint):</p>
            <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
              cyperfagent controller set &lt;CONTROLLER-IP&gt;
            </pre>
          </div>

          <div className="space-y-1">
            <p className="text-sm text-luxury-text font-semibold">Recommended (explicit credentials + fingerprint):</p>
            <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
{`cyperfagent controller set 10.38.166.147 \\
  --username "admin" \\
  --password "CyPerf&Keysight#1" \\
  --fingerprint "SHA256:dgBd+IKW5GsN8eXec3f/Mm1XRKQmHvfM73gdcZQDdlU"`}
            </pre>
          </div>

          <div className="space-y-1">
            <p className="text-sm text-luxury-text font-semibold">Interactive (guided prompts):</p>
            <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
              cyperfagent controller set 10.38.166.147 --interactive
            </pre>
          </div>

          <div className="space-y-1">
            <p className="text-sm text-luxury-text font-semibold">Verify connection:</p>
            <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
              cyperfagent controller show
            </pre>
          </div>
        </div>

        <div className="overflow-x-auto">
          <p className="text-sm font-semibold text-luxury-text mb-2">Useful agent CLI commands:</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-luxury-border">
                <th className="text-left py-2 pr-6 text-luxury-text-secondary font-semibold tracking-luxury">Command</th>
                <th className="text-left py-2 text-luxury-text-secondary font-semibold tracking-luxury">What It Does</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-luxury-border/40 text-xs">
              {[
                ['cyperfagent controller show', 'Show current controller connection'],
                ['cyperfagent interface management show', 'Show current management interface'],
                ['cyperfagent interface management set ens160', 'Set management interface explicitly'],
                ['cyperfagent interface management set auto', 'Auto-detect management interface'],
                ['cyperfagent interface test set ens160', 'Set test interface explicitly'],
                ['cyperfagent interface test set auto', 'Auto-detect test interface'],
              ].map(([cmd, desc]) => (
                <tr key={cmd} className="hover:bg-luxury-bg-subtle transition-colors">
                  <td className="py-2 pr-6 font-mono text-luxury-accent">{cmd}</td>
                  <td className="py-2 text-luxury-text-secondary">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Step 3: Fingerprint */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Step 3: Get Your Controller Fingerprint
        </h2>
        <ol className="space-y-2 text-sm text-luxury-text list-decimal list-inside">
          <li>Log into the CyPerf web UI.</li>
          <li>Go to <strong>Settings → Controller Security → Key Management</strong>.</li>
          <li>Click <strong>Copy</strong> to copy the fingerprint string.</li>
          <li>Use it in the <code className="text-luxury-accent bg-luxury-bg-subtle px-1 rounded">--fingerprint</code> flag when connecting agents.</li>
        </ol>
        <p className="text-xs text-amber-400/80 border-l-2 border-amber-400/30 pl-3">
          Clicking <strong>Revoke server fingerprint</strong> generates a new key pair and immediately disconnects all active agents.
        </p>
      </div>

      {/* Hardware reference */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">Hardware Reference</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-luxury-border">
                {['Component', 'CPU', 'RAM', 'Storage'].map((h) => (
                  <th key={h} className="text-left py-2 pr-6 text-luxury-text-secondary font-semibold tracking-luxury">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-luxury-border/40">
              {[
                ['Controller', '8 cores', '16 GB', '100 GB SSD (thin) / 250 GB (thick)'],
                ['Agent', '4 cores', '8 GB', '100 GB SSD'],
                ['Controller Proxy', '2 cores', '2 GB', '10 GB SSD'],
                ['License & User Manager', '2 cores', '4 GB', '50 GB SSD'],
              ].map(([comp, cpu, ram, storage]) => (
                <tr key={comp} className="hover:bg-luxury-bg-subtle transition-colors">
                  <td className="py-2.5 pr-6 text-luxury-text font-medium">{comp}</td>
                  <td className="py-2.5 pr-6 text-luxury-text-secondary">{cpu}</td>
                  <td className="py-2.5 pr-6 text-luxury-text-secondary">{ram}</td>
                  <td className="py-2.5 text-luxury-text-secondary">{storage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Updating CyPerf */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">Updating CyPerf</h2>
        <ol className="space-y-2 text-sm text-luxury-text list-decimal list-inside">
          <li>Download the upgrade package from the Keysight CyPerf Support page.</li>
          <li>Go to <strong>Settings → Software Updates</strong>.</li>
          <li>Click <strong>Select packages for upload</strong> → choose your file → <strong>Open</strong>.</li>
          <li>Click <strong>Upload</strong> (do not refresh the page during upload).</li>
          <li>Click <strong>Start update</strong>.</li>
        </ol>
        <p className="text-xs text-amber-400/80 border-l-2 border-amber-400/30 pl-3">
          Direct upgrade from CyPerf 6.x to 7.0 is <strong>not supported</strong> — agents must be redeployed from scratch for 7.0 (Debian base image migration).
        </p>
      </div>

      {/* Factory reset */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">Resetting an Agent to Factory Defaults</h2>
        <pre className="bg-luxury-bg-subtle border border-luxury-border/60 rounded p-3 text-xs text-luxury-accent overflow-x-auto">
          sudo cyperfagent configuration reset hard
        </pre>
        <p className="text-sm text-luxury-text-secondary">
          Confirm with <code className="text-luxury-accent">yes</code> when prompted. All agent configuration (controller URL, interface settings) will be wiped.
        </p>
      </div>

      {/* Troubleshooting */}
      <div className="card-luxury space-y-5">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">Troubleshooting Agent Connections</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-luxury-border">
                {['Symptom', 'Likely Cause', 'Fix'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-luxury-text-secondary font-semibold tracking-luxury">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-luxury-border/40">
              {[
                [
                  'Connection status: Unauthorized',
                  'Wrong credentials or fingerprint',
                  'Re-run cyperfagent controller set with correct --username, --password, --fingerprint',
                ],
                [
                  'Controller UI shows "incorrect credentials" banner',
                  'Agent repeatedly connecting with bad creds',
                  'Fix credentials on the agent side',
                ],
                [
                  'Agent visible in SSH but not in Controller UI',
                  'Agent not yet pointed at controller',
                  'Run cyperfagent controller set <ip>',
                ],
                [
                  'IPv6 address showing instead of IPv4 in UI',
                  'Known behavior',
                  'Only IPv4 is displayed in Agent Management — this is expected',
                ],
              ].map(([symptom, cause, fix]) => (
                <tr key={symptom} className="hover:bg-luxury-bg-subtle transition-colors align-top">
                  <td className="py-2.5 pr-4 text-red-400/80 font-medium">{symptom}</td>
                  <td className="py-2.5 pr-4 text-luxury-text-secondary">{cause}</td>
                  <td className="py-2.5 text-luxury-text-secondary">{fix}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Support */}
      <div className="card-luxury space-y-3">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">Getting Help</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <p className="font-semibold text-luxury-text">Support channels</p>
            <ul className="space-y-1 text-luxury-text-secondary">
              <li>US / Canada: <span className="text-luxury-text">1-888-829-5558</span> (8:00–17:00)</li>
              <li>Europe / APAC: support.ixiacom.com</li>
              <li>Email: <span className="text-luxury-text">support@keysight.com</span></li>
            </ul>
          </div>
          <div className="space-y-2">
            <p className="font-semibold text-luxury-text">Security vulnerabilities</p>
            <p className="text-luxury-text-secondary">
              Visit support portal → <strong>Product &amp; Solution Cyber Security → Report an Issue</strong>
            </p>
          </div>
        </div>
        <p className="text-xs text-luxury-text-secondary border-t border-luxury-border/40 pt-3">
          © Keysight Technologies 2020–2025 · CyPerf Release 7.0
        </p>
      </div>

    </div>
  );
}
