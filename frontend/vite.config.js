/* 
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
*/

// If Docker isn't refreshing automatically, it's usually a WSL file-watching bug. 
// Add this to vite.config.js to force it:
/*
server: {
  watch: {
    usePolling: true, // Forces Vite to check for changes frequently
  },
},
*/

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    host: true,
    watch: {
      usePolling: true,
    },
    proxy: {
      // FastAPI backend — inside Docker network on port 8000
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },

      // TiTiler — inside Docker network the service is "raster-server" on port 80
      // (docker-compose maps TITILER_HOST_PORT → 80 inside container)
      // Browser sends:  GET /titiler/cog/tiles/...
      // Vite forwards:  GET http://raster-server/cog/tiles/...
      '/titiler': {
        target: 'http://raster-server:80',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/titiler/, ''),
      },
    },
  },
})