/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        body: ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      colors: {
        soul: {
          cream: '#faf8f5',
          sand: '#e8e2d9',
          sage: '#9a9b7a',
          rose: '#c1666b',
          terracotta: '#b85c4a',
          deep: '#2d2a26',
          ink: '#1a1917',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.4s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backgroundImage: {
        'gradient-soft': 'linear-gradient(135deg, #faf8f5 0%, #e8e2d9 50%, #e0d9cf 100%)',
        'gradient-warm': 'linear-gradient(160deg, #c1666b 0%, #b85c4a 40%, #9a9b7a 100%)',
      },
    },
  },
  plugins: [],
};
