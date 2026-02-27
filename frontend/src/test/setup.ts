/**
 * Global Vitest setup file.
 *
 * Extends the vitest `expect` interface with @testing-library/jest-dom matchers
 * (toBeInTheDocument, toBeDisabled, toHaveValue, etc.) so they are available
 * in every test file without explicit imports.
 */
import "@testing-library/jest-dom";
