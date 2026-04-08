/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef7ee',
          100: '#fdedd6',
          200: '#fad7ac',
          300: '#f6ba77',
          400: '#f19340',
          500: '#ee751a',
          600: '#df5b10',
          700: '#b94410',
          800: '#933715',
          900: '#772f14',
        },
        sage: {
          50: '#f6f7f4',
          100: '#e9ebe3',
          200: '#d4d8c9',
          300: '#b6bca5',
          400: '#969e81',
          500: '#798264',
          600: '#5e674d',
          700: '#4a5140',
          800: '#3d4336',
          900: '#35392f',
        }
      },
    },
  },
  plugins: [],
}
