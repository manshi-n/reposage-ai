/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0E1218",
          900: "#131822",
          800: "#1B212C",
          700: "#242C3A",
          600: "#323C4E",
        },
        mist: {
          400: "#5B6472",
          300: "#8B93A3",
          200: "#B7BECB",
          100: "#E4E7EC",
        },
        signal: {
          amber: "#E8A33D",
          teal: "#4FB8A6",
          rose: "#E1596A",
          violet: "#8C7BE0",
        },
      },
      fontFamily: {
        display: ["\"Space Grotesk\"", "sans-serif"],
        body: ["\"Inter\"", "sans-serif"],
        mono: ["\"JetBrains Mono\"", "monospace"],
      },
      borderRadius: {
        card: "10px",
      },
    },
  },
  plugins: [],
};
