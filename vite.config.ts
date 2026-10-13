import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, Plugin} from 'vite';

// Built-in backend API middleware plugin for InvoiceTrust
function invoiceTrustApiPlugin(): Plugin {
  return {
    name: 'invoicetrust-api',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith('/api/')) {
          return next();
        }

        res.setHeader('Content-Type', 'application/json');

        if (req.url === '/api/health') {
          res.end(JSON.stringify({ status: 'ok', engine: 'InvoiceTrust Neural Verifier v2.4', time: new Date().toISOString() }));
          return;
        }

        // Pass through to next if not handled here; our client library handles live fetch + fallback
        next();
      });
    },
  };
}

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss(), invoiceTrustApiPlugin()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    build: {
      rollupOptions: {
        input: {
          main: path.resolve(__dirname, 'index.html'),
          result: path.resolve(__dirname, 'result.html'),
          dashboard: path.resolve(__dirname, 'dashboard.html'),
          audit: path.resolve(__dirname, 'audit.html'),
        },
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
