import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './features/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#edf7ff',
          100: '#dbeafe',
          500: '#0f766e',
          600: '#0d9488',
          900: '#0f172a',
        },
      },
    },
  },
  plugins: [],
};

export default config;
