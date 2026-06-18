import React, { ChangeEvent, KeyboardEvent, RefObject, useEffect, useRef, useState } from 'react';
import { FcGoogle } from 'react-icons/fc';
import { RiKakaoTalkFill } from 'react-icons/ri';
import { SiNaver } from 'react-icons/si';
import { FiX } from 'react-icons/fi';
import papermateLogo from '../assets/papermate-logo.png';
import {
  CloseIconButton,
  FigAuthBox,
  ModalOverlay,
  RecommendBody,
  RecommendBox,
  RecommendHeader,
} from './styles/AuthModal.styles';
import { authAPI } from '../services/api';

type ModalMode = 'login' | 'signup' | 'recommend' | null;

interface FormData {
  id?: string;
  pw?: string;
  confirmPw?: string;
}

interface AuthModalProps {
  modalMode: ModalMode;
  setModalMode: (mode: ModalMode) => void;
  formData: FormData;
  onInputChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onLoginSubmit: () => void;
  onSignupSubmit: () => void;
  onGoogleSubmit: (idToken: string) => void;
  onGoogleError: (message: string) => void;
  onKakaoStart: () => void;
  onNaverStart: () => void;
  authError: string | null;
  authLoading: boolean;
}

const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client';
const DEFAULT_GOOGLE_ALLOWED_ORIGINS = [
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:3004',
  'http://127.0.0.1:3004',
];

const getAllowedGoogleOrigins = () => {
  const configured = import.meta.env.VITE_GOOGLE_ALLOWED_ORIGINS || '';
  const origins = configured
    .split(',')
    .map((origin: string) => origin.trim().replace(/\/$/, ''))
    .filter(Boolean);
  return origins.length ? origins : DEFAULT_GOOGLE_ALLOWED_ORIGINS;
};

const loadGoogleScript = () =>
  new Promise<void>((resolve, reject) => {
    const existingScript = document.querySelector<HTMLScriptElement>(
      `script[src="${GOOGLE_SCRIPT_SRC}"]`,
    );

    if (existingScript) {
      if ((window as any).google?.accounts?.id) resolve();
      else existingScript.addEventListener('load', () => resolve(), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = GOOGLE_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Google login script failed to load.'));
    document.head.appendChild(script);
  });

const SocialButtons = ({
  mode,
  googleButtonRef,
  googleClientId,
  googleUnavailableMessage,
  kakaoUnavailableMessage,
  onKakaoClick,
  naverUnavailableMessage,
  onNaverClick,
}: {
  mode: 'login' | 'signup';
  googleButtonRef: RefObject<HTMLDivElement>;
  googleClientId: string;
  googleUnavailableMessage?: string;
  kakaoUnavailableMessage?: string;
  onKakaoClick: () => void;
  naverUnavailableMessage?: string;
  onNaverClick: () => void;
}) => {
  const isSignup = mode === 'signup';

  return (
    <div className="social-stack">
      {googleClientId && !googleUnavailableMessage ? (
        <div className="google-signin-slot" ref={googleButtonRef} aria-label="Google 연동" />
      ) : (
        <button className="social-btn google" type="button" disabled aria-label="Google 연동">
          <FcGoogle />
          <span>{googleUnavailableMessage || 'Google Client ID 필요'}</span>
        </button>
      )}
      <button
        className="social-btn kakao"
        type="button"
        aria-label="카카오톡 연동"
        onClick={onKakaoClick}
        disabled={Boolean(kakaoUnavailableMessage)}
      >
        <RiKakaoTalkFill />
        <span>{kakaoUnavailableMessage || (isSignup ? '카카오톡으로 시작하기' : '카카오톡으로 계속하기')}</span>
      </button>
      <button
        className="social-btn naver"
        type="button"
        aria-label="네이버 연동"
        onClick={onNaverClick}
        disabled={Boolean(naverUnavailableMessage)}
      >
        <SiNaver />
        <span>{naverUnavailableMessage || (isSignup ? '네이버로 시작하기' : '네이버로 계속하기')}</span>
      </button>
    </div>
  );
};

function AuthModal({
  modalMode,
  setModalMode,
  formData,
  onInputChange,
  onLoginSubmit,
  onSignupSubmit,
  onGoogleSubmit,
  onGoogleError,
  onKakaoStart,
  onNaverStart,
  authError,
  authLoading,
}: AuthModalProps) {
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const envGoogleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
  const [runtimeGoogleClientId, setRuntimeGoogleClientId] = useState(envGoogleClientId);
  const [kakaoConfig, setKakaoConfig] = useState({ restApiKey: '', redirectUri: '' });
  const [naverConfig, setNaverConfig] = useState({ clientId: '', redirectUri: '' });
  const googleClientId = runtimeGoogleClientId || envGoogleClientId;
  const googleAllowedOrigins = getAllowedGoogleOrigins();
  const googleOriginAllowed =
    typeof window === 'undefined' || googleAllowedOrigins.includes(window.location.origin);
  const googleUnavailableMessage = !googleClientId
    ? 'Google Client ID 확인 중'
    : !googleOriginAllowed
      ? 'Google 허용 출처 확인 필요'
      : '';
  const kakaoUnavailableMessage = !kakaoConfig.restApiKey ? 'Kakao REST API 키 확인 중' : '';
  const naverUnavailableMessage = !naverConfig.clientId ? 'Naver Client ID 확인 중' : '';

  useEffect(() => {
    if (modalMode !== 'login' && modalMode !== 'signup') return;
    if (!googleClientId) {
      let cancelled = false;

      authAPI.googleConfig()
        .then((response) => {
          if (cancelled) return;
          const clientId = String(response.data?.client_id || '').trim();
          if (clientId) {
            setRuntimeGoogleClientId(clientId);
            return;
          }
          onGoogleError('Google Client ID가 서버 .env에도 설정되지 않았습니다.');
        })
        .catch(() => {
          if (!cancelled) onGoogleError('Google Client ID 설정을 서버에서 불러오지 못했습니다.');
        });

      return () => {
        cancelled = true;
      };
    }

    if (!googleOriginAllowed) {
      onGoogleError(`현재 주소(${window.location.origin})가 Google 로그인 허용 출처에 없습니다.`);
      return;
    }

    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !googleButtonRef.current) return;

        const google = (window as any).google;
        google.accounts.id.initialize({
          client_id: googleClientId,
          callback: (response: { credential?: string }) => {
            if (response.credential) onGoogleSubmit(response.credential);
          },
        });

        googleButtonRef.current.innerHTML = '';
        google.accounts.id.renderButton(googleButtonRef.current, {
          theme: 'outline',
          size: 'large',
          width: 348,
          text: modalMode === 'signup' ? 'signup_with' : 'continue_with',
        });
      })
      .catch(() => {
        onGoogleError('Google 로그인 스크립트를 불러오지 못했습니다.');
        if (googleButtonRef.current) {
          googleButtonRef.current.textContent = 'Google 로그인 버튼을 불러오지 못했습니다.';
        }
      });

    return () => {
      cancelled = true;
    };
  }, [modalMode, googleClientId, googleOriginAllowed, onGoogleSubmit, onGoogleError]);

  useEffect(() => {
    if (modalMode !== 'login' && modalMode !== 'signup') return;

    let cancelled = false;
    authAPI.kakaoConfig()
      .then((response) => {
        if (cancelled) return;
        const restApiKey = String(response.data?.rest_api_key || '').trim();
        const redirectUri = String(response.data?.redirect_uri || '').trim();
        setKakaoConfig({ restApiKey, redirectUri });
        if (!restApiKey) onGoogleError('서버 .env에 KAKAO_REST_API_KEY가 설정되지 않았습니다.');
      })
      .catch(() => {
        if (!cancelled) onGoogleError('카카오 로그인 설정을 서버에서 불러오지 못했습니다.');
      });

    return () => {
      cancelled = true;
    };
  }, [modalMode, onGoogleError]);

  useEffect(() => {
    if (modalMode !== 'login' && modalMode !== 'signup') return;

    let cancelled = false;
    authAPI.naverConfig()
      .then((response) => {
        if (cancelled) return;
        const clientId = String(response.data?.client_id || '').trim();
        const redirectUri = String(response.data?.redirect_uri || '').trim();
        setNaverConfig({ clientId, redirectUri });
        if (!clientId) onGoogleError('서버 .env에 NAVER_CLIENT_ID가 설정되지 않았습니다.');
      })
      .catch(() => {
        if (!cancelled) onGoogleError('네이버 로그인 설정을 서버에서 불러오지 못했습니다.');
      });

    return () => {
      cancelled = true;
    };
  }, [modalMode, onGoogleError]);

  const handleKakaoClick = () => {
    if (!kakaoConfig.restApiKey || !kakaoConfig.redirectUri) {
      onGoogleError('카카오 로그인 설정을 확인해주세요.');
      return;
    }

    onKakaoStart();
    const authorizeUrl = new URL('https://kauth.kakao.com/oauth/authorize');
    authorizeUrl.searchParams.set('response_type', 'code');
    authorizeUrl.searchParams.set('client_id', kakaoConfig.restApiKey);
    authorizeUrl.searchParams.set('redirect_uri', kakaoConfig.redirectUri);
    window.location.href = authorizeUrl.toString();
  };

  const handleNaverClick = () => {
    if (!naverConfig.clientId || !naverConfig.redirectUri) {
      onGoogleError('네이버 로그인 설정을 확인해주세요.');
      return;
    }

    onNaverStart();
    const state =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem('papermate.naverOAuthState', state);

    const authorizeUrl = new URL('https://nid.naver.com/oauth2.0/authorize');
    authorizeUrl.searchParams.set('response_type', 'code');
    authorizeUrl.searchParams.set('client_id', naverConfig.clientId);
    authorizeUrl.searchParams.set('redirect_uri', naverConfig.redirectUri);
    authorizeUrl.searchParams.set('state', state);
    window.location.href = authorizeUrl.toString();
  };

  if (!modalMode) return null;

  const handleEnterSubmit = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Enter' || authLoading) return;
    if (modalMode === 'login') onLoginSubmit();
    if (modalMode === 'signup') onSignupSubmit();
  };

  return (
    <ModalOverlay $show={!!modalMode} onClick={() => setModalMode(null)}>
      {modalMode === 'recommend' && (
        <RecommendBox onClick={(event) => event.stopPropagation()}>
          <CloseIconButton type="button" onClick={() => setModalMode(null)} aria-label="닫기">
            <FiX />
          </CloseIconButton>

          <RecommendHeader>
            <img className="brand-logo" src={papermateLogo} alt="PaperMate" />
          </RecommendHeader>

          <RecommendBody>
            <h3>로그인이 필요한 기능입니다</h3>
            <p>로그인하면 프로젝트, 분석 질문, 자료와 참여 팀을 계정별로 관리할 수 있어요.</p>
            <div className="auth-links">
              <span onClick={() => setModalMode('login')}>Login</span>
              <span onClick={() => setModalMode('signup')}>signup</span>
            </div>
          </RecommendBody>
        </RecommendBox>
      )}

      {(modalMode === 'login' || modalMode === 'signup') && (
        <FigAuthBox onClick={(event) => event.stopPropagation()} onKeyDown={handleEnterSubmit}>
          <CloseIconButton type="button" onClick={() => setModalMode(null)} aria-label="닫기">
            <FiX />
          </CloseIconButton>

          <div className="popup-logo">
            <img className="popup-logo-image" src={papermateLogo} alt="PaperMate" />
          </div>

          <h3 className="popup-title">{modalMode === 'login' ? '로그인' : '회원가입'}</h3>
          <SocialButtons
            mode={modalMode === 'signup' ? 'signup' : 'login'}
            googleButtonRef={googleButtonRef}
            googleClientId={googleClientId}
            googleUnavailableMessage={googleUnavailableMessage}
            kakaoUnavailableMessage={kakaoUnavailableMessage}
            onKakaoClick={handleKakaoClick}
            naverUnavailableMessage={naverUnavailableMessage}
            onNaverClick={handleNaverClick}
          />
          <div className="divider">{modalMode === 'login' ? '또는' : '또는 일반 가입'}</div>

          {modalMode === 'login' ? (
            <>
              <div className="input-group">
                <input name="id" placeholder="아이디" value={formData?.id || ''} onChange={onInputChange} />
                <input name="pw" type="password" placeholder="비밀번호" value={formData?.pw || ''} onChange={onInputChange} />
              </div>

              <div className="action-row">
                <button className="continue-btn" type="button" onClick={onLoginSubmit} disabled={authLoading}>
                  {authLoading ? '로그인 중...' : '로그인'}
                </button>
              </div>
              {authError && <p className="auth-error">{authError}</p>}

              <p className="toggle-guide">
                계정이 없으신가요?
                <button type="button" onClick={() => setModalMode('signup')}>회원가입</button>
              </p>
            </>
          ) : (
            <>
              <div className="input-group">
                <input name="id" placeholder="사용자 아이디" value={formData?.id || ''} onChange={onInputChange} />
                <input name="pw" type="password" placeholder="비밀번호" value={formData?.pw || ''} onChange={onInputChange} />
                <input name="confirmPw" type="password" placeholder="비밀번호 확인" value={formData?.confirmPw || ''} onChange={onInputChange} />
              </div>

              <div className="action-row">
                <button className="continue-btn" type="button" onClick={onSignupSubmit} disabled={authLoading}>
                  {authLoading ? '가입 중...' : '가입하기'}
                </button>
              </div>
              {authError && <p className="auth-error">{authError}</p>}

              <p className="toggle-guide">
                이미 계정이 있으신가요?
                <button type="button" onClick={() => setModalMode('login')}>로그인</button>
              </p>
            </>
          )}
        </FigAuthBox>
      )}
    </ModalOverlay>
  );
}

export default AuthModal;
