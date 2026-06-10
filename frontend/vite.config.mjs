// 초보자 안내: Vite 개발 서버와 빌드 옵션을 정하는 프론트엔드 설정 파일입니다.

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  envDir: '..',
  // Windows에서 node_modules/.vite 캐시가 잠기면 개발 서버 시작 시 EPERM이 날 수 있습니다.
  cacheDir: '.vite-cache',
  plugins: [
    // React Compiler는 선택 최적화 플러그인입니다.
    // 패키지 설치가 꼬이면 개발 서버가 시작되지 않으므로 기본 React 플러그인만 사용합니다.
    react(),
  ],
  server: {
    host: '127.0.0.1',
    port: 3000,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 3000,
  },
});
