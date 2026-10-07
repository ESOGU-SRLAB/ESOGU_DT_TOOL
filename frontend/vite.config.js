import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const port = Number(env.VITE_DEV_PORT || 5175);
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8100';

  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    preview: {
      host: '127.0.0.1',
      port,
      strictPort: true,
    },
  };
});
