// TypeScript 변경 표시: JSX가 없는 유틸/API 파일이라 .js에서 .ts로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 동작은 유지하고, 이후 함수 인자/반환 타입을 점진적으로 붙일 수 있습니다.
// 초보자 안내: localStorage에 저장하는 키 이름과 저장/복원 도우미 함수를 모아둔 파일입니다.

// 이 파일은 PaperMate의 임시 프론트 저장소 규칙을 한 곳에 모아둔 유틸입니다.
// 지금은 배포 전 단계라 브라우저 내장 저장소인 localStorage를 사용합니다.
// 나중에 FastAPI + MongoDB로 옮길 때도 이 파일의 역할이 백엔드 API 호출로 바뀌면 됩니다.
export const BASE_PROJECTS_KEY = 'papermate.projects.v1';
export const BASE_RECENT_CONVERSATIONS_KEY = 'papermate.recentConversations.v1';
export const BASE_SHARE_ROOM_KEY = 'papermate.shareRoom.v1';
export const ACTIVE_ANALYSIS_SESSION_KEY = 'papermate.activeAnalysisSession.v1';
export const SHARED_PROJECTS_KEY = 'papermate.sharedProjects.v1';
export const SHARED_ROOM_PREFIX = 'papermate.sharedRoom.v1';

const isQuotaExceededError = (error) =>
  error?.name === 'QuotaExceededError' ||
  error?.code === 22 ||
  String(error?.message || '').includes('exceeded the quota');

// 초대코드 검색용 전역 인덱스에는 프로젝트 원본 전체를 넣지 않습니다.
// 이미지 dataUrl 같은 큰 값은 localStorage 한도를 빨리 넘기므로, 공유 검색과 카드 복원에 필요한 가벼운 정보만 남깁니다.
export const normalizeInviteCode = (code = '') => String(code || '').trim();

const compactVisualItems = (items) =>
  Array.isArray(items)
    ? items.slice(0, 12).map((item) => ({
        id: item.id,
        filename: item.filename,
        kind: item.kind,
        name: item.name,
        source: item.source,
        width: item.width,
        height: item.height,
        mimeType: item.mimeType,
        ocrText: item.ocrText,
        previewText: item.previewText,
        dataUrl: item.dataUrl,
      }))
    : undefined;

export const compactProjectForSharedIndex = (project) => ({
  id: project.id,
  source: project.source,
  type: project.type,
  title: project.title,
  owner: project.owner,
  updatedAt: project.updatedAt,
  date: project.date,
  charts: project.charts,
  isHwp: project.isHwp,
  inviteCode: project.inviteCode,
  files: Array.isArray(project.files) ? project.files.slice(0, 20) : [],
  sourceProjects: Array.isArray(project.sourceProjects) ? project.sourceProjects.slice(0, 8) : [],
  visuals: Array.isArray(project.visuals)
    ? project.visuals.slice(0, 10).map((visual) => ({
        id: visual.id,
        kind: visual.kind,
        type: visual.type,
        title: visual.title,
        desc: visual.desc,
        chartType: visual.chartType,
        xAxisKey: visual.xAxisKey,
        columns: Array.isArray(visual.columns) ? visual.columns.slice(0, 20) : undefined,
        series: Array.isArray(visual.series) ? visual.series.slice(0, 12) : undefined,
        data: Array.isArray(visual.data) ? visual.data.slice(0, 80) : undefined,
        theme: visual.theme,
        details: Array.isArray(visual.details) ? visual.details.slice(0, 8) : [],
        rows: Array.isArray(visual.rows) ? visual.rows.slice(0, 8) : undefined,
        items: compactVisualItems(visual.items),
        date: visual.date,
        projectTitle: visual.projectTitle,
      }))
    : [],
  thread: Array.isArray(project.thread)
    ? project.thread.slice(0, 20).map((item) => ({
        id: item.id,
        role: item.role,
        title: item.title,
        text: typeof item.text === 'string' ? item.text.slice(0, 20000) : '',
        kind: item.kind,
        type: item.type,
        chartType: item.chartType,
        xAxisKey: item.xAxisKey,
        columns: Array.isArray(item.columns) ? item.columns.slice(0, 20) : undefined,
        series: Array.isArray(item.series) ? item.series.slice(0, 12) : undefined,
        data: Array.isArray(item.data) ? item.data.slice(0, 80) : undefined,
        theme: item.theme,
        rows: Array.isArray(item.rows) ? item.rows.slice(0, 8) : undefined,
        items: compactVisualItems(item.items),
      }))
    : [],
  discussionImages: Array.isArray(project.discussionImages)
    ? project.discussionImages.slice(0, 8).map((image) => ({
        id: image.id,
        title: image.title,
        time: image.time,
        uploadedBy: image.uploadedBy,
        hasImage: Boolean(image.dataUrl || image.hasImage),
      }))
    : [],
  discussionComments: Array.isArray(project.discussionComments)
    ? project.discussionComments.slice(-50)
    : [],
  createdAt: project.createdAt,
});

export const compactSharedProjects = (projects) =>
  (Array.isArray(projects) ? projects : [])
    .filter((project) => project?.inviteCode)
    .map(compactProjectForSharedIndex)
    .slice(0, 60);

export const upsertProjectByIdOrInvite = (projects, project, limit = 100) => {
  if (!project?.id && !project?.inviteCode) {
    return Array.isArray(projects) ? projects : [];
  }

  const nextProjects = (Array.isArray(projects) ? projects : []).filter(
    (item) => item?.id !== project.id && item?.inviteCode !== project.inviteCode
  );
  return [project, ...nextProjects].slice(0, limit);
};

export const upsertSharedProjectIndex = (project) => {
  if (!project?.inviteCode) return readJson(SHARED_PROJECTS_KEY, []);

  const sharedProjects = readJson(SHARED_PROJECTS_KEY, []);
  const nextSharedProjects = compactSharedProjects(
    upsertProjectByIdOrInvite(sharedProjects, project, 100)
  );
  writeJson(SHARED_PROJECTS_KEY, nextSharedProjects);
  return nextSharedProjects;
};

// userId 또는 username을 키 뒤에 붙여서 계정별 저장 공간을 분리합니다.
// 예: papermate.projects.v1.3, papermate.projects.v1.user14530
const getUserScope = () => {
  try {
    const userId = localStorage.getItem('userId');
    const username = localStorage.getItem('username');
    return encodeURIComponent(userId || username || 'guest');
  } catch {
    return 'guest';
  }
};

export const scopedKey = (baseKey) => `${baseKey}.${getUserScope()}`;

// 개인 데이터는 계정별 키를 사용합니다.
export const getProjectsKey = () => scopedKey(BASE_PROJECTS_KEY);
export const getRecentConversationsKey = () => scopedKey(BASE_RECENT_CONVERSATIONS_KEY);
export const getShareRoomKey = () => scopedKey(BASE_SHARE_ROOM_KEY);
export const getActiveAnalysisSessionKey = () => scopedKey(ACTIVE_ANALYSIS_SESSION_KEY);

// 공유방 데이터는 계정별이 아니라 초대코드별 키를 사용합니다.
// 그래야 다른 아이디로 로그인해도 같은 초대코드 방의 참여자/코멘트를 같이 볼 수 있습니다.
export const getSharedRoomKey = (inviteCode) => `${SHARED_ROOM_PREFIX}.${encodeURIComponent(inviteCode || 'unknown')}`;

// localStorage에는 문자열만 저장할 수 있으므로 JSON.parse로 객체/배열을 복원합니다.
export const readJson = (key, fallback) => {
  try {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : fallback;
  } catch {
    return fallback;
  }
};

// JSON.stringify로 저장한 뒤 CustomEvent를 발생시켜 같은 화면 안의 다른 컴포넌트도 즉시 갱신되게 합니다.
// 브라우저 기본 storage 이벤트는 다른 탭에는 잘 전달되지만, 같은 탭 내부 상태 갱신에는 직접 이벤트가 더 확실합니다.
export const writeJson = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    if (isQuotaExceededError(error) && key === SHARED_PROJECTS_KEY) {
      localStorage.removeItem(key);
      localStorage.setItem(key, JSON.stringify(compactSharedProjects(value)));
    } else {
      console.warn('PaperMate storage write skipped:', key, error);
      return false;
    }
  }
  window.dispatchEvent(new CustomEvent('papermate-storage-updated', { detail: { key } }));
  return true;
};

export const recordMatchesAnyId = (record, ids = []) => {
  const normalizedIds = new Set(
    (Array.isArray(ids) ? ids : [ids]).map((id) => String(id || '').trim()).filter(Boolean)
  );
  if (normalizedIds.size === 0 || !record) return false;

  return [
    record.id,
    record.projectId,
    record.conversationId,
    record.inviteCode,
  ].some((value) => normalizedIds.has(String(value || '').trim()));
};

export const clearActiveAnalysisSessionIfMatched = (ids = []) => {
  const key = getActiveAnalysisSessionKey();
  const activeSession = readJson(key, null);
  if (!recordMatchesAnyId(activeSession, ids)) return false;

  localStorage.removeItem(key);
  window.dispatchEvent(new CustomEvent('papermate-storage-updated', { detail: { key } }));
  return true;
};

// 마이그레이션할 값이 실제로 비어 있지 않은지 확인하는 보조 함수입니다.
// 초대코드 입력으로 프로젝트를 찾기 위한 전역 인덱스입니다.
// 개인 프로젝트 저장소와 별도로, inviteCode가 있는 프로젝트만 모아서 저장합니다.
export const mergeProjectsIntoSharedIndex = (projects) => {
  const projectsWithInvite = Array.isArray(projects)
    ? projects.filter((project) => project?.inviteCode)
    : [];
  if (projectsWithInvite.length === 0) return;

  const sharedProjects = readJson(SHARED_PROJECTS_KEY, []);
  const ownIds = new Set(projectsWithInvite.map((project) => project.id));
  const ownInviteCodes = new Set(projectsWithInvite.map((project) => project.inviteCode));
  const otherSharedProjects = Array.isArray(sharedProjects)
    ? sharedProjects.filter((project) => !ownIds.has(project.id) && !ownInviteCodes.has(project.inviteCode))
    : [];

  writeJson(SHARED_PROJECTS_KEY, compactSharedProjects([...projectsWithInvite, ...otherSharedProjects]));
};

// 예전 버전에서 저장한 키를 현재 로그인 계정의 새 키로 한 번만 옮깁니다.
// 이미 다른 계정으로 이전된 데이터는 다시 복사하지 않도록 migratedTo 표시를 남깁니다.
// TODO: 배포 전에는 반드시 계정별 스코프(getUserScope)로 복구할 것!
// 로그인 직후 호출됩니다.
// 목적: 예전 작업물이 "사라진 것처럼 보이는" 문제를 막고, 현재 계정 저장소로 안전하게 옮기기.
export const migrateCurrentUserStorage = () => {
  if (!localStorage.getItem('userId')) return;

  const projectsKey = getProjectsKey();
  mergeProjectsIntoSharedIndex(readJson(projectsKey, []));
};
