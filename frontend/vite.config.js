import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Tesseract appends the language filename to its model directory.
        assetFileNames: (asset) => asset.names.includes("eng.traineddata.gz")
          ? "assets/ocr-[hash]/[name][extname]"
          : "assets/[name]-[hash][extname]",
      },
    },
  },
  server: {
    port: 5173,
  },
});
