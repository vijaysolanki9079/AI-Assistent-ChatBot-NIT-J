/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#07090e',
        surface: 'rgba(15, 23, 42, 0.65)',
        accent: {
          purple: '#a855f7',
          indigo: '#6366f1',
          cyan: '#06b6d4',
          emerald: '#10b981',
          rose: '#f43f5e'
        }
      },
      animation: {
        'spin-slow': 'spin 12s linear infinite',
      }
    },
  },
  plugins: [],
}

