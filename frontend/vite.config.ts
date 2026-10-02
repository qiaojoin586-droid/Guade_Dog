import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

const FRONTEND_DIR = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(FRONTEND_DIR, '..');

/**
 * 把仓库根目录的 video/ 与 images/ 直接映射到站点 /video、/images。
 * 用户把演示视频和图片放在项目根目录即可，不需要复制到 public/。
 */
const MEDIA_DIRS: Record<string, string> = {
  video: path.join(PROJECT_ROOT, 'video'),
  images: path.join(PROJECT_ROOT, 'images'),
};

const MIME_TYPES: Record<string, string> = {
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.mov': 'video/quicktime',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
};

function rootMediaPlugin(): Plugin {
  return {
    name: 'guide-dog-root-media',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = (req.url ?? '').split('?')[0];
        const match = /^\/(video|images)\/(.+)$/.exec(pathname);
        if (!match) {
          next();
          return;
        }
        const [, dirName, fileName] = match;
        const baseDir = MEDIA_DIRS[dirName];
        const filePath = path.join(baseDir, decodeURIComponent(fileName));

        // 防目录穿越
        if (!filePath.startsWith(baseDir) || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
          res.statusCode = 404;
          res.end(`media not found: ${pathname}`);
          return;
        }

        res.setHeader('Content-Type', MIME_TYPES[path.extname(filePath).toLowerCase()] ?? 'application/octet-stream');
        res.setHeader('Cache-Control', 'no-cache');
        fs.createReadStream(filePath).pipe(res);
      });
    },
    closeBundle() {
      // 构建时把素材复制进 dist，保证 preview/部署后也能播放
      const distDir = path.join(FRONTEND_DIR, 'dist');
      for (const [dirName, sourceDir] of Object.entries(MEDIA_DIRS)) {
        if (fs.existsSync(sourceDir)) {
          fs.cpSync(sourceDir, path.join(distDir, dirName), { recursive: true });
        }
      }
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    rootMediaPlugin(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icons/*.png'],
      manifest: {
        name: '导盲AI智能体',
        short_name: '导盲AI',
        description: '面向视障人士的全方位AI辅助应用',
        theme_color: '#1e40af',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/app',
        icons: [
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        // 缓存策略占位（见前端文档 §7.4）
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.example\.com\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
