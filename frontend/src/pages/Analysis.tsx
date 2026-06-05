// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 JS 로직은 유지하면서 함수 인자와 화면 props에 실제 타입을 붙여 TypeScript 검사를 통과하게 했습니다.
// 초보자 안내: 사용자가 실제로 보게 되는 한 화면 단위의 React 페이지 컴포넌트입니다.

import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FiBarChart2, FiFileText, FiGrid, FiImage, FiPaperclip, FiRefreshCcw } from 'react-icons/fi';
import {
  AiRow,
  BottomPromptInput,
  Container,
  MainQAEngine,
  StreamMessageArea,
  TopMenuBar,
  UserRow,
  ModalBackdrop,
} from './styles/Analysis.styles';
import {
  InviteCodePill,
  MainLayout,
  SaveInlinePanel,
  VisualArtifact,
  VisualPanel,
  PreviewModalContainer,
} from './styles/AnalysisLocal.styles';
import { DynamicVisualizer } from '../components/DynamicVisualizer';
import { analysisAPI, projectAPI } from '../services/api';
import {
  getProjectsKey,
  getRecentConversationsKey,
  readJson,
  SHARED_PROJECTS_KEY,
  writeJson,
} from '../utils/storageKeys';

const MAX_PROJECTS = 10;
const MAX_VISUALS = 10;
const MAX_RECENT_CONVERSATIONS = 50;

const visualStorageKinds = new Set(['table', 'graph', 'image', 'chart']);
const isVisualStorageItem = (visual) => visualStorageKinds.has(visual?.kind) || visualStorageKinds.has(visual?.type);
const normalizeVisualId = (id) => String(id || '').replace(/^(thread-|visual-|saved-)+/, '');

const createInviteCode = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  return Array.from({ length: 7 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
};

const formatDate = () => new Date().toLocaleDateString('ko-KR').replace(/. /g, '.').slice(0, -1);
const nowIso = () => new Date().toISOString();
const formatDateTime = (value) => {
  if (!value) return '';
  const text = String(value).trim();
  if (!/[T\s]\d{1,2}:\d{2}/.test(text)) return text;
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;

  const date = parsed.toLocaleDateString('ko-KR').replace(/. /g, '.').slice(0, -1);
  const time = `${String(parsed.getHours()).padStart(2, '0')}:${String(parsed.getMinutes()).padStart(2, '0')}`;
  return `${date} ${time}`;
};
const getAssetTimestamp = (asset) => formatDateTime(asset?.savedAt || asset?.createdAt || asset?.updatedAt || asset?.date);
const getFileKey = (file) => `${file.name}-${file.size}-${file.lastModified || 0}`;
const mergeUniqueFiles = (...fileGroups) => {
  const seen = new Set();
  return fileGroups.flat().filter((file) => {
    const key = getFileKey(file);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};
const isUploadableFile = (file) =>
  (typeof File !== 'undefined' && file instanceof File) ||
  (typeof Blob !== 'undefined' && file instanceof Blob);

const SOURCE_FILE_DB = 'papermate-source-files';
const SOURCE_FILE_STORE = 'sourceFiles';
const ACTIVE_ANALYSIS_SESSION_KEY = 'papermate.activeAnalysisSession.v1';

const getActiveAnalysisSessionKey = () => {
  try {
    return `${ACTIVE_ANALYSIS_SESSION_KEY}.${localStorage.getItem('userId') || localStorage.getItem('username') || 'guest'}`;
  } catch {
    return `${ACTIVE_ANALYSIS_SESSION_KEY}.guest`;
  }
};

const compactIds = (ids: any[] = []) =>
  ids.map((id) => String(id || '').trim()).filter(Boolean).filter((id, index, arr) => arr.indexOf(id) === index);

const openSourceFileDb = () =>
  new Promise<IDBDatabase | null>((resolve) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      resolve(null);
      return;
    }

    const request = window.indexedDB.open(SOURCE_FILE_DB, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(SOURCE_FILE_STORE)) {
        db.createObjectStore(SOURCE_FILE_STORE, { keyPath: 'ownerId' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(null);
  });

const loadSourceFiles = async (ownerIds: string[] = []) => {
  const uniqueOwnerIds = ownerIds.filter(Boolean).filter((id, index, arr) => arr.indexOf(id) === index);
  if (uniqueOwnerIds.length === 0) return [];

  const db = await openSourceFileDb();
  if (!db) return [];

  return new Promise<any[]>((resolve) => {
    const transaction = db.transaction(SOURCE_FILE_STORE, 'readonly');
    const store = transaction.objectStore(SOURCE_FILE_STORE);
    const loadedFiles: any[] = [];
    let pending = uniqueOwnerIds.length;

    const finish = () => {
      pending -= 1;
      if (pending === 0) resolve(mergeUniqueFiles(loadedFiles));
    };

    uniqueOwnerIds.forEach((ownerId) => {
      const request = store.get(ownerId);
      request.onsuccess = () => {
        const files = Array.isArray(request.result?.files) ? request.result.files.map(hydrateStoredSourceFile) : [];
        loadedFiles.push(...files);
        finish();
      };
      request.onerror = finish;
    });
  });
};

const saveSourceFiles = async (ownerIds: string[] = [], files: any[] = []) => {
  const uploadableFiles = files.filter(isUploadableFile);
  const uniqueOwnerIds = ownerIds.filter(Boolean).filter((id, index, arr) => arr.indexOf(id) === index);
  if (uniqueOwnerIds.length === 0 || uploadableFiles.length === 0) return;

  const db = await openSourceFileDb();
  if (!db) return;

  uniqueOwnerIds.forEach((ownerId) => {
    const transaction = db.transaction(SOURCE_FILE_STORE, 'readwrite');
    transaction.objectStore(SOURCE_FILE_STORE).put({
      ownerId,
      files: uploadableFiles.map(toStoredSourceFile),
      updatedAt: nowIso(),
    });
  });
};

const toStoredSourceFile = (file) => ({
  name: file.name || 'document',
  size: file.size,
  type: file.type || '',
  lastModified: file.lastModified || Date.now(),
  blob: file,
});

const hydrateStoredSourceFile = (record) => {
  if (typeof File !== 'undefined' && record instanceof File) return record;
  if (record?.blob instanceof Blob) {
    try {
      return new File([record.blob], record.name || 'document', {
        type: record.type || record.blob.type || '',
        lastModified: record.lastModified || Date.now(),
      });
    } catch {
      const blob = record.blob;
      blob.name = record.name || 'document';
      blob.lastModified = record.lastModified || Date.now();
      return blob;
    }
  }
  return record;
};

const toStoredFiles = (files) =>
  files.map((file) => ({
    id: `${file.name}-${file.size}-${file.lastModified || Date.now()}`,
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: file.lastModified,
  }));

const toStoredThread = (messages) =>
  messages
    .filter((message) => ['ai', 'user', 'asset', 'system'].includes(message.role))
    .map((message, index) => ({
      id: message.id || `thread-${Date.now()}-${index}`,
      role: message.role,
      title: message.title,
      text: message.text || message.title || '',
      rows: message.rows,
      kind: message.kind,
      type: message.type,
      chartType: message.chartType,
      xAxisKey: message.xAxisKey,
      columns: message.columns,
      series: message.series,
      data: message.data,
      theme: message.theme,
      date: message.date,
      time: message.time,
      createdAt: message.createdAt,
      updatedAt: message.updatedAt,
      savedAt: message.savedAt,
    }));

const hasVisualPayload = (message: any = {}) => {
  const data = Array.isArray(message.data) ? message.data : [];
  const rows = Array.isArray(message.rows) ? message.rows : [];
  const columns = Array.isArray(message.columns) ? message.columns : [];
  const series = Array.isArray(message.series) ? message.series : [];
  return data.length > 0 || rows.length > 0 || columns.length > 0 || series.length > 0 || Boolean(message.chartType);
};

const normalizeRestoredThread = (thread: any[] = []) =>
  thread
    .map((message, index) => {
      if (!message) return null;
      const rawType = message.type || message.kind;
      const title = String(message.title || '').trim();
      const text = String(message.text || '').trim();
      const base = {
        ...message,
        id: message.id || `restored-${index}`,
        text,
      };

      if (message.role === 'asset' && (rawType === 'question' || title === '질문')) {
        return { ...base, role: 'user', type: undefined, kind: undefined, title: undefined };
      }
      if (message.role === 'asset' && (rawType === 'answer' || title === 'AI 답변')) {
        return { ...base, role: 'ai', type: undefined, kind: undefined, title: undefined };
      }
      if (message.role === 'asset' && !hasVisualPayload(message)) {
        return text ? { ...base, role: 'ai', type: undefined, kind: undefined, title: undefined } : null;
      }
      if (message.role === 'asset' || hasVisualPayload(message)) {
        return { ...base, role: 'asset' };
      }
      if (message.role === 'ai' || message.role === 'user' || message.role === 'system') {
        return text ? base : null;
      }
      return text ? { ...base, role: 'ai' } : null;
    })
    .filter(Boolean);

const dedupeVisuals = (visuals: any[] = []) => {
  const seen = new Set();
  return visuals.filter((visual) => {
    const key = normalizeVisualId(visual?.id);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const hasMessageContent = (message: any = {}) => {
  if (message.role === 'asset') return hasVisualPayload(message);
  return Boolean(String(message.text || '').trim());
};

const splitMeaningfulLines = (text) =>
  String(text || '')
    .split(/\n+/)
    .map((line) => line.replace(/^[-\d.\s]+/, '').trim())
    .filter((line) => line.length > 8)
    .slice(0, 8);

const isNonEvidenceText = (text = '') => {
  const value = String(text || '');
  return [
    '분석을 시작하려면 파일을 업로드',
    '서버 분석 실패',
    '파일 전송 실패',
    '파일 전송 성공',
    'LLM 없이 로컬 기본 분석',
    '로컬 기본 분석으로 처리했습니다',
    '아직 충분한 문서 텍스트가 없어',
    '아직 발췌할 본문 텍스트가 없습니다',
    '분석할 파일을 업로드해주세요',
    '현재 분석할 문서 본문이 없습니다',
  ].some((pattern) => value.includes(pattern));
};

const getLatestAnalysisText = (messages) => {
  const latest = [...messages]
    .reverse()
    .find((message) => (
      ['ai', 'asset'].includes(message.role) &&
      String(message.text || '').trim() &&
      !isNonEvidenceText(message.text)
    ));
  return latest?.text || '';
};

const splitEvidenceSections = (text = '') => {
  const sectionPattern = /(\[(?:수치 후보|관련 문서 구간|문서별 핵심 근거)\])/g;
  const parts = String(text).split(sectionPattern);
  const main = (parts.shift() || '').trim();
  const evidence = [];

  for (let index = 0; index < parts.length; index += 2) {
    const title = parts[index]?.replace(/^\[|\]$/g, '').trim();
    const body = parts[index + 1]?.trim();
    if (title && body) evidence.push({ title, body });
  }

  return { main, evidence };
};

const removeInlineFileCitations = (text = '') =>
  String(text).replace(/\s*\[[^\]\n]+\.(?:pdf|hwp|hwpx|docx|txt|pptx|xlsx)\]/gi, '').trim();

const parseVisualJsonFromAnswer = (text = '') => {
  const cleaned = String(text).replace(/```json/gi, '').replace(/```/g, '').trim();
  const startIndex = cleaned.search(/[\[{]/);
  if (startIndex < 0) return null;

  const opener = cleaned[startIndex];
  const closer = opener === '{' ? '}' : ']';
  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let index = startIndex; index < cleaned.length; index += 1) {
    const char = cleaned[index];

    if (escaped) {
      escaped = false;
      continue;
    }
    if (char === '\\') {
      escaped = true;
      continue;
    }
    if (char === '"') {
      inString = !inString;
      continue;
    }
    if (inString) continue;

    if (char === opener) depth += 1;
    if (char === closer) depth -= 1;

    if (depth === 0) {
      try {
        const parsed = JSON.parse(cleaned.slice(startIndex, index + 1));
        if (parsed && typeof parsed === 'object') return parsed;
      } catch {
        return null;
      }
    }
  }

  return null;
};

const EvidenceMarkdown = ({ text }) => {
  const { main, evidence } = splitEvidenceSections(text);
  const cleanMain = removeInlineFileCitations(main || text);

  return (
    <>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleanMain}</ReactMarkdown>
      {evidence.length > 0 && (
        <div className="evidence-panel">
          {evidence.map((section) => (
            <details className="evidence-section" key={section.title}>
              <summary>
                <span>{section.title}</span>
                <small>열어서 보기</small>
              </summary>
              <div className="evidence-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.body}</ReactMarkdown>
              </div>
            </details>
          ))}
        </div>
      )}
    </>
  );
};

const buildLocalFallbackAnswer = (question, files, messages) => {
  const sourceText = messages
    .filter((message) => ['ai', 'asset', 'system'].includes(message.role))
    .map((message) => [message.text, message.desc, ...(message.details || []).map((detail) => detail.val)].filter(Boolean).join(' '))
    .filter((text) => !isNonEvidenceText(text))
    .join('\n');
  const lines = splitMeaningfulLines(sourceText);
  const fileNames = files.length > 0 ? files.map((file) => file.name || '업로드 파일') : ['현재 대화 내용'];
  const questionIntro = question
    ? `질문하신 내용은 "${question}"에 관한 분석으로 보입니다. 제가 현재 남아 있는 문서 기록에서 먼저 뽑아볼게요.`
    : '업로드한 문서를 기준으로 핵심 내용을 먼저 정리해볼게요.';

  if (!lines.length) {
    return [
      questionIntro,
      '',
      '현재 분석할 문서 본문이 없습니다.',
      '',
      '[필요한 자료]',
      files.length
        ? `- 선택된 파일: ${fileNames.join(', ')}`
        : '- 파일을 먼저 업로드해야 질문에 맞는 근거 문장을 뽑을 수 있습니다.',
      '- "40대 여성 이동 동향"처럼 통계성 질문은 연령/성별/지역/기간이 들어 있는 표, CSV, PDF, HWPX 같은 원본 자료가 필요합니다.',
      '',
      '[다음 질문 예시]',
      '- 업로드한 문서에서 40대 여성 이동 동향을 요약해줘.',
      '- 40대 여성의 이동 증가/감소 지역을 표로 정리해줘.',
    ].join('\n');
  }

  return [
    questionIntro,
    '',
    'LLM 없이 로컬 기본 분석으로 처리했습니다.',
    '',
    '[핵심 내용 요약]',
    ...(lines.length
      ? lines.slice(0, 4).map((line, index) => `${index + 1}. ${line}`)
      : [
          `1. ${fileNames.join(', ')} 기준으로 분석 준비가 되었습니다.`,
          '2. 아직 충분한 문서 텍스트가 없어 파일명과 기존 대화 중심으로 정리했습니다.',
        ]),
    '',
    '[중요 문장 발췌]',
    ...(lines.length ? lines.slice(0, 6).map((line) => `- ${line}`) : ['- 아직 발췌할 본문 텍스트가 없습니다.']),
    '',
    '[질문 반영]',
    question ? `질문 "${question}"에 맞춰 내용을 우선 정리했습니다.` : '질문이 비어 있어 전체 요약 기준으로 정리했습니다.',
  ].join('\n');
};

interface AnalysisProps {
  projectId?: any;
  projectTitle?: any;
  restoredData?: any;
  newAnalysisSignal?: number;
  clearRestore?: () => void;
  onConversationChange?: (conversationId: any) => void;
  onLoginRequired?: () => void;
}

function AnalysisC({ projectId, projectTitle, restoredData, newAnalysisSignal, clearRestore, onConversationChange, onLoginRequired }: AnalysisProps) {
  const fileInputRef = useRef(null);
  const pendingVisualTypeRef = useRef<'image' | 'graph' | 'table' | null>(null);
  const promptInputRef = useRef(null);
  const scrollRef = useRef(null);
  const compareShellRef = useRef(null);
  const clipMenuRef = useRef(null);
  const sourceObjectUrlsRef = useRef<Record<string, string>>({});
  const sourceResetVersionRef = useRef(0);
  const recentConversationIdRef = useRef(
    restoredData?.conversationId || restoredData?.projectId || projectId || `conversation-${Date.now()}`
  );
  const [savedProjectId, setSavedProjectId] = useState(null);
  const effectiveProjectId = savedProjectId || projectId || restoredData?.projectId;
  const [files, setFiles] = useState([]);
  const [activeFiles, setActiveFiles] = useState([]);
  const [promptText, setPromptText] = useState('');
  const [messages, setMessages] = useState([
    { id: 'intro', role: 'ai', text: '분석을 시작하려면 파일을 업로드한 뒤 질문을 입력하세요.' },
  ]);
  const [visuals, setVisuals] = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [generatedVisuals, setGeneratedVisuals] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSavingProject, setIsSavingProject] = useState(false);
  const [isProjectSaveOpen, setIsProjectSaveOpen] = useState(false);
  const [projectNameInput, setProjectNameInput] = useState('');
  const [selectedVisual, setSelectedVisual] = useState(null);
  const [expandedVisualIds, setExpandedVisualIds] = useState<string[]>([]);
  const [selectedSourceKey, setSelectedSourceKey] = useState('');
  const [sourcePreview, setSourcePreview] = useState({ kind: 'empty', url: '', text: '', message: '' });
  const [sourcePreviewCache, setSourcePreviewCache] = useState<Record<string, any>>({});
  const [sourcePaneWidth, setSourcePaneWidth] = useState(58);
  const [isResizingSource, setIsResizingSource] = useState(false);
  const [isClipMenuOpen, setIsClipMenuOpen] = useState(false);

  const currentInviteCode = currentProject?.inviteCode || restoredData?.inviteCode || '저장 후 생성';
  const sourceFiles = activeFiles;
  const selectedSourceFile = sourceFiles.find((file) => getFileKey(file) === selectedSourceKey) || sourceFiles[0];

  const cacheSourcePreview = (fileKey: string, preview: any) => {
    setSourcePreviewCache((prev) => ({ ...prev, [fileKey]: preview }));
    if (fileKey === selectedSourceKey || !selectedSourceKey) {
      setSourcePreview(preview);
    }
  };

  const revokeSourceObjectUrl = (fileKey: string) => {
    const url = sourceObjectUrlsRef.current[fileKey];
    if (!url) return;
    URL.revokeObjectURL(url);
    delete sourceObjectUrlsRef.current[fileKey];
  };

  const requireLoginForSave = () => {
    if (localStorage.getItem('accessToken')) return false;
    window.alert('저장과 공유 기능은 로그인 후 사용할 수 있습니다.');
    onLoginRequired?.();
    return true;
  };

  const restoreAnalysisSession = (sessionData) => {
    if (!sessionData) return false;
    if (sessionData.conversationId || sessionData.projectId || sessionData.id) {
      recentConversationIdRef.current = sessionData.conversationId || sessionData.projectId || sessionData.id;
    }

    const restoredFiles = Array.isArray(sessionData.files) ? sessionData.files : [];
    const restoredThread = Array.isArray(sessionData.thread) && sessionData.thread.length > 0
      ? sessionData.thread
      : [
          sessionData.q && { id: 'restored-q', role: 'user', text: sessionData.q },
          sessionData.a && { id: 'restored-a', role: 'ai', text: sessionData.a },
        ].filter(Boolean);
    const normalizedThread = normalizeRestoredThread(restoredThread);

    setFiles([]);
    setActiveFiles(restoredFiles);
    const restoreVersion = sourceResetVersionRef.current;
    loadSourceFiles(compactIds([
      sessionData.projectId,
      sessionData.conversationId,
      sessionData.id,
      effectiveProjectId,
      savedProjectId,
      projectId,
      restoredData?.projectId,
      restoredData?.conversationId,
      restoredData?.id,
      recentConversationIdRef.current,
    ])).then((restoredSourceFiles) => {
      if (restoreVersion !== sourceResetVersionRef.current) return;
      if (restoredSourceFiles.length > 0) {
        const restoredKeys = new Set(restoredSourceFiles.map((file) => getFileKey(file)));
        setSourcePreviewCache((prev) => {
          const next = { ...prev };
          restoredKeys.forEach((key) => delete next[key]);
          return next;
        });
        setFiles([]);
        setActiveFiles(restoredSourceFiles);
        setSelectedSourceKey(getFileKey(restoredSourceFiles[0]));
      }
    });
    if (normalizedThread.length > 0) setMessages(normalizedThread);
    setCurrentProject(sessionData);

    const restoredGeneratedVisuals = normalizedThread.filter((msg: any) => msg.role === 'asset' && isVisualStorageItem(msg));
    setGeneratedVisuals(dedupeVisuals(restoredGeneratedVisuals));

    const threadVisualIds = new Set(restoredGeneratedVisuals.map((visual: any) => normalizeVisualId(visual.id)));
    setVisuals(dedupeVisuals((sessionData.visuals || []).filter((visual: any) => isVisualStorageItem(visual) && !threadVisualIds.has(normalizeVisualId(visual.id)))));
    return normalizedThread.length > 0 || restoredFiles.length > 0;
  };

  useEffect(() => {
    if (restoredData) return;
    const navigationEntry = performance.getEntriesByType?.('navigation')?.[0] as PerformanceNavigationTiming | undefined;
    const isPageReload = navigationEntry?.type === 'reload';
    if (!isPageReload && sessionStorage.getItem('papermate.skipActiveAnalysisRestore') === '1') {
      sessionStorage.removeItem('papermate.skipActiveAnalysisRestore');
      return;
    }
    sessionStorage.removeItem('papermate.skipActiveAnalysisRestore');
    restoreAnalysisSession(readJson(getActiveAnalysisSessionKey(), null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!restoredData) return;
    restoreAnalysisSession(restoredData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restoredData]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!isClipMenuOpen) return undefined;

    const handleOutsideClick = (event) => {
      if (clipMenuRef.current?.contains?.(event.target)) return;
      setIsClipMenuOpen(false);
    };

    window.addEventListener('mousedown', handleOutsideClick);
    return () => window.removeEventListener('mousedown', handleOutsideClick);
  }, [isClipMenuOpen]);

  useEffect(() => {
    if (!isResizingSource) return undefined;

    const updateSourcePaneWidth = (clientX: number) => {
      const shell = compareShellRef.current;
      if (!shell) return;
      const rect = shell.getBoundingClientRect();
      const nextWidth = ((clientX - rect.left) / rect.width) * 100;
      setSourcePaneWidth(Math.min(75, Math.max(35, nextWidth)));
    };

    const handleMouseMove = (event) => {
      event.preventDefault();
      updateSourcePaneWidth(event.clientX);
    };

    const handleTouchMove = (event) => {
      const touch = event.touches?.[0];
      if (!touch) return;
      event.preventDefault();
      updateSourcePaneWidth(touch.clientX);
    };

    const stopResize = () => setIsResizingSource(false);

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', stopResize);
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', stopResize);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', stopResize);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', stopResize);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizingSource]);

  useEffect(() => {
    if (sourceFiles.length === 0) {
      setSelectedSourceKey('');
      setSourcePreview({ kind: 'empty', url: '', text: '', message: '' });
      setSourcePreviewCache({});
      return;
    }

    if (!selectedSourceKey || !sourceFiles.some((file) => getFileKey(file) === selectedSourceKey)) {
      setSelectedSourceKey(getFileKey(sourceFiles[0]));
    }
  }, [sourceFiles, selectedSourceKey]);

  useEffect(() => () => {
    Object.values(sourceObjectUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    sourceObjectUrlsRef.current = {};
  }, []);

  useEffect(() => {
    if (!selectedSourceFile) {
      setSourcePreview({ kind: 'empty', url: '', text: '', message: '' });
      return undefined;
    }

    const previewVersion = sourceResetVersionRef.current;
    const isCurrentPreviewWork = () => previewVersion === sourceResetVersionRef.current;
    const fileKey = getFileKey(selectedSourceFile);
    const cachedPreview = sourcePreviewCache[fileKey];
    const canHydratePreview = typeof selectedSourceFile.text === 'function';
    const isStaleStoredMeta =
      canHydratePreview &&
      cachedPreview?.kind === 'meta' &&
      String(cachedPreview.message || '').includes('저장된 기록');
    if (cachedPreview && !isStaleStoredMeta) {
      if (isCurrentPreviewWork()) setSourcePreview(cachedPreview);
      return undefined;
    }

    if (typeof selectedSourceFile.text !== 'function') {
      if (isCurrentPreviewWork()) cacheSourcePreview(fileKey, {
        kind: 'meta',
        url: '',
        text: '',
        message: '저장된 기록에서는 원본 파일 본문을 바로 열 수 없습니다. 파일을 다시 업로드하면 여기서 원본을 함께 볼 수 있습니다.',
      });
      return undefined;
    }

    const filename = selectedSourceFile.name || '';
    const mime = selectedSourceFile.type || '';
    const extension = filename.split('.').pop()?.toLowerCase() || '';
    const isPdf = mime === 'application/pdf' || extension === 'pdf';
    const isImage = mime.startsWith('image/');
    const isText = mime.startsWith('text/') || ['txt', 'csv', 'tsv', 'md', 'json'].includes(extension);
    const isConvertibleDocument = ['hwp', 'hwpx'].includes(extension);

    if (isPdf || isImage) {
      const url = URL.createObjectURL(selectedSourceFile);
      setSourcePreview({ kind: isPdf ? 'pdf' : 'image', url, text: '', message: '', fileKey: getFileKey(selectedSourceFile) });
      return () => URL.revokeObjectURL(url);
    }

    if (isText) {
      let cancelled = false;
      selectedSourceFile.text()
        .then((text) => {
          if (!cancelled && isCurrentPreviewWork()) cacheSourcePreview(fileKey, { kind: 'text', url: '', text: text.slice(0, 20000), message: '', fileKey });
        })
        .catch(() => {
          if (!cancelled && isCurrentPreviewWork()) {
            cacheSourcePreview(fileKey, { kind: 'meta', url: '', text: '', message: '원본 텍스트를 읽지 못했습니다.', fileKey });
          }
        });
      return () => {
        cancelled = true;
      };
    }

    if (isConvertibleDocument) {
      let cancelled = false;
      if (isCurrentPreviewWork()) cacheSourcePreview(fileKey, {
        kind: 'loading',
        url: '',
        text: '',
        message: 'HWP/HWPX 문서를 파싱해 PDF 원본 미리보기를 준비하는 중입니다.',
        fileKey,
      });

      analysisAPI.previewDocument(selectedSourceFile)
        .then((response) => {
          if (cancelled || !isCurrentPreviewWork()) return;
          const pdfBlob = response.data instanceof Blob
            ? response.data
            : new Blob([response.data], { type: 'application/pdf' });
          revokeSourceObjectUrl(fileKey);
          const previewUrl = URL.createObjectURL(pdfBlob);
          sourceObjectUrlsRef.current[fileKey] = previewUrl;
          cacheSourcePreview(fileKey, { kind: 'pdf', url: previewUrl, text: '', message: '', fileKey });
        })
        .catch((error) => {
          if (cancelled || !isCurrentPreviewWork()) return;
          const message = error.response?.data?.detail || error.userMessage || '문서를 PDF 미리보기로 변환하지 못했습니다.';
          cacheSourcePreview(fileKey, { kind: 'meta', url: '', text: '', message, fileKey });
        });

      return () => {
        cancelled = true;
      };
    }

    setSourcePreview({
      kind: 'meta',
      url: '',
      text: '',
      message: '이 형식은 브라우저 안에서 바로 미리보기 어렵습니다. 분석 결과의 근거 구간과 시각화를 나란히 확인해주세요.',
      fileKey,
    });
    return undefined;
    // sourcePreviewCache is intentionally omitted. Cache writes must not cancel
    // an in-flight HWP/HWPX preview conversion.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSourceFile, selectedSourceKey]);

  const copyInviteCode = async () => {
    if (requireLoginForSave()) return;
    if (!currentInviteCode || currentInviteCode === '저장 후 생성') {
      window.alert('프로젝트를 저장하면 초대코드가 생성됩니다.');
      return;
    }
    await navigator.clipboard?.writeText(currentInviteCode);
    window.alert(`초대코드가 복사되었습니다: ${currentInviteCode}`);
  };

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    const pendingVisualType = pendingVisualTypeRef.current;
    pendingVisualTypeRef.current = null;
    event.target.value = '';
    if (selectedFiles.length === 0) return;

    const nextFiles = mergeUniqueFiles(files, selectedFiles);
    if (pendingVisualType) {
      const nextActiveFiles = mergeUniqueFiles(activeFiles, nextFiles);
      setFiles([]);
      setActiveFiles(nextActiveFiles);
      setSelectedSourceKey(getFileKey(selectedFiles[0]));
      saveSourceFiles([recentConversationIdRef.current, effectiveProjectId], nextActiveFiles);
      handleCreateVisualFromFiles(pendingVisualType, nextFiles, nextActiveFiles);
      event.target.value = '';
      window.setTimeout(() => promptInputRef.current?.focus(), 0);
      return;
    }

    setFiles(nextFiles);
    writeJson(getActiveAnalysisSessionKey(), {
      id: recentConversationIdRef.current,
      conversationId: recentConversationIdRef.current,
      projectId: effectiveProjectId || null,
      title: currentProject?.title || projectTitle || restoredData?.projectTitle || '새 분석 대화',
      projectTitle: currentProject?.title || projectTitle || restoredData?.projectTitle,
      question: '',
      date: formatDate(),
      updatedAt: nowIso(),
      inviteCode: currentProject?.inviteCode || restoredData?.inviteCode,
      files: toStoredFiles(activeFiles),
      thread: toStoredThread(messages),
    });
    event.target.value = '';
    window.setTimeout(() => promptInputRef.current?.focus(), 0);
  };

  const handleRemoveFile = (file) => {
    const nextFiles = files.filter((item) => getFileKey(item) !== getFileKey(file));
    setFiles(nextFiles);
  };

  const handleClipFileAdd = () => {
    setIsClipMenuOpen(false);
    fileInputRef.current?.click();
  };

  const handleCreateVisualFromFiles = async (
    visualType: 'image' | 'graph' | 'table',
    selectedFiles: any[] = [],
    nextActiveFiles = activeFiles
  ) => {
    if (isAnalyzing) return;

    const labelMap = {
      image: '이미지',
      graph: '그래프',
      table: '표',
    };
    const requestFiles = selectedFiles.filter(isUploadableFile);
    const analysisText = getLatestAnalysisText(messages);
    const label = labelMap[visualType];
    const requestMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: `${label} 만들어줘`,
      createdAt: nowIso(),
    };
    const messagesWithRequest = [...messages, requestMessage];

    setMessages(messagesWithRequest);
    setIsAnalyzing(true);

    try {
      const response = await analysisAPI.createVisual(visualType, requestFiles, analysisText);
      const visual = response.data?.visual || response.data;
      const visualAsset = {
        ...visual,
        id: visual?.id || `visual-${Date.now()}`,
        role: 'asset',
        kind: visual?.kind || visualType,
        type: visual?.type || visualType,
        title: visual?.title || `${label} 자료`,
        text: visual?.text || visual?.desc || `${label} 자료를 생성했습니다.`,
        saved: false,
        createdAt: nowIso(),
      };
      const nextMessages = [...messagesWithRequest, visualAsset];
      setMessages(nextMessages);
      setGeneratedVisuals((prev) => [visualAsset, ...prev].slice(0, MAX_VISUALS));
      upsertRecentConversation(nextMessages, requestMessage.text, nextActiveFiles);
    } catch (error) {
      const serverMessage = error.response?.data?.detail || error.userMessage || error.message || `${label} 생성에 실패했습니다.`;
      const nextMessages = [
        ...messagesWithRequest,
        {
          id: `ai-${Date.now()}`,
          role: 'ai',
          text: `${label} 생성 실패: ${serverMessage}`,
          createdAt: nowIso(),
        },
      ];
      setMessages(nextMessages);
      upsertRecentConversation(nextMessages, requestMessage.text, nextActiveFiles);
    } finally {
      setIsAnalyzing(false);
      window.setTimeout(() => promptInputRef.current?.focus(), 0);
    }
  };

  const handleCreateVisualFromMenu = (visualType: 'image' | 'graph' | 'table') => {
    if (isAnalyzing) return;
    pendingVisualTypeRef.current = visualType;
    setIsClipMenuOpen(false);
    fileInputRef.current?.click();
  };

  const handlePromptEnter = (event) => {
    if (event.key !== 'Enter' || event.nativeEvent?.isComposing) return;
    if (event.target?.closest?.('.remove-file')) return;

    event.preventDefault();
    event.stopPropagation();
    const pendingFiles = [...files];
    handleSendMessage(pendingFiles);
  };

  const upsertRecentConversation = (nextMessages, question, nextFiles = files, generatedTitle = null) => {
    const recentConversationsKey = getRecentConversationsKey();
    const savedRecents = readJson(recentConversationsKey, []);
    const conversationId = effectiveProjectId || recentConversationIdRef.current;
    const storedThread = toStoredThread(nextMessages);
    
    // 만약 이미 저장된 제목이 있거나 새로 생성된 제목이 있으면 그걸 우선으로 씀
    const existing = savedRecents.find(item => item.id === conversationId || item.conversationId === conversationId);
    
    const title =
      generatedTitle ||
      (existing && existing.title && existing.title !== question && existing.title !== '새 분석 대화' ? existing.title : null) ||
      currentProject?.title ||
      projectTitle ||
      restoredData?.projectTitle ||
      question ||
      nextFiles[0]?.name?.replace(/\.[^.]+$/, '') ||
      '새 분석 대화';

    writeJson(recentConversationsKey, [
      {
        id: conversationId,
        conversationId,
        projectId: effectiveProjectId || null,
        title,
        question,
        date: formatDate(),
        updatedAt: nowIso(),
        inviteCode: currentProject?.inviteCode || restoredData?.inviteCode,
        files: toStoredFiles(nextFiles),
        thread: storedThread,
      },
      ...(Array.isArray(savedRecents)
        ? savedRecents.filter(
            (item) =>
              item.id !== conversationId &&
              item.conversationId !== conversationId &&
              item.projectId !== conversationId
          )
        : []),
    ].slice(0, MAX_RECENT_CONVERSATIONS));

    writeJson(getActiveAnalysisSessionKey(), {
      id: conversationId,
      conversationId,
      projectId: effectiveProjectId || null,
      title,
      projectTitle: title,
      question,
      date: formatDate(),
      updatedAt: nowIso(),
      inviteCode: currentProject?.inviteCode || restoredData?.inviteCode,
      files: toStoredFiles(nextFiles),
      thread: storedThread,
    });

    const currentId = effectiveProjectId || currentProject?.id || restoredData?.projectId;
    const currentInviteCode = currentProject?.inviteCode || restoredData?.inviteCode;
    if (!currentId && !currentInviteCode) return;

    const projectsKey = getProjectsKey();
    const savedProjects = readJson(projectsKey, []);
    if (!Array.isArray(savedProjects)) return;

    let syncedProject = null;
    const nextProjects = savedProjects.map((project) => {
      const matchesProject =
        (currentId && project.id === currentId) ||
        (currentInviteCode && project.inviteCode === currentInviteCode);
      if (!matchesProject) return project;
      syncedProject = {
        ...project,
        question,
        files: toStoredFiles(nextFiles),
        thread: storedThread,
        updatedAt: nowIso(),
        date: formatDate(),
      };
      return syncedProject;
    });
    if (!syncedProject) return;

    writeJson(projectsKey, nextProjects);
    const sharedProjects = readJson(SHARED_PROJECTS_KEY, []);
    if (Array.isArray(sharedProjects)) {
      writeJson(
        SHARED_PROJECTS_KEY,
        sharedProjects.map((project) => (
          project.id === syncedProject.id || project.inviteCode === syncedProject.inviteCode
            ? { ...project, ...syncedProject }
            : project
        ))
      );
    }
    setCurrentProject((prev) => (prev?.id === syncedProject.id ? { ...prev, ...syncedProject } : prev));
  };

  const handleSendMessage = async (filesToSend = files, overrideQuestion = '') => {
    const nextQuestion = overrideQuestion || promptText.trim();
    const newFiles = [...filesToSend];
    const activeUploadFiles = activeFiles.filter(isUploadableFile);
    const requestFiles = newFiles.length > 0 ? newFiles.filter(isUploadableFile) : activeUploadFiles;
    const pendingFiles = newFiles.length > 0 ? newFiles : [...activeFiles];
    const hasNewUpload = newFiles.length > 0;
    if (!nextQuestion && pendingFiles.length === 0) {
      window.alert('질문을 입력하거나 파일을 선택해주세요.');
      return;
    }

    const question = nextQuestion || '업로드한 문서를 요약해줘';
    setPromptText('');
    if (hasNewUpload) {
      setActiveFiles(pendingFiles);
      setSelectedSourceKey(getFileKey(pendingFiles[0]));
      setFiles([]);
    }

    const fileNames = pendingFiles.map((file) => file.name).filter(Boolean).join(', ');
    const fileMessage = hasNewUpload
      ? { id: `uploaded-files-${Date.now()}`, role: 'system', text: `업로드된 파일: ${fileNames}`, createdAt: nowIso() }
      : null;
    const userMessage = { id: `user-${Date.now()}`, role: 'user', text: question, createdAt: nowIso() };
    const messagesWithQuestion = [...messages, ...(fileMessage ? [fileMessage] : []), userMessage];
    const isNewConversation = recentConversationIdRef.current.startsWith('conversation-');

    if (isNewConversation) {
      recentConversationIdRef.current = `conv-${Date.now()}`;
    }

    saveSourceFiles([recentConversationIdRef.current, effectiveProjectId], pendingFiles);
    setMessages(messagesWithQuestion);
    upsertRecentConversation(messagesWithQuestion, question, pendingFiles);
    if (isNewConversation && typeof onConversationChange === 'function') {
      onConversationChange(recentConversationIdRef.current);
    }

    const hasStoredFileNamesOnly = pendingFiles.length > 0 && requestFiles.length === 0 && !getLatestAnalysisText(messages);
    if (hasStoredFileNamesOnly) {
      const messagesWithAnswer = [
        ...messagesWithQuestion,
        {
          id: `ai-${Date.now()}`,
          role: 'ai',
          text: [
            '저장된 프로젝트에는 파일명만 남아 있고, 브라우저가 다시 전송할 수 있는 원본 파일 본문은 없습니다.',
            '',
            '[다시 필요한 작업]',
            '- 같은 원본 파일을 클립 버튼으로 다시 업로드해주세요.',
            '- 그 다음 질문을 보내면 서버가 문서 본문을 읽어서 요약, 발췌, 수치 후보를 만들 수 있습니다.',
          ].join('\n'),
        },
      ];
      setMessages(messagesWithAnswer);
      upsertRecentConversation(messagesWithAnswer, question, pendingFiles);
      return;
    }

    setIsAnalyzing(true);

    try {
      const response = await analysisAPI.chat(question, requestFiles, {
        conversationId: recentConversationIdRef.current,
      }, getLatestAnalysisText(messages));
      const providerLabel = 'OpenAI';
      const keySourceLabel = response.data?.llm_key_source === 'request'
        ? '화면 입력 키'
        : response.data?.llm_key_source === 'env'
          ? '서버 .env 키'
          : response.data?.llm_key_received
            ? '서버 .env 키'
          : '없음';
      const providerNote = response.data?.provider
        ? response.data?.llm_used
          ? `\n\n분석 엔진: ${providerLabel}${response.data.model ? ` (${response.data.model})` : ''}\nAPI 키: ${keySourceLabel}`
          : `\n\n분석 엔진: 로컬 기본 분석\n선택 Provider: ${providerLabel}\nAPI 키: ${keySourceLabel}${response.data?.llm_error && response.data.llm_error !== 'No grounded document context' ? `\nLLM 호출 실패: ${response.data.llm_error}` : ''}`
        : '';
      const answer = response.data?.answer || response.data?.summary || buildLocalFallbackAnswer(question, pendingFiles, messages);
      const successMessage = hasNewUpload
        ? { id: `upload-success-${Date.now()}`, role: 'system', text: `파일 전송 성공: ${fileNames}`, createdAt: nowIso() }
        : null;
      const suggestedQuestions = response.data?.suggested_questions || [];

      let parsedAssetData = null;
      let isJsonAsset = false;
      try {
        parsedAssetData = parseVisualJsonFromAnswer(answer);
        if (parsedAssetData) {
          isJsonAsset = true;
        }
      } catch (e) {
        // Not valid JSON
      }

      const messagesWithAnswer = [
        ...messagesWithQuestion,
        ...(successMessage ? [successMessage] : []),
      ];

      if (isJsonAsset) {
        // AI가 응답한 JSON 객체를 그대로 병합하되, 기존 호환성을 위해 role, id, title 보장
        const newVisual = {
          ...parsedAssetData, // AI가 생성한 type, chartType, data 등을 전개
          id: `visual-${Date.now()}`,
          role: 'asset',
          title: parsedAssetData.title || (question.includes('차트') || question.includes('표') || question.includes('비교') || question.includes('그래프') ? question : '데이터 시각화'),
          saved: false,
          createdAt: nowIso(),
          suggestedQuestions,
        };
        messagesWithAnswer.push(newVisual);
        
        // 새로 생성된 visual을 상단 보관함(generatedVisuals)에도 추가
        setGeneratedVisuals((prev) => [newVisual, ...prev].slice(0, MAX_VISUALS));
      } else {
        messagesWithAnswer.push({ id: `ai-${Date.now()}`, role: 'ai', text: `${answer}${providerNote}`, createdAt: nowIso(), suggestedQuestions });
      }

      setMessages(messagesWithAnswer);
      setMessages(messagesWithAnswer);
      upsertRecentConversation(messagesWithAnswer, question, pendingFiles);
      
      // 첫 질문인 경우, 백그라운드에서 AI 채팅방 제목 생성 호출
      if (isNewConversation) {
        analysisAPI.generateChatTitle(question, {
        }, getLatestAnalysisText(messages)).then(res => {
          if (res.data?.title) {
            upsertRecentConversation(messagesWithAnswer, question, pendingFiles, res.data.title);
            // 사이드바 등 다른 컴포넌트가 최신 목록을 알 수 있도록 이벤트 발송
            window.dispatchEvent(new Event('storage'));
          }
        }).catch(err => console.warn('Background title generation failed', err));
      }
      
    } catch (error) {
      const serverMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '알 수 없는 오류가 발생했습니다.';
      const failureMessage = hasNewUpload
        ? { id: `upload-failure-${Date.now()}`, role: 'system', text: `파일 전송 실패: ${serverMessage}`, createdAt: nowIso() }
        : null;
      const messagesWithAnswer = [
        ...messagesWithQuestion,
        ...(failureMessage ? [failureMessage] : []),
        {
          id: `ai-${Date.now()}`,
          role: 'ai',
          text: [`서버 분석 실패: ${serverMessage}`, buildLocalFallbackAnswer(question, pendingFiles, messages)]
            .filter(Boolean)
            .join('\n\n'),
          createdAt: nowIso(),
        },
      ];
      setMessages(messagesWithAnswer);
      upsertRecentConversation(messagesWithAnswer, question, pendingFiles);
    } finally {
      if (hasNewUpload) setFiles([]);
      setIsAnalyzing(false);
    }
  };

  const buildProjectRecord = (title, existingProject = null) => {
    const today = formatDate();
    const savedAt = nowIso();
    const storedVisuals = [...generatedVisuals, ...visuals]
      .filter(isVisualStorageItem)
      .filter((visual, index, arr) => arr.findIndex((item) => item.id === visual.id) === index)
      .map((visual) => ({
        ...visual,
        createdAt: visual.createdAt || savedAt,
        updatedAt: visual.updatedAt || savedAt,
      }))
      .slice(0, MAX_VISUALS);

    return {
      ...(existingProject || {}),
      id: existingProject?.id || effectiveProjectId || `project-${Date.now()}`,
      type: activeFiles.some((file) => file.name?.toLowerCase().endsWith('.hwp') || file.name?.toLowerCase().endsWith('.hwpx')) ? 'HWP' : '분석',
      title,
      owner: localStorage.getItem('username') || 'Guest',
      createdAt: existingProject?.createdAt || savedAt,
      updatedAt: savedAt,
      date: today,
      charts: storedVisuals.length,
      isHwp: activeFiles.some((file) => file.name?.toLowerCase().endsWith('.hwp') || file.name?.toLowerCase().endsWith('.hwpx')),
      inviteCode: existingProject?.inviteCode || restoredData?.inviteCode || createInviteCode(),
      files: toStoredFiles(activeFiles.length > 0 ? activeFiles : files),
      thread: toStoredThread(messages),
      visuals: storedVisuals,
    };
  };

  const persistProject = async (projectRecord) => {
    const projectsKey = getProjectsKey();
    const recentConversationsKey = getRecentConversationsKey();
    const savedProjects = readJson(projectsKey, []);
    const nextProjects = [
      projectRecord,
      ...(Array.isArray(savedProjects) ? savedProjects.filter((project) => project.id !== projectRecord.id) : []),
    ].slice(0, MAX_PROJECTS);

    const savedRecents = readJson(recentConversationsKey, []);
    const lastUserMessage = [...projectRecord.thread].reverse().find((item) => item.role === 'user');
    const nextRecent = {
      id: projectRecord.id,
      projectId: projectRecord.id,
      conversationId: recentConversationIdRef.current,
      title: projectRecord.title,
      question: lastUserMessage?.text || projectRecord.title,
      date: projectRecord.date,
      updatedAt: projectRecord.updatedAt,
      inviteCode: projectRecord.inviteCode,
      files: projectRecord.files,
      thread: projectRecord.thread,
    };

    writeJson(projectsKey, nextProjects);
    writeJson(recentConversationsKey, [
      nextRecent,
      ...(Array.isArray(savedRecents)
        ? savedRecents.filter(
            (item) =>
              item.projectId !== projectRecord.id &&
              item.id !== projectRecord.id &&
              item.id !== recentConversationIdRef.current &&
              item.conversationId !== recentConversationIdRef.current
          )
        : []),
    ].slice(0, MAX_RECENT_CONVERSATIONS));

    const sharedProjects = readJson(SHARED_PROJECTS_KEY, []);
    writeJson(SHARED_PROJECTS_KEY, [
      projectRecord,
      ...(Array.isArray(sharedProjects)
        ? sharedProjects.filter((project) => project.id !== projectRecord.id && project.inviteCode !== projectRecord.inviteCode)
        : []),
    ].slice(0, 100));

    await saveSourceFiles([projectRecord.id, recentConversationIdRef.current], activeFiles);

    const token = localStorage.getItem('accessToken');
    if (token) {
      try {
        await projectAPI.save(projectRecord);
      } catch (error) {
        console.warn('MongoDB project save skipped:', error);
      }
    }
  };

  const openProjectSavePanel = () => {
    if (requireLoginForSave()) return;
    const defaultTitle =
      currentProject?.title ||
      projectTitle ||
      restoredData?.projectTitle ||
      files[0]?.name?.replace(/\.[^.]+$/, '') ||
      '새 분석 프로젝트';
    setProjectNameInput(defaultTitle);
    setIsProjectSaveOpen(true);
  };

  const handleNewAnalysis = () => {
    sourceResetVersionRef.current += 1;
    Object.values(sourceObjectUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    sourceObjectUrlsRef.current = {};
    recentConversationIdRef.current = `conversation-${Date.now()}`;
    setSavedProjectId(null);
    setFiles([]);
    setActiveFiles([]);
    setPromptText('');
    setMessages([{ id: 'intro', role: 'ai', text: '분석을 시작하려면 파일을 업로드한 뒤 질문을 입력하세요.' }]);
    setVisuals([]);
    setCurrentProject(null);
    setGeneratedVisuals([]);
    setIsAnalyzing(false);
    setIsProjectSaveOpen(false);
    setProjectNameInput('');
    setSelectedVisual(null);
    setExpandedVisualIds([]);
    setSelectedSourceKey('');
    setSourcePreview({ kind: 'empty', url: '', text: '', message: '' });
    setSourcePreviewCache({});
    localStorage.removeItem(getActiveAnalysisSessionKey());
    clearRestore?.();
    window.setTimeout(() => promptInputRef.current?.focus(), 0);
  };

  useEffect(() => {
    if (!newAnalysisSignal) return;
    handleNewAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newAnalysisSignal]);

  const handleSaveAnalysisProject = async () => {
    if (isSavingProject) return;
    if (requireLoginForSave()) return;
    const title = projectNameInput.trim();
    if (!title) {
      window.alert('프로젝트명을 입력해주세요.');
      return;
    }

    const savedProjects = readJson(getProjectsKey(), []);
    const existingProject = Array.isArray(savedProjects)
      ? savedProjects.find((project) => project.id === effectiveProjectId)
      : null;
    if (!existingProject && Array.isArray(savedProjects) && savedProjects.length >= MAX_PROJECTS) {
      window.alert('프로젝트는 최대 10개까지 저장됩니다. 새 프로젝트를 저장하려면 기존 프로젝트를 삭제해주세요.');
      return;
    }

    setIsSavingProject(true);
    try {
      const projectRecord = buildProjectRecord(title, existingProject);
      await persistProject(projectRecord);
      setSavedProjectId(projectRecord.id);
      recentConversationIdRef.current = projectRecord.id;
      setCurrentProject(projectRecord);
      setVisuals(projectRecord.visuals);
      setIsProjectSaveOpen(false);
      window.alert('프로젝트 페이지와 최근 대화에 저장되었습니다.');
    } finally {
      setIsSavingProject(false);
    }
  };

  const saveVisualAssetToProject = async (asset) => {
    if (!asset || isSavingProject) return;
    if (requireLoginForSave()) return;
    const savedProjects = readJson(getProjectsKey(), []);
    const existingProject = Array.isArray(savedProjects)
      ? savedProjects.find((project) => project.id === effectiveProjectId)
      : null;
    if (existingProject && (existingProject.visuals || []).filter(isVisualStorageItem).length >= MAX_VISUALS) {
      window.alert('시각화 보관함은 최대 10개까지 저장됩니다. 기존 시각화를 삭제해주세요.');
      return;
    }

    const title =
      existingProject?.title ||
      currentProject?.title ||
      projectTitle ||
      window.prompt('저장할 프로젝트명을 입력하세요.', files[0]?.name?.replace(/\.[^.]+$/, '') || '시각화 분석 프로젝트');
    if (!title?.trim()) return;

    setIsSavingProject(true);
    try {
      const savedAt = nowIso();
      const savedAsset = {
        ...asset,
        saved: true,
        projectTitle: title.trim(),
        date: formatDate(),
        createdAt: asset.createdAt || savedAt,
        savedAt,
        updatedAt: savedAt,
      };
      const projectRecord = buildProjectRecord(title.trim(), existingProject);
      const previouslySavedVisuals = Array.isArray(existingProject?.visuals)
        ? existingProject.visuals.filter(isVisualStorageItem)
        : [];
      projectRecord.visuals = [
        savedAsset,
        ...previouslySavedVisuals.filter((visual) => visual.id !== asset.id),
      ].slice(0, MAX_VISUALS);
      projectRecord.charts = projectRecord.visuals.length;
      await persistProject(projectRecord);
      setSavedProjectId(projectRecord.id);
      setCurrentProject(projectRecord);
      setVisuals(projectRecord.visuals);
      setGeneratedVisuals((prev) => prev.map((visual) => (visual.id === asset.id ? savedAsset : visual)));
      setMessages((prev) => prev.map((message) => (message.id === asset.id ? savedAsset : message)));
      window.alert('프로젝트 시각화 보관함에 저장되었습니다.');
    } finally {
      setIsSavingProject(false);
    }
  };

  const renderVisualPreview = (asset: any) => {
    return <DynamicVisualizer config={asset} fallbackTitle={asset.title} />;
  };

  const toggleVisualExpanded = (visualId: string) => {
    setExpandedVisualIds((prev) =>
      prev.includes(visualId)
        ? prev.filter((item) => item !== visualId)
        : [...prev, visualId]
    );
  };

  const renderVisualArtifact = (asset, compact = false, isModal = false, openOnClick = false) => (
    <VisualArtifact className={`${isModal ? 'is-modal' : ''}${openOnClick ? ' is-clickable' : ''}`}>
      <div className="artifact-head">
        <h4>{asset.title}</h4>
        <div className="artifact-meta">
          <span>{asset.saved ? '저장됨' : '생성됨'}</span>
          {getAssetTimestamp(asset) && <time dateTime={asset.savedAt || asset.createdAt || asset.updatedAt || ''}>{getAssetTimestamp(asset)}</time>}
        </div>
      </div>
      <div
        className="artifact-body"
        onClick={openOnClick ? () => setSelectedVisual(asset) : undefined}
        role={openOnClick ? 'button' : undefined}
        tabIndex={openOnClick ? 0 : undefined}
        onKeyDown={openOnClick ? (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return;
          event.preventDefault();
          setSelectedVisual(asset);
        } : undefined}
      >
        {!compact && <p className="artifact-desc">{asset.text}</p>}
        {renderVisualPreview(asset)}
      </div>
      {!compact && (
        <div className="save-container">
          <button
            type="button"
            className="save-visual"
            onClick={() => saveVisualAssetToProject(asset)}
            disabled={asset.saved || isSavingProject}
          >
            {asset.saved ? '프로젝트에 저장됨' : '프로젝트 시각화 보관함에 저장하기'}
          </button>
        </div>
      )}
    </VisualArtifact>
  );

  const renderVisualLibraryItem = (visual, index) => {
    const visualId = normalizeVisualId(visual.id) || `${visual.title}-${index}`;
    const isLatest = index === 0;
    const isExpanded = isLatest || expandedVisualIds.includes(visualId);

    return (
      <div key={`${visual.id}-${index}`} className={`asset-item${isExpanded ? ' expanded' : ''}`}>
        <button
          type="button"
          className="asset-title-button"
          onClick={() => {
            if (!isLatest) toggleVisualExpanded(visualId);
          }}
          aria-expanded={isExpanded}
        >
          <strong>{visual.title}</strong>
          {!isLatest && <span className="toggle-indicator">{isExpanded ? '접기' : '보기'}</span>}
        </button>
        <span>{visual.saved ? '프로젝트 보관함 저장됨' : '채팅창에 생성됨'}</span>
        {isExpanded && renderVisualArtifact(visual, true, false, true)}
      </div>
    );
  };

  const renderSourcePreview = () => {
    if (!selectedSourceFile) {
      return (
        <div className="source-empty">
          <strong>원본 없음</strong>
          <span>문서를 업로드하면 이 영역에서 원본과 시각화를 나란히 볼 수 있습니다.</span>
        </div>
      );
    }

    if (sourcePreview.kind === 'pdf') {
      return <iframe className="source-frame" key={sourcePreview.fileKey || sourcePreview.url} title={selectedSourceFile.name} src={sourcePreview.url} />;
    }

    if (sourcePreview.kind === 'image') {
      return <img className="source-image" src={sourcePreview.url} alt={selectedSourceFile.name} />;
    }

    if (sourcePreview.kind === 'text') {
      return <pre className="source-text">{sourcePreview.text}</pre>;
    }

    return (
      <div className="source-empty">
        <strong>{selectedSourceFile.name}</strong>
        <span>{sourcePreview.message}</span>
      </div>
    );
  };

  const visibleVisuals = dedupeVisuals([
    ...generatedVisuals,
    ...visuals.filter((visual) => !generatedVisuals.some((item) => normalizeVisualId(item.id) === normalizeVisualId(visual.id))),
  ]);
  const questionTimeline = messages
    .filter((message) => message.role === 'user' && String(message.text || '').trim())
    .map((message, index) => ({
      id: message.id,
      text: String(message.text || '').trim(),
      label: `Q${index + 1}`,
    }));

  const scrollToQuestion = (messageId: string) => {
    const target = document.getElementById(`message-${messageId}`);
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  return (
    <Container>
      <input type="file" ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} multiple />
      <MainLayout>
        <VisualPanel>
          <div
            className={`compare-shell${isResizingSource ? ' is-resizing' : ''}`}
            ref={compareShellRef}
            style={{ '--source-pane-width': `${sourcePaneWidth}%` } as React.CSSProperties}
          >
            <section className="source-pane">
              <div className="panel-head">
                <div>
                  <div className="title">미리보기</div>
                  <p className="hint">업로드한 원본을 보면서 시각화와 바로 비교합니다.</p>
                </div>
              </div>
              {sourceFiles.length > 0 && (
                <div className="source-file-list" aria-label="업로드된 파일 목록">
                  {sourceFiles.map((file) => (
                    <button
                      type="button"
                      key={getFileKey(file)}
                      className={`source-file-item${getFileKey(file) === getFileKey(selectedSourceFile) ? ' active' : ''}`}
                      onClick={() => setSelectedSourceKey(getFileKey(file))}
                      title={file.name}
                    >
                      <FiFileText aria-hidden="true" />
                      <span>{file.name}</span>
                    </button>
                  ))}
                </div>
              )}
              <div className="source-preview">
                {renderSourcePreview()}
              </div>
            </section>

            <div
              className="pane-resizer"
              role="separator"
              aria-label="원본과 시각화 영역 크기 조절"
              aria-orientation="vertical"
              onMouseDown={(event) => {
                event.preventDefault();
                setIsResizingSource(true);
              }}
              onTouchStart={(event) => {
                event.preventDefault();
                setIsResizingSource(true);
              }}
            />
            {isResizingSource && (
              <div
                className="resize-shield"
                aria-hidden="true"
                onMouseMove={(event) => {
                  const shell = compareShellRef.current;
                  if (!shell) return;
                  const rect = shell.getBoundingClientRect();
                  const nextWidth = ((event.clientX - rect.left) / rect.width) * 100;
                  setSourcePaneWidth(Math.min(75, Math.max(35, nextWidth)));
                }}
                onMouseUp={() => setIsResizingSource(false)}
                onMouseLeave={() => setIsResizingSource(false)}
              />
            )}

            <section className="visual-library">
              <div className="panel-head">
                <div>
                  <div className="title">시각화 보관함</div>
                  <p className="hint">채팅으로 생성한 표와 그래프가 여기에 모입니다.</p>
                </div>
              </div>
              <div className="asset-list">
                {visibleVisuals.length === 0 ? (
                  <div className="asset-item">
                    <strong>아직 생성된 자료가 없습니다.</strong>
                    <span>표, 그래프, 비교 시각화를 요청하면 이곳에 쌓입니다.</span>
                  </div>
                ) : visibleVisuals.map((visual, index) => renderVisualLibraryItem(visual, index))}
              </div>
            </section>
          </div>
          <div className="title">시각화 보관함</div>
          <p className="hint">채팅으로 요청해 생성된 표와 그래프가 여기에 모입니다.</p>
          <div className="asset-list">
            {visibleVisuals.length === 0 ? (
              <div className="asset-item">
                <strong>아직 생성된 자료가 없습니다.</strong>
                <span>채팅창에 “표로 정리해줘”, “그래프로 만들어줘”처럼 요청하면 여기에 표시됩니다.</span>
              </div>
            ) : visibleVisuals.map((visual, index) => renderVisualLibraryItem(visual, index))}
          </div>
        </VisualPanel>

        <MainQAEngine>
          <TopMenuBar>
            <h2>AI 분석 Q&amp;A</h2>
            <div className="actions">
              <button type="button" onClick={openProjectSavePanel} disabled={isSavingProject}>
                프로젝트 저장
              </button>
              <button
                type="button"
                className="icon-action"
                onClick={handleNewAnalysis}
                aria-label="새 분석 시작"
                title="새 분석 시작"
              >
                <FiRefreshCcw aria-hidden="true" />
              </button>
              <InviteCodePill type="button" onClick={copyInviteCode} title="클릭하면 초대코드가 복사됩니다.">
                <span>초대코드</span>
                <strong>{currentInviteCode}</strong>
              </InviteCodePill>
            </div>
          </TopMenuBar>

          {isProjectSaveOpen && (
            <SaveInlinePanel>
              <input
                value={projectNameInput}
                placeholder="프로젝트 제목을 입력하세요."
                onChange={(event) => setProjectNameInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') handleSaveAnalysisProject();
                  if (event.key === 'Escape') setIsProjectSaveOpen(false);
                }}
                autoFocus
              />
              <button type="button" className="primary" onClick={handleSaveAnalysisProject} disabled={isSavingProject}>
                {isSavingProject ? '저장 중...' : '저장'}
              </button>
              <button type="button" onClick={() => setIsProjectSaveOpen(false)}>
                취소
              </button>
            </SaveInlinePanel>
          )}

          <StreamMessageArea ref={scrollRef}>
            {questionTimeline.length > 0 && (
              <aside className="question-timeline" aria-label="질문 타임라인">
                {questionTimeline.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => scrollToQuestion(item.id)}
                    title={item.text}
                  >
                    <span>{item.label}</span>
                    <strong>{item.text}</strong>
                  </button>
                ))}
              </aside>
            )}
            {messages.filter(hasMessageContent).map((message) => (
              <div key={message.id} id={`message-${message.id}`} className={message.role === 'user' ? 'message-anchor user-anchor' : 'message-anchor'}>
                {message.role === 'ai' ? (
                  <AiRow>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '80%' }}>
                      <div className="ai-box markdown-body"><EvidenceMarkdown text={message.text} /></div>
                      {message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
                        <div className="suggested-questions">
                          {message.suggestedQuestions.map((q, idx) => (
                            <button 
                              key={idx} 
                              className="suggested-chip" 
                              onClick={() => handleSendMessage(files, q)}
                            >
                              {q}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </AiRow>
                ) : message.role === 'user' ? (
                  <UserRow><div className="user-box">{message.text}</div></UserRow>
                ) : message.role === 'asset' ? (
                  <AiRow>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%', maxWidth: '85%', minWidth: '450px' }}>
                      {renderVisualArtifact(message)}
                      {message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
                        <div className="suggested-questions">
                          {message.suggestedQuestions.map((q: string, idx: number) => (
                            <button 
                              key={idx} 
                              className="suggested-chip" 
                              onClick={() => handleSendMessage(files, q)}
                            >
                              {q}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </AiRow>
                ) : (
                  <div style={{ textAlign: 'center', color: '#94a3b8' }}>{message.text}</div>
                )}
              </div>
            ))}
            {isAnalyzing && <AiRow><div className="ai-box">OpenAI가 문서를 분석하고 있습니다...</div></AiRow>}
          </StreamMessageArea>

          <BottomPromptInput onKeyDownCapture={handlePromptEnter}>
            {files.length > 0 && (
              <div className="file-island-list" aria-label="전송 대기 파일 목록">
                {files.map((file) => (
                  <div className="file-island" key={getFileKey(file)} title={file.name}>
                    <FiFileText aria-hidden="true" />
                    <span>{file.name}</span>
                    <button
                      type="button"
                      className="remove-file"
                      onClick={() => handleRemoveFile(file)}
                      aria-label={`${file.name} 삭제`}
                      title="파일 삭제"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="input-wrapper">
              <div className="clip-menu-wrap" ref={clipMenuRef}>
                <button
                  type="button"
                  className={`clip-upload${isClipMenuOpen ? ' active' : ''}`}
                  onClick={() => setIsClipMenuOpen((prev) => !prev)}
                  aria-label="생성 메뉴 열기"
                  aria-expanded={isClipMenuOpen}
                  title="생성 메뉴"
                >
                  <FiPaperclip aria-hidden="true" />
                </button>
                {isClipMenuOpen && (
                  <div className="clip-action-menu" role="menu" aria-label="생성 메뉴">
                    <button type="button" className="primary-action" role="menuitem" onClick={handleClipFileAdd}>
                      <FiPaperclip aria-hidden="true" />
                      <span>파일 추가</span>
                    </button>
                    <div className="clip-menu-divider" aria-hidden="true" />
                    <button type="button" role="menuitem" onClick={() => handleCreateVisualFromMenu('image')}>
                      <FiImage aria-hidden="true" />
                      <span>이미지 만들기</span>
                    </button>
                    <button type="button" role="menuitem" onClick={() => handleCreateVisualFromMenu('graph')}>
                      <FiBarChart2 aria-hidden="true" />
                      <span>그래프 만들기</span>
                    </button>
                    <button type="button" role="menuitem" onClick={() => handleCreateVisualFromMenu('table')}>
                      <FiGrid aria-hidden="true" />
                      <span>표 만들기</span>
                    </button>
                  </div>
                )}
              </div>
              <input
                ref={promptInputRef}
                value={promptText}
                placeholder={files.length > 0 ? `${files.length}개 파일 기준으로 질문을 입력하세요...` : '분석 질문을 입력하세요...'}
                onChange={(event) => setPromptText(event.target.value)}
              />
              <button type="button" onClick={() => handleSendMessage(files)}>전송</button>
            </div>
          </BottomPromptInput>
        </MainQAEngine>
      </MainLayout>
      
      {selectedVisual && (
        <ModalBackdrop onClick={() => setSelectedVisual(null)}>
          <PreviewModalContainer onClick={(e) => e.stopPropagation()}>
            {renderVisualArtifact(selectedVisual, false, true)}
          </PreviewModalContainer>
        </ModalBackdrop>
      )}
    </Container>
  );
}

export default AnalysisC;
