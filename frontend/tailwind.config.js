/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f3efe6",
        ink: "#1c2430",
        navy: "#1e3a5f",
        copper: "#9a4e32",
        pine: "#1f6b56",
        line: "#ddd4c4",
        card: "#fffdf8",
      },
      fontFamily: {
        sans: ["Source Sans 3", "Segoe UI", "sans-serif"],
        serif: ["Newsreader", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(28, 36, 48, 0.06), 0 12px 32px rgba(28, 36, 48, 0.05)",
      },
    },
  },
  plugins: [],
};
