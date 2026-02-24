import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        dark: {
          50: "#f8f8f8",
          100: "#f0f0f0",
          200: "#d9d9d9",
          900: "#0D1117",
          950: "#010409",
        },
        // Refined luxury palette
        luxury: {
          bg: "#0A0E14",        // Deep charcoal
          "bg-subtle": "#1a1f2e", // Subtle contrast
          border: "#2d3748",    // Refined border
          text: "#f5f1e8",      // Warm cream
          "text-secondary": "#b8b5b0", // Warm gray
          accent: "#d4af37",    // Gold
          "accent-alt": "#c0a080", // Bronze
        },
      },
      fontFamily: {
        display: ["Georgia", "Garamond", "serif"],
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Helvetica Neue",
          "sans-serif",
        ],
        mono: [
          "Menlo",
          "Monaco",
          "Courier New",
          "monospace",
        ],
      },
      letterSpacing: {
        luxury: "0.05em",
      },
      boxShadow: {
        elegant: "0 2px 8px rgba(0, 0, 0, 0.3)",
        "elegant-lg": "0 8px 24px rgba(0, 0, 0, 0.4)",
      },
    },
  },
  darkMode: "class",
  plugins: [],
};

export default config;
