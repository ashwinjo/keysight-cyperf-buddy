/**
 * CyPerf Automation page — quick-start card hub.
 *
 * Five action cards modelled on the IxNetwork Automation 101 layout:
 *   Download, Deploy, Write Tests, Learn, API Reference
 * "VIEW GUIDE" cards expand in place to show sub-links.
 */
import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

// ── Icons ──────────────────────────────────────────────────────────────────
function IconDownload() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0 0l-4-4m4 4l4-4" />
    </svg>
  );
}
function IconDeploy() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
      <polygon strokeLinejoin="round" points="5,3 19,12 5,21" />
    </svg>
  );
}
function IconWriteTests() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
      <polyline strokeLinecap="round" strokeLinejoin="round" points="16,18 22,12 16,6" />
      <polyline strokeLinecap="round" strokeLinejoin="round" points="8,6 2,12 8,18" />
    </svg>
  );
}
function IconLearn() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  );
}
function IconVideo() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
      <rect x="2" y="4" width="15" height="16" rx="2" strokeLinejoin="round" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l5 4-5 4V8z" />
    </svg>
  );
}
function IconAPI() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-6 w-6">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path strokeLinecap="round" d="M3 5v14c0 1.657 4.03 3 9 3s9-1.343 9-3V5" />
      <path strokeLinecap="round" d="M3 12c0 1.657 4.03 3 9 3s9-1.343 9-3" />
    </svg>
  );
}

// ── Card types ─────────────────────────────────────────────────────────────
interface GoCard {
  kind: 'go';
  icon: React.ReactNode;
  title: string;
  description: string;
  href: string;
}

interface GuideCard {
  kind: 'guide';
  icon: React.ReactNode;
  title: string;
  description: string;
  links: { label: string; href: string }[];
}

type Card = GoCard | GuideCard;

const CARDS: Card[] = [
  {
    kind: 'go',
    icon: <IconDownload />,
    title: 'Official Documentation',
    description: 'Get CyPerf & tools',
    href: 'https://www.keysight.com/us/en/products/network-test/cloud-test/cyperf.html',
  },
  {
    kind: 'guide',
    icon: <IconDeploy />,
    title: 'Deploy',
    description: 'Install and configure',
    links: [
      { label: 'Deployment Guide (this portal)', href: '/cyperf-deployment' },
      { label: 'Infrastructure as Code Options', href: 'https://github.com/Keysight/cyperf/tree/main/deployment' },
    ],
  },
  {
    kind: 'go',
    icon: <IconLearn />,
    title: 'Precanned Cyperf Configurations',
    description: 'Explore patterns & use cases',
    href: 'https://github.com/Keysight/cyperf/tree/main/CyPerf-Performance-Benchmark',
  },
  {
    kind: 'guide',
    icon: <IconAPI />,
    title: 'Python API Wrapper SDK',
    description: 'Browse documentation',
    links: [
      { label: 'CyPerf Python SDK (cyperf-api-wrapper)', href: 'https://github.com/Keysight/cyperf-api-wrapper' },
      { label: 'CyPerf REST API — Swagger UI', href: 'https://github.com/Keysight/cyperf' },
    ],
  },
  {
    kind: 'go',
    icon: <IconWriteTests />,
    title: 'Custom Framework',
    description: 'cyperf-restpy community SDK',
    href: 'https://cyperf-restpy.readthedocs.io/en/latest/overview.html',
  },
  {
    kind: 'go',
    icon: <IconVideo />,
    title: 'Video Tutorials',
    description: 'Watch & learn CyPerf',
    href: 'https://www.youtube.com/playlist?list=PLtRQdxmT_472N7Duz2l37HWf7wikIK4Pc',
  },
];

// ── GuideCard component (expandable) ──────────────────────────────────────
function GuideCardView({ card }: { card: GuideCard }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col bg-[#0f1117] border border-[#1e2230] rounded-lg overflow-hidden hover:border-luxury-accent/40 transition-colors">
      {/* Body */}
      <div className="flex-1 p-5 space-y-3">
        <div className="inline-flex items-center justify-center h-10 w-10 rounded-md bg-[#1a1e2e] text-luxury-accent">
          {card.icon}
        </div>
        <div>
          <p className="font-bold text-luxury-text tracking-tight">{card.title}</p>
          <p className="text-sm text-luxury-text-secondary mt-0.5">{card.description}</p>
        </div>
      </div>

      {/* Expandable links */}
      {open && (
        <div className="border-t border-[#1e2230] px-5 py-3 space-y-2">
          {card.links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              target={link.href.startsWith('http') ? '_blank' : undefined}
              rel={link.href.startsWith('http') ? 'noopener noreferrer' : undefined}
              className="block text-sm text-luxury-accent hover:text-luxury-accent-alt transition-colors"
            >
              → {link.label}
            </a>
          ))}
        </div>
      )}

      {/* Footer toggle */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-5 py-3 border-t border-[#1e2230]
          text-xs font-bold tracking-widest uppercase text-luxury-text-secondary
          hover:text-luxury-text transition-colors"
      >
        View Guide
        <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
    </div>
  );
}

// ── GoCard component ───────────────────────────────────────────────────────
function GoCardView({ card }: { card: GoCard }) {
  return (
    <div className="flex flex-col bg-[#0f1117] border border-[#1e2230] rounded-lg overflow-hidden hover:border-luxury-accent/40 transition-colors">
      {/* Body */}
      <div className="flex-1 p-5 space-y-3">
        <div className="inline-flex items-center justify-center h-10 w-10 rounded-md bg-[#1a1e2e] text-luxury-accent">
          {card.icon}
        </div>
        <div>
          <p className="font-bold text-luxury-text tracking-tight">{card.title}</p>
          <p className="text-sm text-luxury-text-secondary mt-0.5">{card.description}</p>
        </div>
      </div>

      {/* Footer link */}
      <a
        href={card.href}
        target={card.href.startsWith('http') ? '_blank' : undefined}
        rel={card.href.startsWith('http') ? 'noopener noreferrer' : undefined}
        className="flex items-center gap-1.5 px-5 py-3 border-t border-[#1e2230]
          text-xs font-bold tracking-widest uppercase text-luxury-text-secondary
          hover:text-luxury-text transition-colors"
      >
        Go
        <span aria-hidden="true">→</span>
      </a>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────
export default function WhatIsCyperfPage() {
  return (
    <div className="space-y-8 animate-in">
      <div className="text-center space-y-2 pb-2">
        <h1 className="text-4xl font-display font-bold text-luxury-accent tracking-luxury">
          CyPerf Automation 101
        </h1>
        <p className="text-luxury-text-secondary">
          Everything you need to automate, deploy, and run CyPerf tests
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {CARDS.map((card) =>
          card.kind === 'guide' ? (
            <GuideCardView key={card.title} card={card} />
          ) : (
            <GoCardView key={card.title} card={card} />
          )
        )}
      </div>

      {/* How to interact with CyPerf */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          How to interact with Cyperf?
        </h2>
        <img
          src="/CyperfInteractionModes.png"
          alt="Keysight CyPerf – REST API First Product interaction modes"
          className="w-full rounded-md border border-luxury-border/40"
        />
        <img
          src="/DifferentWaysToUseCyperf.png"
          alt="Different ways to use Keysight CyPerf"
          className="w-full rounded-md border border-luxury-border/40"
        />
      </div>

      {/* Test Session Components Hierarchy */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Cyperf Test Session Components Hierarchy
        </h2>
        <img
          src="/CyperfAutomationObjectArchitecture.png"
          alt="CyPerf automation object architecture — session, configuration, test run"
          className="w-full rounded-md border border-luxury-border/40"
        />
      </div>

      {/* Typical Test Run Flow */}
      <div className="card-luxury space-y-4">
        <h2 className="text-xl font-display font-bold text-luxury-accent tracking-luxury">
          Typical Test Run Flow
        </h2>
        <img
          src="/FastestWayToStartTheTest.png"
          alt="CyPerf automation script workflow — session creation to export results"
          className="w-full rounded-md border border-luxury-border/40"
        />
      </div>

    </div>
  );
}
