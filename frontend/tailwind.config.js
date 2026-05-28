/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
          colors: {
              "primary": "#f97415",
              "background-light": "#f8f7f5",
              "background-dark": "#23170f",
              "navy-industrial": "#1E293B",
              "slate-industrial": "#F8FAFC",
          },
          fontFamily: {
              "display": ["Space Grotesk", "sans-serif"]
          },
          borderRadius: {
              "DEFAULT": "0.125rem",
              "lg": "0.25rem",
              "xl": "0.5rem",
              "full": "0.75rem"
          },
      },
  },
    plugins: [],
  }
