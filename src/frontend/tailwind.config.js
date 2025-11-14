/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // S.LSI Learning Platform brand colors
        primary: {
          DEFAULT: '#1976d2',
          dark: '#1565c0',
          light: '#42a5f5',
        },
        gradient: {
          from: '#667eea',
          to: '#764ba2',
        },
      },
    },
  },
  plugins: [],
}
