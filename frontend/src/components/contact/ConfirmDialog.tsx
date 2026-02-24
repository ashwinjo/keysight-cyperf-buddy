import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Button } from '../ui/button';

interface ConfirmDialogProps {
  isOpen: boolean;
  cveId: string;
  context: 'discuss' | 'feature_request';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  cveId,
  context,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const contextLabel = context === 'discuss' ? "Let's Discuss" : 'Request Feature';

  return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className="fixed left-[50%] top-[50%] z-50 w-full max-w-md translate-x-[-50%] translate-y-[-50%] rounded-lg border border-luxury-border bg-luxury-bg p-6 shadow-elegant-lg data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]"
          onEscapeKeyDown={onCancel}
        >
          <Dialog.Title className="text-base font-semibold text-luxury-text font-display mb-2">
            Share your contact information?
          </Dialog.Title>

          <Dialog.Description className="text-sm text-luxury-text-secondary mb-1">
            We'll send your contact details and CVE context to the Keysight team. No account
            required.
          </Dialog.Description>

          <p className="text-xs text-luxury-text-secondary mb-6">
            <span className="text-luxury-accent font-mono">{cveId}</span>
            {' — '}
            {contextLabel}
          </p>

          <div className="flex flex-col gap-3">
            <Button
              variant="default"
              className="w-full"
              onClick={onConfirm}
              autoFocus
            >
              Continue
            </Button>
            <Button
              variant="ghost"
              className="w-full"
              onClick={onCancel}
            >
              Cancel
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
