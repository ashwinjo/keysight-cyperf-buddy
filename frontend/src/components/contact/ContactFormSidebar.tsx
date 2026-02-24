import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { CheckCircle2, X } from 'lucide-react';

import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { ConfirmDialog } from './ConfirmDialog';
import { useContactForm } from '../../hooks/useContactForm';
import { ContactContext, ContactFormResponse } from '../../types/api';

// ─── Zod schema (client-side validation only) ──────────────────────────────

const contactSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  company: z.string().min(1, 'Company is required').max(200),
  email: z.string().email('Enter a valid email address'),
});

type ContactFormData = z.infer<typeof contactSchema>;

// ─── State machine ──────────────────────────────────────────────────────────

type SidebarState = 'idle' | 'confirming' | 'form' | 'submitting' | 'success' | 'error';

// ─── Props ──────────────────────────────────────────────────────────────────

interface ContactFormSidebarProps {
  cveId: string;
  testable: boolean;
  context: ContactContext;
  cvssScore: number | null;
  attackProfiles: string[];
  isOpen: boolean;
  onClose: () => void;
}

// ─── Field error helper ─────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-red-400">{message}</p>;
}

// ─── Label helper ───────────────────────────────────────────────────────────

function Label({ htmlFor, children }: { htmlFor: string; children: React.ReactNode }) {
  return (
    <label
      htmlFor={htmlFor}
      className="block text-xs font-medium uppercase tracking-luxury text-luxury-text-secondary mb-1"
    >
      {children}
    </label>
  );
}

// ─── Main component ─────────────────────────────────────────────────────────

export function ContactFormSidebar({
  cveId,
  testable,
  context,
  cvssScore,
  attackProfiles,
  isOpen,
  onClose,
}: ContactFormSidebarProps) {
  const [state, setState] = React.useState<SidebarState>('idle');
  const [apiResponse, setApiResponse] = React.useState<ContactFormResponse | null>(null);

  const { submitForm, isSubmitting, error: apiError, reset: resetHook } = useContactForm();

  const form = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
      company: '',
      email: '',
    },
  });

  // Drive state transitions from isOpen prop
  React.useEffect(() => {
    if (isOpen && state === 'idle') {
      setState('confirming');
    }
    if (!isOpen) {
      // Reset everything when parent closes the sheet
      setState('idle');
      form.reset();
      resetHook();
      setApiResponse(null);
    }
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleConfirm = () => {
    setState('form');
  };

  const handleCancel = () => {
    onClose();
  };

  const handleSubmit = form.handleSubmit(async (data: ContactFormData) => {
    setState('submitting');
    try {
      const payload = {
        ...data,
        cve_id: cveId,
        context,
        testable,
        cvss_score: cvssScore,
        attack_profiles: attackProfiles,
      };
      const response = await submitForm(payload);
      setApiResponse(response);
      setState('success');
    } catch {
      // apiError is set by the hook; stay on form for retry
      setState('form');
    }
  });

  const sheetTitle =
    context === 'discuss'
      ? `Let's Discuss CVE-${cveId}`
      : `Request Feature: CVE-${cveId}`;

  const contextLabel =
    context === 'discuss' ? "Let's Discuss" : 'Request Feature';

  const isSheetOpen = isOpen && state !== 'idle';

  return (
    <>
      {/* Confirmation dialog — shown before form */}
      <ConfirmDialog
        isOpen={isOpen && state === 'confirming'}
        cveId={cveId}
        context={context}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />

      {/* Sidebar sheet — shown after confirmation */}
      <Dialog.Root
        open={isSheetOpen && state !== 'confirming'}
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
      >
        <Dialog.Portal>
          {/* Backdrop */}
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />

          {/* Side panel */}
          <Dialog.Content
            className="fixed right-0 top-0 z-50 h-full w-full sm:w-[420px] flex flex-col border-l border-luxury-border bg-luxury-bg shadow-elegant-lg data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right duration-300"
            onEscapeKeyDown={handleCancel}
            aria-describedby="contact-sidebar-desc"
          >
            {/* Header */}
            <div className="flex items-start justify-between border-b border-luxury-border px-6 py-4">
              <div>
                <Dialog.Title className="text-sm font-semibold text-luxury-accent font-display tracking-luxury uppercase">
                  {sheetTitle}
                </Dialog.Title>
                <p id="contact-sidebar-desc" className="mt-1 text-xs text-luxury-text-secondary">
                  Your information will be shared with the Keysight team.
                </p>
              </div>
              <Dialog.Close asChild>
                <button
                  className="ml-4 mt-0.5 rounded p-1 text-luxury-text-secondary hover:text-luxury-text hover:bg-luxury-bg-subtle transition-colors"
                  aria-label="Close"
                  onClick={onClose}
                >
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-6 py-6">

              {/* ── Success state ── */}
              {state === 'success' && apiResponse && (
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle2 size={20} />
                    <span className="text-sm font-medium">Email sent to the Keysight team.</span>
                  </div>

                  <p className="text-xs text-luxury-text-secondary">{apiResponse.message}</p>

                  {/* Email preview */}
                  <div className="rounded border border-luxury-border bg-[#0d0d0d] p-4">
                    <p className="mb-2 text-xs font-medium uppercase tracking-luxury text-luxury-text-secondary">
                      Email Preview
                    </p>
                    <pre className="whitespace-pre-wrap break-words font-mono text-xs text-luxury-text leading-relaxed">
                      {apiResponse.preview}
                    </pre>
                  </div>

                  <Button
                    variant="outline"
                    className="w-full mt-2"
                    onClick={onClose}
                  >
                    Close
                  </Button>
                </div>
              )}

              {/* ── Form state (+ submitting) ── */}
              {(state === 'form' || state === 'submitting') && (
                <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">

                  {/* First Name */}
                  <div>
                    <Label htmlFor="first_name">First Name</Label>
                    <Input
                      id="first_name"
                      type="text"
                      autoComplete="given-name"
                      aria-invalid={!!form.formState.errors.first_name}
                      {...form.register('first_name')}
                    />
                    <FieldError message={form.formState.errors.first_name?.message} />
                  </div>

                  {/* Last Name */}
                  <div>
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input
                      id="last_name"
                      type="text"
                      autoComplete="family-name"
                      aria-invalid={!!form.formState.errors.last_name}
                      {...form.register('last_name')}
                    />
                    <FieldError message={form.formState.errors.last_name?.message} />
                  </div>

                  {/* Company */}
                  <div>
                    <Label htmlFor="company">Company</Label>
                    <Input
                      id="company"
                      type="text"
                      autoComplete="organization"
                      aria-invalid={!!form.formState.errors.company}
                      {...form.register('company')}
                    />
                    <FieldError message={form.formState.errors.company?.message} />
                  </div>

                  {/* Work Email */}
                  <div>
                    <Label htmlFor="email">Work Email</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="work email"
                      aria-invalid={!!form.formState.errors.email}
                      {...form.register('email')}
                    />
                    <FieldError message={form.formState.errors.email?.message} />
                  </div>

                  {/* Context read-only */}
                  <div className="rounded border border-luxury-border bg-luxury-bg-subtle px-4 py-3">
                    <p className="text-xs text-luxury-text-secondary">
                      Regarding:{' '}
                      <span className="font-mono text-luxury-text">{cveId}</span>
                      {' — '}
                      <span className="text-luxury-accent">{contextLabel}</span>
                    </p>
                  </div>

                  {/* API error inline */}
                  {apiError && state === 'form' && (
                    <p className="text-xs text-red-400 rounded border border-red-900/40 bg-red-950/20 px-3 py-2">
                      {apiError}
                    </p>
                  )}

                  {/* Submit */}
                  <Button
                    type="submit"
                    variant="default"
                    className="w-full"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Sending…' : 'Send'}
                  </Button>
                </form>
              )}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
