import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0A0A0A",
        bone: "#F5F1E8",
        ember: "#FF5A1F",
        fog: "#C9C3B8"
      },
      fontFamily: {
        sans: ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"]
      },
      boxShadow: {
        panel: "0 30px 80px rgba(0, 0, 0, 0.18)"
      }
    }
  },
  plugins: []
};

export default config;
