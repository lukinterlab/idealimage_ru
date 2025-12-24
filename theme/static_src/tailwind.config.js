/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    '../templates/**/*.html',
    '../../templates/**/*.html',
    '../../**/templates/**/*.html',
    '../../blog/templates/**/*.html',
    '../../Home/templates/**/*.html',
    '../../Visitor/templates/**/*.html',
    '../../Asistent/templates/**/*.html',
    '../../donations/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#EC4899',  // Розовый как в base_tailwind
        secondary: '#8B5CF6',  // Фиолетовый
        accent: '#F59E0B',  // Оранжевый
      },
      fontFamily: {
        sans: ['Nunito Sans', 'sans-serif'],
        heading: ['Montserrat', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
}
