/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: '#0B1626', 800: '#12233A', 700: '#1B3150', 600: '#2A4468' },
        paper: '#EDF0F4',
        line: '#D5DBE4',
        signal: { DEFAULT: '#0E7C86', dark: '#0A5F67', soft: '#DDF1F2' },
        risk: { low: '#0F766E', medium: '#B45309', high: '#C2410C', critical: '#9F1239' },
      },
      fontFamily: {
        sans: ['"Segoe UI"', 'system-ui', '-apple-system', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'Consolas', '"Cascadia Mono"', 'Menlo', 'monospace'],
      },
      boxShadow: { card: '0 1px 2px rgba(11,22,38,0.06), 0 1px 1px rgba(11,22,38,0.04)' },
    },
  },
  plugins: [],
};
