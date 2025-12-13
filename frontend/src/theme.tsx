import { createSystem, defaultConfig } from "@chakra-ui/react"
import { buttonRecipe } from "./theme/button.recipe"

export const system = createSystem(defaultConfig, {
  globalCss: {
    html: {
      fontSize: "16px",
    },
    body: {
      fontSize: "0.875rem",
      margin: 0,
      padding: 0,
      backgroundColor: "#f4f6f8", // Light gray background for contrast
      color: "#1a202c",
    },
    ".main-link": {
      color: "brand.500",
      fontWeight: "bold",
    },
  },
  theme: {
    tokens: {
      colors: {
        brand: {
          50: { value: "#E3F2FD" },
          100: { value: "#BBDEFB" },
          500: { value: "#2196F3" }, // Primary Blue
          600: { value: "#1E88E5" },
          700: { value: "#1976D2" }, // Professional Deep Blue
          900: { value: "#0D47A1" },
        },
        accent: {
          500: { value: "#009688" }, // Teal for "Efficiency/Eco"
        },
      },
    },
    recipes: {
      button: buttonRecipe,
    },
  },
})