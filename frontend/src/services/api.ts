// TypeScript 변경 표시: JSX가 없는 유틸/API 파일이라 .js에서 .ts로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 동작은 유지하고, 이후 함수 인자/반환 타입을 점진적으로 붙일 수 있습니다.
// 초보자 안내: 프론트엔드에서 백엔드 API를 호출할 때 공통으로 사용하는 axios 설정 파일입니다.

import axios from 'axios';

interface AnalysisChatOptions {
  provider?: string;
  conversationId?: string;
}

const isBrowserFile = (file: unknown): file is File =>
  typeof File !== 'undefined' && file instanceof File;

const getApiBaseUrl = () => {
  // TypeScript 변경 표시: Vite에서는 CRA의 process.env 대신 import.meta.env로 환경변수를 읽습니다.
  const configuredUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.REACT_APP_API_BASE_URL;

  if (configuredUrl) {
    return configuredUrl;
  }

  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 모든 API 요청을 보내기 직전에 실행됩니다.
// 로그인 토큰이 있으면 Authorization 헤더에 자동으로 붙여서 백엔드가 사용자를 알아볼 수 있게 합니다.
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 백엔드가 401을 보내면 로그인 정보가 만료되었거나 잘못된 상태입니다.
// 이때 저장된 로그인 값을 지우고 새로고침해서 다시 로그인하도록 만듭니다.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || '';
    const isAuthSubmitRequest =
      requestUrl.includes('/api/auth/login') || requestUrl.includes('/api/auth/signup');

    if (error.response?.status === 401 && !isAuthSubmitRequest) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('isLoggedIn');
      localStorage.removeItem('username');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  signup: (username: string, password: string) =>
    apiClient.post('/api/auth/signup', { username, password }),

  login: (username: string, password: string) =>
    apiClient.post('/api/auth/login', { username, password }),

  healthCheck: () => apiClient.get('/api/health'),

  updateProfile: (username: string) =>
    apiClient.patch('/api/auth/profile', { username }),

  changePassword: (currentPassword: string, newPassword: string) =>
    apiClient.patch('/api/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  deleteAccount: () => apiClient.delete('/api/auth/account'),
};

export const analysisAPI = {
  chat: (question: string, files: File[], options: AnalysisChatOptions = {}, analysisText = '') => {
    const formData = new FormData();
    formData.append('question', question);
    if (options.conversationId) formData.append('conversation_id', options.conversationId);
    formData.append('llm_provider', options.provider || 'openai');
    if (analysisText) formData.append('analysis_text', analysisText);
    files.filter(isBrowserFile).forEach((file) => formData.append('files', file, file.name));

    return apiClient.post('/api/analysis/chat', formData);
  },
  generateChatTitle: (question: string, options: AnalysisChatOptions = {}, analysisText = '') => {
    const formData = new FormData();
    formData.append('question', question);
    formData.append('llm_provider', options.provider || 'openai');
    if (analysisText) formData.append('analysis_text', analysisText);

    return apiClient.post('/api/analysis/title', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  createVisual: (type: string, files: File[], analysisText = '') => {
    const formData = new FormData();
    formData.append('analysis_text', analysisText);
    files.filter(isBrowserFile).forEach((file) => formData.append('files', file, file.name));

    return apiClient.post(`/api/visuals/${encodeURIComponent(type)}`, formData);
  },
};

export const projectAPI = {
  list: () => apiClient.get('/api/projects'),
  sync: (projects: unknown[]) => apiClient.put('/api/projects/sync', { projects }),
  save: (project: unknown) => apiClient.post('/api/projects', { project }),
  delete: (projectId: string) => apiClient.delete(`/api/projects/${encodeURIComponent(projectId)}`),
  findByInviteCode: (inviteCode: string) => apiClient.get(`/api/projects/invite/${encodeURIComponent(inviteCode)}`),
};

export default apiClient;
