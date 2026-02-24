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
        // Keysight brand palette
        keysight: {
          red: "#EF3B39",           // Keysight Red (primary accent)
          gray: "#4A4A4A",          // Keysight Gray (dark)
          "gray-medium": "#9C9C9C", // Keysight Medium Gray
          "gray-light": "#D3D3D3",  // Keysight Light Gray
          black: "#000000",         // Black
          white: "#FFFFFF",         // White
        },
        // Alias for backward compatibility
        luxury: {
          bg: "#FFFFFF",            // White background (clean, crisp)
          "bg-subtle": "#F5F5F5",   // Very light gray
          border: "#D3D3D3",        // Light gray border
          text: "#000000",          // Black text
          "text-secondary": "#9C9C9C", // Medium gray text
          accent: "#EF3B39",        // Keysight Red (primary)
          "accent-alt": "#4A4A4A",  // Keysight Gray (secondary)
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
