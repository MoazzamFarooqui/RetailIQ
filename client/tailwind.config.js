/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#27272a',
          700: '#18181b',
          800: '#111113',
          900: '#09090b',
        },
        slate: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b',
        },
        surface: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          900: '#18181b',
          925: '#111113',
          950: '#09090b',
        },
        ink: {
          DEFAULT: '#fafafa',
          soft: '#a1a1aa',
          faint: '#71717a',
        },
        success: '#90c99e',
        warning: '#d97706',
        danger: '#ef4444',
        info: '#60a5fa',
        // Premium indigo for AI features
        indigo: {
          50: '#eeedff',
          100: '#dddcff',
          200: '#c5c4ff',
          300: '#aaa9f2',
          400: '#8988e7',
          500: '#5b5bd6',
          600: '#4d4dc2',
          700: '#3f3fa3',
          800: '#323280',
          900: '#25255e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.4)',
        'card-hover': '0 4px 14px -2px rgb(0 0 0 / 0.5), 0 2px 4px -2px rgb(0 0 0 / 0.4)',
        soft: '0 8px 30px -6px rgb(0 0 0 / 0.12)',
        ring: '0 0 0 4px rgb(0 0 0 / 0.12)',
        glow: '0 0 40px -8px rgb(0 0 0 / 0.18)',
        'glow-green': '0 0 30px -6px rgb(144 201 158 / 0.35)',
        'glow-indigo': '0 0 30px -6px rgb(70 133 255 / 0.3)',
        // Premium soft shadows
        'soft-outer': '0 4px 12px -2px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.04)',
        'soft-inset': 'inset 0 1px 2px rgba(0 0 0 / 0.04)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.97)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-2px)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.25s ease-out both',
        'scale-in': 'scale-in 0.18s ease-out both',
        'float': 'float 3s ease-in-out infinite',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

