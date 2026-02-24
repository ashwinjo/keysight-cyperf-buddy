import { useState } from 'react';
import axios from 'axios';
import { ContactFormRequest, ContactFormResponse } from '../types/api';

const API_BASE = '/api';

interface UseContactFormReturn {
  submitForm: (data: ContactFormRequest) => Promise<ContactFormResponse>;
  isSubmitting: boolean;
  error: string | null;
  reset: () => void;
}

export function useContactForm(): UseContactFormReturn {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitForm = async (data: ContactFormRequest): Promise<ContactFormResponse> => {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await axios.post<ContactFormResponse>(
        `${API_BASE}/contact/submit`,
        data,
        { timeout: 15000 }
      );
      return res.data;
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message =
        axiosErr?.response?.data?.detail || 'Submission failed. Please try again.';
      setError(message);
      throw new Error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const reset = () => {
    setError(null);
  };

  return { submitForm, isSubmitting, error, reset };
}
