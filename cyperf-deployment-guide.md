# Getting Started with Keysight CyPerf
> **Release 7.0** · First-Time Deployment Guide

Welcome to CyPerf. This guide walks you through everything you need to get your environment up and running — in plain language, no assumptions, no jargon overload.

---

## What Is CyPerf?

CyPerf is a software-based network test platform that simulates real-world traffic — including attacks, encrypted sessions, and application traffic — so you can stress-test your network devices and security infrastructure before they face the real thing.

Think of it as a **traffic generation engine you control entirely through a browser**.

---

## How CyPerf Is Structured

Before you deploy anything, understand the three moving parts:

| Component | What It Does | Where It Lives |
|---|---|---|
| **Controller** | Web UI — your command center for building and running tests | On-prem VM or cloud |
| **Traffic Agent** | The engine that actually generates test traffic | On-prem VM, cloud, or bare metal |
| **Controller Proxy** | A bridge for hybrid setups where agents and controller are in different networks | On-prem VM or cloud |

> **First time?** You need at minimum a **Controller** and at least **two Agents** (one client-side, one server-side).

---

## Step 1: Choose Your Deployment Path

CyPerf runs on multiple platforms. Pick the one that matches your environment:

| Your Environment | Deployment Method |
|---|---|
| VMware ESXi | OVA (recommended for on-prem) |
| KVM / Linux | QCOW2 image |
| AWS / Azure / GCP | Cloud templates (CloudFormation, ARM, Deployment Manager) |
| Kubernetes | Helm / K8s manifests |
| Docker | Container deployment |
| Bare metal Linux | COTS `.deb` installer |

---

## Option A: Deploy on VMware (OVA) — Most Common On-Prem Path

### Deploy the Controller

**Hardware requirements (minimum):**
- 8 CPU cores
- 16 GB RAM
- 100 GB SSD (thin provisioned) or 250 GB SSD (thick)
- 1 NIC for management
- ESXi 6.5 or newer

**Steps:**

1. Download the Controller OVA from your Keysight support link.
2. Open your ESXi or vSphere client and deploy the OVA.
3. Before powering on — confirm the management NIC is connected to your network.
4. Power on the VM. It will pull an IP via DHCP by default.
5. Open a browser and navigate to `https://<controller-ip>`.
6. Log in with default credentials:
   - **Username:** `admin`
   - **Password:** `CyPerf&Keysight#1`

> **Want a static IP instead of DHCP?**
> Connect to the VM console → log in with the credentials above → run:
> ```
> kcos networking ip set mgmt0 <YOUR_IP>/<PREFIX> <GATEWAY_IP>
> ```
> Example: `kcos networking ip set mgmt0 10.38.166.89/24 10.38.166.1`

---

### Deploy the Traffic Agent

**Hardware requirements (minimum):**
- 4 CPU cores
- 8 GB RAM
- 100 GB SSD
- **2 NICs** — one for management, one for test traffic
- ESXi 6.5 or newer

**Steps:**

1. Download the Agent OVA.
2. In vSphere, create a new VM → select **"Deploy a virtual machine from an OVF or OVA file"**.
3. Name the VM and select your OVA file.
4. Select your datastore.
5. **Network mapping — critical step:**
   - Map `VM Network` → your **management** vSwitch
   - Map `Test_net1` → your **test traffic** vSwitch
6. Choose **Thin** disk provisioning and finish the deployment.
7. Power on the VM.

**After the VM boots — configure networking:**

SSH into the agent:
```
ssh cyperf@<agent-management-ip>
# Password: cyperf
```

Edit `/etc/netplan/01-netcfg.yaml` to set your test interface IP. Example for DHCP on both interfaces:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    ens160:          # management interface
      dhcp4: yes
      dhcp-identifier: mac
      dhcp4-overrides:
        route-metric: 100
    ens33:           # test interface
      dhcp4: yes
      dhcp-identifier: mac
      dhcp4-overrides:
        route-metric: 200
```

> **Key rule:** If management and test are on the same subnet, management MUST have a **lower metric** (100) than test (200).

Apply the config:
```bash
sudo netplan apply
```

---

## Option B: Deploy on KVM (QCOW2)

**Supported host OS:** Ubuntu 22.04 or Ubuntu 24.04

### Prerequisites

Install required packages:
```bash
sudo apt update
sudo apt -y install qemu-kvm libvirt-daemon-system libvirt-clients \
  bridge-utils qemu-guest-agent virt-manager vim cifs-utils
```

Configure bridge networking in `/etc/netplan/` and run `sudo netplan apply`.

### Launch Controller VM

```bash
sudo virt-install \
  --connect qemu:///system \
  --virt-type kvm \
  --name cyperf-controller \
  --ram 16384 \
  --vcpus=8 \
  --osinfo detect=on,require=off \
  --disk path=/var/lib/libvirt/cyperf-mdw.qcow2,format=qcow2 \
  --import \
  --network bridge=br0,model=virtio \
  --noautoconsole
```

### Launch Agent VM

```bash
sudo virt-install \
  --connect qemu:///system \
  --virt-type kvm \
  --name cyperf-agent1 \
  --ram 8192 \
  --vcpus=4 \
  --osinfo detect=on,require=off \
  --disk path=/var/lib/libvirt/cyperf-agent1.qcow2,format=qcow2 \
  --import \
  --network bridge=br0 \
  --network network=default \
  --noautoconsole
```

> **Tip:** If the KVM agent login console doesn't appear, press `Ctrl+Alt+F4` to bring it up.

---

## Option C: Deploy on Bare Metal Linux (COTS Installer)

Use this when you want to run the CyPerf agent on your own physical or virtual Linux server.

**Supported OS:** Debian 12 Server

**Install:**
```bash
sudo apt install /path/to/cyperf-agent-installer.deb
```

That's it. Existing `portmanager` config is preserved if present; otherwise defaults are used.

---

## Step 2: Connect Agents to the Controller

Once your Controller and Agents are both running, you need to point each agent at the controller.

**On each agent, run:**

```bash
# Quickest way — uses default credentials, trusts the controller fingerprint
cyperfagent controller set <CONTROLLER-IP>
```

**With explicit credentials (recommended for production):**
```bash
cyperfagent controller set 10.38.166.147 \
  --username "admin" \
  --password "CyPerf&Keysight#1" \
  --fingerprint "SHA256:dgBd+IKW5GsN8eXec3f/Mm1XRKQmHvfM73gdcZQDdlU"
```

**Or interactively (guided prompts):**
```bash
cyperfagent controller set 10.38.166.147 --interactive
```

**Verify the connection:**
```bash
cyperfagent controller show
```

Once connected, agents appear on the **Agent Management** page in the Controller web UI.

### Useful Agent CLI Commands

| Command | What It Does |
|---|---|
| `cyperfagent controller show` | Show current controller connection |
| `cyperfagent interface management show` | Show current management interface |
| `cyperfagent interface management set ens160` | Set management interface explicitly |
| `cyperfagent interface management set auto` | Auto-detect management interface |
| `cyperfagent interface test set ens160` | Set test interface explicitly |
| `cyperfagent interface test set auto` | Auto-detect test interface |

---

## Step 3: Get Your Controller Fingerprint

The fingerprint is used to securely authenticate agents to your controller.

1. Log into the CyPerf web UI.
2. Go to **Settings → Controller Security → Key Management**.
3. Click the **Copy** button to copy the fingerprint string.
4. Use it in the `--fingerprint` flag when connecting agents.

> **Note:** Clicking **Revoke server fingerprint** generates a new key pair and immediately disconnects all active agents. Use with caution.

---

## Cloud Deployment (AWS / Azure / GCP)

For cloud deployments, Keysight provides ready-to-use templates:

- **AWS:** CloudFormation template
- **Azure:** Resource Manager template
- **GCP:** Deployment Manager template

Each template deploys the Controller Proxy + Agent pair in a new or existing VPC/VNet.

> When deploying in AWS with the Controller Proxy architecture: the Controller (which can be on-prem or in a different region) connects to the **public IP of the Controller Proxy on port 443**, and reaches agents through it. All traffic is encrypted.

### AWS Troubleshooting

**`CREATE_FAILED` error?**
Set **Rollback on failure → No** in the CloudFormation Advanced options. This keeps the stack alive so you can inspect logs at:
- `%ProgramFiles%\Amazon\EC2ConfigService`
- `C:\cfn\log`

> ⚠️ Remember to delete the stack when done troubleshooting — you'll keep incurring charges while it's up.

**Template size limitation error?**
Always launch templates from the URL Keysight provides or from an S3 bucket — not from a local file copy.

---

## Hardware Reference: At a Glance

| Component | CPU | RAM | Storage |
|---|---|---|---|
| Controller | 8 cores | 16 GB | 100 GB SSD (thin) / 250 GB (thick) |
| Agent | 4 cores | 8 GB | 100 GB SSD |
| Controller Proxy | 2 cores | 2 GB | 10 GB SSD |
| License & User Manager | 2 cores | 4 GB | 50 GB SSD |

---

## Updating CyPerf

Updates are handled through the web UI:

1. Download the upgrade package from the Keysight CyPerf Support page.
2. Go to **Settings → Software Updates**.
3. Click **Select packages for upload** → choose your file → click **Open**.
4. Click **Upload** (do not refresh the page during upload).
5. Click **Start update**.

Connected agents are updated automatically if they are running version 4.0 or newer.

> **Important:** Direct upgrade from CyPerf 6.x to 7.0 is **not supported** due to a migration to Debian base images. You'll need to redeploy agents from scratch for 7.0.

---

## Resetting an Agent to Factory Defaults

If something goes wrong and you need a clean slate:

```bash
sudo cyperfagent configuration reset hard
```

Confirm with `yes` when prompted. All agent configuration (controller URL, interface settings) will be wiped.

---

## Troubleshooting Agent Connections

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Connection status: Unauthorized` | Wrong credentials or fingerprint | Re-run `cyperfagent controller set` with correct `--username`, `--password`, `--fingerprint` |
| Controller UI shows "incorrect credentials" banner | Agent repeatedly connecting with bad creds | Fix credentials on the agent side |
| Agent visible in SSH but not in Controller UI | Agent not yet pointed at controller | Run `cyperfagent controller set <ip>` |
| IPv6 address showing instead of IPv4 in UI | Known behavior | Only IPv4 is displayed in Agent Management — this is expected |

---

## Getting Help

| Region | Phone | Hours (Local) |
|---|---|---|
| US / Canada | 1-888-829-5558 | 8:00 – 17:00 |
| Europe | See [support.ixiacom.com](https://support.ixiacom.com) | 8:30 – 17:30 |
| Asia / Pacific | See [support.ixiacom.com](https://support.ixiacom.com) | 8:30 – 17:30 |

**Support portal:** [https://support.ixiacom.com](https://support.ixiacom.com)
**Email:** support@keysight.com

To report a security vulnerability: visit the portal → **Product & Solution Cyber Security → Report an Issue**.

---

*© Keysight Technologies 2020–2025 · CyPerf Release 7.0*
