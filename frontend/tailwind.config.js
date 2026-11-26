/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: "#06070a",
          900: "#090a0f",
          850: "#0e1017",
          800: "#13161f",
          750: "#181c28",
          700: "#1f2434",
          600: "#2b3248",
          500: "#3d4663",
        },
        fox: {
          50: "#fff8f0",
          100: "#feeddb",
          200: "#fcd6b3",
          300: "#fab880",
          400: "#f89146",
          500: "#ff7a00", // TicketFox Signature Radiant Orange
          600: "#ea6500",
          700: "#c24d00",
          800: "#9a3d07",
          900: "#7c340b",
          950: "#441803",
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "system-ui", "-apple-system", "sans-serif"],
        heading: ["Outfit", "system-ui", "-apple-system", "sans-serif"],
      },
      keyframes: {
        radar: {
          "0%": { transform: "scale(0.95)", boxShadow: "0 0 0 0 rgba(16, 185, 129, 0.7)" },
          "70%": { transform: "scale(1)", boxShadow: "0 0 0 8px rgba(16, 185, 129, 0)" },
          "100%": { transform: "scale(0.95)", boxShadow: "0 0 0 0 rgba(16, 185, 129, 0)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        scaleIn: {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        radar: "radar 2s infinite cubic-bezier(0.16, 1, 0.3, 1)",
        fadeIn: "fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
        scaleIn: "scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
        slideUp: "slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
      },
      boxShadow: {
        "fox-glow": "0 0 25px rgba(255, 122, 0, 0.25)",
        "emerald-glow": "0 0 20px rgba(16, 185, 129, 0.3)",
      },
    },
  },
  plugins: [],
};
