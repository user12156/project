// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 JS 로직은 유지하면서 함수 인자와 화면 props에 실제 타입을 붙여 TypeScript 검사를 통과하게 했습니다.
// 초보자 안내: 로그인 상태와 사용자 정보를 여러 컴포넌트에서 같이 쓰게 해주는 React Context입니다.

import React, { createContext, useState, useContext, useEffect } from 'react';
import { authAPI } from '../services/api';
import {
  getProjectsKey,
  getRecentConversationsKey,
  getShareRoomKey,
  migrateCurrentUserStorage,
  readJson,
  SHARED_PROJECTS_KEY,
  SHARED_ROOM_PREFIX,
  writeJson,
} from '../utils/storageKeys';

// React Context API로 로그인 상태를 앱 전체에서 공유합니다.
// Home, Sidebar, 각 페이지는 useAuth()를 통해 현재 로그인 유저와 login/logout 함수를 가져옵니다.
const AuthContext = createContext(null);

const getProfileImageKey = (userId) => `profileImage:${userId}`;
const LOCAL_AUTH_PREFIX = 'local-auth-user:';

const getLocalAuthKey = (username) => `${LOCAL_AUTH_PREFIX}${username.trim().toLowerCase()}`;

const clearSession = () => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('username');
  localStorage.removeItem('userId');
};

const encodeLocalPassword = (password) => {
  try {
    return btoa(unescape(encodeURIComponent(password)));
  } catch {
    return password;
  }
};

const createLocalAuthResponse = (username, password, { allowCreate = true } = {}) => {
  const normalizedUsername = username.trim();
  const key = getLocalAuthKey(normalizedUsername);
  const stored = readJson(key, null);
  const encodedPassword = encodeLocalPassword(password);

  if (stored?.password && stored.password !== encodedPassword) {
    const error = new Error('비밀번호가 올바르지 않습니다.');
    error.userMessage = '비밀번호가 올바르지 않습니다.';
    throw error;
  }

  if (!stored && !allowCreate) {
    const error = new Error('등록되지 않은 아이디입니다.');
    error.userMessage = '등록되지 않은 아이디입니다.';
    throw error;
  }

  const userId = stored?.id || `local:${normalizedUsername}`;
  const userData = {
    id: userId,
    username: stored?.username || normalizedUsername,
  };

  writeJson(key, {
    id: userId,
    username: userData.username,
    password: encodedPassword,
  });

  return {
    data: {
      access_token: `local-dev-token:${userId}`,
      user: userData,
    },
  };
};

export const AuthProvider = ({ children }) => {
  // useState는 React의 상태 저장 기능입니다.
  // 값이 바뀌면 이 Context를 사용하는 컴포넌트들이 다시 렌더링됩니다.
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const applyAuthSession = (accessToken, userData) => {
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('username', userData.username);
    localStorage.setItem('userId', userData.id);
    userData.profileImage = localStorage.getItem(getProfileImageKey(userData.id)) || '';
    migrateCurrentUserStorage();

    setIsLoggedIn(true);
    setUser(userData);
  };

  // useEffect는 컴포넌트가 처음 올라올 때 실행되는 React Hook입니다.
  // 새로고침 후에도 로그인 상태를 유지하기 위해 localStorage의 토큰을 확인합니다.
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    const username = localStorage.getItem('username');
    const userId = localStorage.getItem('userId');

    if (token && username && userId) {
      // 로그인된 계정을 확인한 뒤, 예전 저장 데이터를 현재 계정 키로 한 번 이전합니다.
      migrateCurrentUserStorage();
      setIsLoggedIn(true);
      setUser({
        username,
        id: userId,
        profileImage: localStorage.getItem(getProfileImageKey(userId)) || '',
      });
    }
    setLoading(false);
  }, []);

  // authAPI는 services/api.ts에 정의된 axios 기반 API 호출 객체입니다.
  // 백엔드 로그인 성공 시 access_token과 user 정보를 받아 localStorage에 저장합니다.
  const login = async (username, password) => {
    let response;
    try {
      response = await authAPI.login(username, password);
    } catch (error) {
      if (error?.response) throw error;
      response = createLocalAuthResponse(username, password);
    }
    const { access_token, user: userData } = response.data;

    applyAuthSession(access_token, userData);
  };

  // 회원가입도 로그인과 동일하게 토큰/유저 정보를 저장한 뒤 앱 상태를 로그인으로 바꿉니다.
  const signup = async (username, password) => {
    let response;
    try {
      response = await authAPI.signup(username, password);
    } catch (error) {
      if (error?.response) throw error;
      response = createLocalAuthResponse(username, password);
    }
    const { access_token, user: userData } = response.data;

    applyAuthSession(access_token, userData);
  };

  const googleLogin = async (idToken) => {
    const response = await authAPI.googleLogin(idToken);
    const { access_token, user: userData } = response.data;

    applyAuthSession(access_token, userData);
  };

  const kakaoLogin = async (code, redirectUri) => {
    const response = await authAPI.kakaoLogin(code, redirectUri);
    const { access_token, user: userData } = response.data;
    applyAuthSession(access_token, userData);
  };

  const naverLogin = async (code, state, redirectUri) => {
    const response = await authAPI.naverLogin(code, state, redirectUri);
    const { access_token, user: userData } = response.data;
    applyAuthSession(access_token, userData);
  };

  const acceptOAuthRedirect = ({ accessToken, user: userData }) => {
    if (!accessToken || !userData?.id || !userData?.username) return;
    applyAuthSession(accessToken, userData);
  };

  // 로그아웃은 인증 정보만 지웁니다.
  // 프로젝트/대화 데이터는 계정별 키에 남겨 두어 다음 로그인 때 다시 볼 수 있게 합니다.
  const logout = () => {
    clearSession();
    setIsLoggedIn(false);
    setUser(null);
  };

  const clearCurrentUserLocalData = (currentUser) => {
    if (!currentUser?.id) return;

    const projects = readJson(getProjectsKey(), []);
    const projectIds = new Set(Array.isArray(projects) ? projects.map((project) => project?.id).filter(Boolean) : []);

    localStorage.removeItem(getProjectsKey());
    localStorage.removeItem(getRecentConversationsKey());
    localStorage.removeItem(getShareRoomKey());
    localStorage.removeItem(getProfileImageKey(currentUser.id));

    const sharedProjects = readJson(SHARED_PROJECTS_KEY, []);
    if (Array.isArray(sharedProjects)) {
      writeJson(
        SHARED_PROJECTS_KEY,
        sharedProjects.filter(
          (project) => !projectIds.has(project?.id) && project?.owner !== currentUser.username
        )
      );
    }

    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (!key?.startsWith(`${SHARED_ROOM_PREFIX}.`)) continue;

      const room = readJson(key, null);
      if (!room || typeof room !== 'object') continue;

      writeJson(key, {
        ...room,
        members: Array.isArray(room.members)
          ? room.members.filter((member) => member?.name !== currentUser.username)
          : [],
        comments: Array.isArray(room.comments)
          ? room.comments.filter((comment) => comment?.user !== currentUser.username)
          : [],
        loadedProjectIds: Array.isArray(room.loadedProjectIds)
          ? room.loadedProjectIds.filter((projectId) => !projectIds.has(projectId))
          : [],
      });
    }
  };

  const updateProfile = async ({ username, profileImage }) => {
    if (!user?.id) return null;

    let nextUser = user;
    const trimmedUsername = username?.trim();
    if (trimmedUsername && trimmedUsername !== user.username) {
      const response = await authAPI.updateProfile(trimmedUsername);
      localStorage.setItem('username', response.data.username);
      nextUser = { ...nextUser, ...response.data };
    }

    if (typeof profileImage === 'string') {
      if (profileImage) {
        localStorage.setItem(getProfileImageKey(user.id), profileImage);
      } else {
        localStorage.removeItem(getProfileImageKey(user.id));
      }
      nextUser = { ...nextUser, profileImage };
    }

    setUser(nextUser);
    return nextUser;
  };

  const changePassword = async (currentPassword, newPassword) => {
    await authAPI.changePassword(currentPassword, newPassword);
  };

  const withdrawAccount = async () => {
    if (!user?.id) return;
    const currentUser = user;
    await authAPI.deleteAccount();
    clearCurrentUserLocalData(currentUser);
    clearSession();
    setIsLoggedIn(false);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        user,
        loading,
        login,
        signup,
        googleLogin,
        kakaoLogin,
        naverLogin,
        acceptOAuthRedirect,
        logout,
        updateProfile,
        changePassword,
        withdrawAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Context를 직접 만지지 않고 useAuth()로만 쓰게 만드는 커스텀 Hook입니다.
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
