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
        // Keysight brand palette — red kept for fallback, cyan mapped as primary
        keysight: {
          red: "#22d3ee",           // Remapped → IxNetwork cyan accent
          gray: "#4A4A4A",
          "gray-medium": "#8b949e",
          "gray-light": "#c9d1d9",
          black: "#010409",
          white: "#e6edf3",
        },
        // Semantic design tokens — IxNetwork dark theme
        luxury: {
          bg: "#0d1117",            // GitHub-dark navy
          "bg-subtle": "#161b22",   // Slightly elevated surface
          border: "#21262d",        // Subtle border
          text: "#e6edf3",          // Near-white
          "text-secondary": "#8b949e", // Muted gray
          accent: "#22d3ee",        // Cyan-400 (IxNetwork teal)
          "accent-alt": "#0891b2",  // Cyan-600 (hover / pressed)
        },
      },
      fontFamily: {
        // Monospace display font — matches IxNetwork hero heading style
        display: ["'JetBrains Mono'", "Menlo", "Monaco", "'Courier New'", "monospace"],
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "'JetBrains Mono'",
          "Menlo",
          "Monaco",
          "monospace",
        ],
      },
      letterSpacing: {
        luxury: "0.03em",
      },
      boxShadow: {
        elegant: "0 2px 8px rgba(0, 0, 0, 0.5)",
        "elegant-lg": "0 8px 32px rgba(0, 0, 0, 0.6)",
        cyan: "0 0 16px rgba(34, 211, 238, 0.15)",
      },
    },
  },
  darkMode: "class",
  plugins: [],
};

export default config;
