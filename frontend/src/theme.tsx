import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react"
import { buttonRecipe } from "./theme/button.recipe"

const config = defineConfig({
  globalCss: {
    "html, body": {
      backgroundColor: "bg.canvas", // Adapts to light/dark
      color: "fg.default",
    },
  },
  theme: {
    tokens: {
      colors: {
        brand: {
          50: { value: "#e3f2fd" },
          100: { value: "#bbdefb" },
          500: { value: "#2196f3" }, // Primary Blue
          600: { value: "#1e88e5" }, // Hover Blue
          700: { value: "#1976d2" }, // Deep Blue
        },
        accent: {
          500: { value: "#009688" }, // Teal
        },
      },
    },
    semanticTokens: {
      colors: {
        bg: {
          canvas: { value: { base: "#f8f9fa", _dark: "#121212" } },
          panel: { value: { base: "#ffffff", _dark: "#1e1e1e" } },
          subtle: { value: { base: "#f1f3f5", _dark: "#2a2a2a" } },
          muted: { value: { base: "#e9ecef", _dark: "#333333" } },
        },
        fg: {
          default: { value: { base: "#1a202c", _dark: "#e2e8f0" } },
          muted: { value: { base: "#718096", _dark: "#a0aec0" } },
          inverted: { value: { base: "#ffffff", _dark: "#1a202c" } },
        },
        border: {
          subtle: { value: { base: "#e2e8f0", _dark: "#4a5568" } },
        },
      },
    },
    recipes: {
      button: buttonRecipe,
    },
  },
})

export const system = createSystem(defaultConfig, config)