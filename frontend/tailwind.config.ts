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
      },
      fontFamily: {
        mono: [
          "Menlo",
          "Monaco",
          "Courier New",
          "monospace",
        ],
      },
    },
  },
  darkMode: "class",
  plugins: [],
};

export default config;
