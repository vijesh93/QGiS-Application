import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite' // The new v4 plugin


export default defineConfig({
  plugins: [
    react(),      // Keeps your JSX/React working
    tailwindcss() // Handles the modern styling
  ],
  server: {
    port: 5173,
    host: true,
    watch: {
      usePolling: true, // Recommended for WSL/Docker to ensure auto-refresh works
    },
  }
})

// If Docker isn't refreshing automatically, it's usually a WSL file-watching bug. 
// Add this to vite.config.js to force it:
/*
server: {
  watch: {
    usePolling: true, // Forces Vite to check for changes frequently
  },
},
*/