import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';
import path from 'path';
var __dirname = path.dirname(fileURLToPath(import.meta.url));
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: { '@': path.resolve(__dirname, 'src') },
    },
    server: {
        port: 3000,
        proxy: {
            '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
            '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
        },
    },
});
