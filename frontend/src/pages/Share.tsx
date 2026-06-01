// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 JS 로직은 유지하면서 함수 인자와 화면 props에 실제 타입을 붙여 TypeScript 검사를 통과하게 했습니다.
// 초보자 안내: 사용자가 실제로 보게 되는 한 화면 단위의 React 페이지 컴포넌트입니다.

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Container,
  MainTimelineContent,
  TimelineInner,
  ProjectLoadBar,
  SectionTitle,
  TimelineWrapper,
  TimelineNode,
  ResultTable,
  RightCoopPanel,
  MembersBox,
  ChatTimelineFeed,
  TalkBubble,
  FooterInputBox,
  VisualModalOverlay,
  VisualModalPanel,
} from './styles/Share.styles';
import {
  getProjectsKey,
  getRecentConversationsKey,
  getSharedRoomKey,
  getShareRoomKey,
  readJson,
  SHARED_PROJECTS_KEY,
  writeJson,
} from '../utils/storageKeys';
import { getSharedImage, putSharedImage } from '../utils/imageStore';
import { DynamicVisualizer } from '../components/DynamicVisualizer';

// Share 페이지의 새 역할:
// 프로젝트를 고르는 화면이 아니라, 초대코드로 들어온 프로젝트 결과물을 보며 코멘트를 남기는 저장형 토론방입니다.
// 실시간 소켓 채팅은 아니고 localStorage에 프로젝트별 코멘트를 저장해 같은 초대코드 참여자가 다시 읽는 구조입니다.

// 과거 테스트용 더미 프로젝트 ID를 필터링하기 위한 목록입니다.
// 공유 저장소나 로컬 저장소에서 불필요한 테스트 데이터를 제외합니다.
const legacyDummyProjectIds = new Set([
  1,
  2,
  3,
  ['image', 'classification'].join('-'),
  ['nlp', 'research'].join('-'),
  ['paper', 'analysis'].join('-'),
]);

// 공유 토론방에 필요한 기본 상태 구조입니다.
const fallbackRoom = {
  inviteCode: '',
  joinedCode: '',
  mainProjectId: '',
  members: [],
  loadedProjectIds: [],
  comments: [],
};

const asArray = (value: any): any[] => (Array.isArray(value) ? value : []);
const MAX_RECENT_CONVERSATIONS = 50;

// 로컬/공유 프로젝트 목록에서 유효한 프로젝트만 남깁니다.
const sanitizeProjects = (projects) =>
  asArray(projects).filter((project) => project && !legacyDummyProjectIds.has(project.id));

// 저장된 공유 방 데이터를 안전한 형태로 변환합니다.
// 잘못된 값이나 레거시 더미 데이터를 제거합니다.
const sanitizeRoom = (room = fallbackRoom) => ({
  ...fallbackRoom,
  ...(room && typeof room === 'object' ? room : {}),
  loadedProjectIds: asArray(room?.loadedProjectIds).filter((id) => !legacyDummyProjectIds.has(id)),
  members: asArray(room?.members),
  comments: asArray(room?.comments).filter(
    (comment) =>
      comment &&
      ![
        '논문의 정확성을 비교해주신 자료를 저한테 메일로 보내주세요.',
        '네, 알겠습니다.',
      ].includes(comment.text)
  ),
});

const formatTime = () => {
  const now = new Date();
  return `오늘 ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
};

const formatDate = () => new Date().toLocaleDateString('ko-KR').replace(/. /g, '.').slice(0, -1);

// 화면에서 사용할 초대코드를 생성합니다.
const createInviteCode = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  return Array.from({ length: 7 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
};

// 업로드된 이미지를 data URL로 변환합니다.
const readFileAsDataUrl = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

// 공유 저장소에 저장할 때 이미지 데이터 URL은 제거하고 hasImage 정보만 남깁니다.
const stripImageDataUrls = (project) => ({
  ...project,
  discussionImages: asArray(project.discussionImages).map(({ dataUrl, ...image }) => ({
    ...image,
    hasImage: Boolean(dataUrl || image.hasImage),
  })),
});

// 프로젝트 소유자를 여러 후보에서 차례로 찾습니다.
const getProjectOwner = (project, room) =>
  project?.owner ||
  asArray(project?.sourceProjects)[0]?.owner ||
  asArray(project?.discussionImages).find((image) => image?.uploadedBy)?.uploadedBy ||
  asArray(room?.members)[0]?.name ||
  '프로젝트 주인';

const normalizeVisualId = (id) => String(id || '').replace(/^(thread-|visual-|saved-)+/, '');

const isGraphRequestBetter = (text = '') => /그래프|차트|막대|꺾은선|선\s*그래프|graph|chart|line|bar/i.test(String(text));

const looksLikeTimeSeries = (xAxisKey, data = []) => {
  const keyText = String(xAxisKey || '').toLowerCase();
  if (/월|month|date|year|연도|년도|기간|시점|분기|quarter/.test(keyText)) return true;
  return data.some((row) => {
    const label = String(row?.[xAxisKey] ?? '');
    return /^\d{1,2}월$/.test(label) || /^\d{4}[-.]\d{1,2}/.test(label) || /^\d{4}년?$/.test(label);
  });
};

const normalizeSeriesName = (value) => String(value ?? '').trim();

const pivotLongChartData = (data) => {
  if (!Array.isArray(data) || data.length === 0 || typeof data[0] !== 'object') return null;

  const keys = Object.keys(data[0]);
  const xAxisKey =
    keys.find((key) => /월|month|date|기간|시점|분기|quarter/i.test(key)) ||
    keys.find((key) => data.some((row) => /^\d{1,2}월$/.test(String(row?.[key] ?? ''))));
  const groupKey =
    keys.find((key) => key !== xAxisKey && /년|year|source|file|자료|문서|category|group|series/i.test(key)) ||
    keys.find((key) => key !== xAxisKey && data.some((row) => /^(?:\d{4}년?p?|\d{4}p?)$/i.test(String(row?.[key] ?? '').trim())));
  const valueKey = keys.find(
    (key) => key !== xAxisKey && key !== groupKey && data.some((row) => Number.isFinite(Number(row?.[key])))
  );

  if (!xAxisKey || !groupKey || !valueKey) return null;

  const rowMap = new Map();
  const groups = [];
  data.forEach((row) => {
    const xLabel = normalizeSeriesName(row?.[xAxisKey]);
    const groupLabel = normalizeSeriesName(row?.[groupKey]);
    if (!xLabel || !groupLabel) return;
    if (!groups.includes(groupLabel)) groups.push(groupLabel);
    const current = rowMap.get(xLabel) || { [xAxisKey]: xLabel };
    const value = Number(row?.[valueKey]);
    current[groupLabel] = Number.isFinite(value) ? value : null;
    rowMap.set(xLabel, current);
  });

  if (rowMap.size === 0 || groups.length < 2) return null;

  return {
    xAxisKey,
    data: Array.from(rowMap.values()),
    series: groups.map((group, index) => ({
      dataKey: group,
      name: group,
      color: ['#94a3b8', '#64748b', '#0f172a', '#0ea5a4', '#2563eb', '#f59e0b'][index % 6],
      yAxisId: 'left',
    })),
  };
};

const isGraphRequest = (text = '') => /그래프|차트|막대|꺾은선|선\s*그래프|graph|chart/i.test(String(text));

const isIntroMessage = (text = '') =>
  String(text || '').includes('분석을 시작하려면 파일을 업로드하거나 차트를 생성하세요') ||
  String(text || '').includes('분석을 시작하려면 파일을 업로드한 뒤 질문을 입력하세요');

const splitEvidenceSections = (text = '') => {
  const normalizedText = String(text || "")
    .replace(/\[(?:관련\s*문서|관련\s*문서\s*구간)\]/g, "[관련 문서 구간]")
    .replace(/\[(?:문서별\s*핵심\s*(?:근거|발췌))\]/g, "[문서별 핵심 근거]");
  const sectionPattern = /(\[(?:수치 후보|관련 문서 구간|문서별 핵심 근거)\])/g;
  const parts = normalizedText.split(sectionPattern);
  const main = (parts.shift() || '').trim();
  const evidence = [];

  for (let index = 0; index < parts.length; index += 2) {
    const title = parts[index]?.replace(/^\[|\]$/g, '').trim();
    const body = parts[index + 1]?.trim();
    if (title && body) evidence.push({ title, body });
  }

  return { main, evidence };
};

const hasVisualPayload = (asset = {}) => {
  const data = Array.isArray(asset.data) ? asset.data : [];
  const rows = Array.isArray(asset.rows) ? asset.rows : [];
  const columns = Array.isArray(asset.columns) ? asset.columns : [];
  const series = Array.isArray(asset.series) ? asset.series : [];
  return data.length > 0 || rows.length > 0 || columns.length > 0 || series.length > 0;
};

const hasTimelineAssetContent = (asset = {}) => {
  if (!asset) return false;
  if (asset.type === 'question' || asset.type === 'answer') return Boolean(String(asset.text || '').trim());
  if (asset.type === 'visual') return hasVisualPayload(asset);
  if (asset.type === 'image') return Boolean(asset.dataUrl || asset.hasImage);
  return Boolean(String(asset.text || '').trim()) || hasVisualPayload(asset);
};

const coerceGraphAsset = (asset, promptText = '') => {
  if (!isGraphRequestBetter(promptText) && !isGraphRequest(promptText)) return asset;
  if (asset.chartType || (Array.isArray(asset.series) && asset.series.length > 0)) return asset;
  const data = Array.isArray(asset.data) && asset.data.length > 0 ? asset.data : [];
  if (data.length === 0 || typeof data[0] !== 'object') return asset;

  const pivoted = pivotLongChartData(data);
  if (pivoted) {
    return {
      ...asset,
      type: 'chart',
      kind: 'chart',
      chartType: 'line',
      xAxisKey: pivoted.xAxisKey,
      data: pivoted.data,
      series: pivoted.series,
    };
  }

  const keys = Object.keys(data[0]);
  const xAxisKey = keys.find((key) => data.some((row) => typeof row?.[key] === 'string')) || keys[0];
  const numericKeys = keys.filter((key) => key !== xAxisKey && data.some((row) => Number.isFinite(Number(row?.[key]))));
  if (numericKeys.length === 0) return asset;
  const shouldUseLine = /선|꺾은선|line|추이|월별|연도별|년도별|시계열|trend/i.test(promptText) || looksLikeTimeSeries(xAxisKey, data);

  return {
    ...asset,
    type: 'chart',
    kind: 'chart',
    chartType: /선|꺾은선|line/i.test(promptText) ? 'line' : 'bar',
    xAxisKey,
    chartType: shouldUseLine ? 'line' : 'bar',
    series: numericKeys.slice(0, 6).map((key, index) => ({
      dataKey: key,
      name: key,
      color: ['#94a3b8', '#64748b', '#0f172a', '#0ea5a4', '#2563eb', '#f59e0b'][index % 6],
      yAxisId: 'left',
    })),
  };
};

function ShareC({ onRestoreTrigger, username = 'Guest', initialProject = null }) {
  const imageInputRef = useRef(null);
  const chatFeedRef = useRef(null);
  const assetStartRef = useRef(null);
  const shouldScrollToAssetsRef = useRef(false);

  // 로컬 저장소에서 사용자의 프로젝트 목록을 불러옵니다.
  const loadOwnProjects = () => {
    const saved = readJson(getProjectsKey(), []);
    return Array.isArray(saved) ? sanitizeProjects(saved) : [];
  };

  // 다른 사용자가 공유한 프로젝트 목록을 불러옵니다.
  const loadSharedProjects = () => {
    const saved = readJson(SHARED_PROJECTS_KEY, []);
    return Array.isArray(saved) ? sanitizeProjects(saved) : [];
  };

  // 마지막으로 사용 중이던 공유 토론방 정보를 로드합니다.
  const loadLastRoom = () => {
    const scopedRoom = sanitizeRoom(readJson(getShareRoomKey(), fallbackRoom));
    const lastCode = scopedRoom.inviteCode || scopedRoom.joinedCode;
    return lastCode
      ? sanitizeRoom(readJson(getSharedRoomKey(lastCode), scopedRoom))
      : scopedRoom;
  };

  const [projects, setProjects] = useState(loadOwnProjects);
  const [sharedProjects, setSharedProjects] = useState(loadSharedProjects);
  const [room, setRoom] = useState(loadLastRoom);
  const [activeShareCode, setActiveShareCode] = useState(room.inviteCode || room.joinedCode || '');
  const [selectedProjectId, setSelectedProjectId] = useState(room.loadedProjectIds[0] || '');
  const [supportInviteCode, setSupportInviteCode] = useState('');
  const [typedMsg, setTypedMsg] = useState('');
  const [isComposingMessage, setIsComposingMessage] = useState(false);
  const [notice, setNotice] = useState('');
  const [imageDataUrls, setImageDataUrls] = useState({});
  const [selectedVisualAsset, setSelectedVisualAsset] = useState(null);

  // 로컬 프로젝트와 공유 프로젝트를 합쳐서 하나의 프로젝트 목록으로 만듭니다.
  // 공유본의 이미지를 항상 우선으로 반영합니다.
  const allProjects = useMemo(() => {
    const mergedProjects = new Map();

    asArray(projects).forEach((project) => {
      if (!project?.id) return;
      mergedProjects.set(project.id, project);
    });

    asArray(sharedProjects).forEach((project) => {
      if (!project?.id) return;
      const localProject = mergedProjects.get(project.id) || {};
      // 다른 계정으로 접속했을 때도 이미지/코멘트가 최신 공유본 기준으로 보이도록 공유 저장소 데이터를 우선한다.
      mergedProjects.set(project.id, {
        ...localProject,
        ...project,
        thread: asArray(localProject.thread).length > 0 ? localProject.thread : project.thread,
        visuals: asArray(localProject.visuals).length > 0 ? localProject.visuals : project.visuals,
      });
    });

    return Array.from(mergedProjects.values());
  }, [projects, sharedProjects]);

  const loadedProjects = useMemo(
    () =>
      room.loadedProjectIds
        .map((id) => allProjects.find((project) => project.id === id))
        .filter(Boolean),
    [allProjects, room.loadedProjectIds]
  );

  const activeProject =
    allProjects.find((project) => project.id === room.mainProjectId) ||
    allProjects.find((project) => project.id === selectedProjectId) ||
    loadedProjects[0];
  const activeInviteCode = activeProject?.inviteCode || activeShareCode || '';
  const supportProjects = useMemo(
    () => loadedProjects.filter((project) => project.id !== activeProject?.id),
    [activeProject?.id, loadedProjects]
  );
  const projectOwner = useMemo(() => getProjectOwner(activeProject, room), [activeProject, room]);
  const sortedMembers = useMemo(() => {
    const members = asArray(room.members);
    const ownerMember = members.find((member) => member.name === projectOwner);
    const otherMembers = members.filter((member) => member.name !== projectOwner);
    return ownerMember
      ? [ownerMember, ...otherMembers]
      : [{ id: `owner-${projectOwner}`, name: projectOwner, ownerOnly: true }, ...otherMembers];
  }, [projectOwner, room.members]);

  const projectComments = useMemo(() => {
    const commentsFromProject = asArray(activeProject?.discussionComments);
    const commentsFromRoom = asArray(room.comments).filter(
      (comment) => !activeProject?.id || !comment.projectId || comment.projectId === activeProject.id
    );
    const merged = [...commentsFromProject, ...commentsFromRoom];
    const seen = new Set();
    return merged
      .filter((comment) => {
        if (seen.has(comment.id)) return false;
        seen.add(comment.id);
        return true;
      })
      // 저장형 채팅은 항상 오래된 코멘트가 위, 새 코멘트가 아래에 쌓이도록 정렬한다.
      .sort((a, b) => {
        const aTime = Number(String(a.id).replace('comment-', '')) || 0;
        const bTime = Number(String(b.id).replace('comment-', '')) || 0;
        return aTime - bTime;
      });
  }, [activeProject, room.comments]);

  const collectProjectAssets = useCallback((project, sourceType = 'main') => {
    if (!project) return [];

    const visualIdsFromThread = new Set();
    const visualById = new Map(
      asArray(project.visuals).flatMap((visual) => [
        [visual.id, visual],
        [normalizeVisualId(visual.id), visual],
      ])
    );

    const images = asArray(project.discussionImages).map((image) => ({
      ...image,
      type: 'image',
      dataUrl: image.dataUrl || imageDataUrls[image.id] || '',
      projectId: project.id,
      projectTitle: project.title,
      sourceType,
    }));

    let lastQuestionText = '';
    const threadItems = asArray(project.thread)
      .filter((item) => ['user', 'ai', 'asset'].includes(item.role) || item.rows)
      .filter((item) => !(item.role === 'ai' && isIntroMessage(item.text)))
      .map((item) => {
        const promptText = lastQuestionText;
        if (item.role === 'user') lastQuestionText = item.text || '';
        const mergedItem = {
          ...(visualById.get(item.id) || visualById.get(normalizeVisualId(item.id)) || {}),
          ...item,
        };
        const rawType = mergedItem.type || mergedItem.kind;
        const isVisual = ['chart', 'table'].includes(rawType) || mergedItem.data || mergedItem.columns || mergedItem.series;
        const nextAsset = {
          ...mergedItem,
          id: `thread-${item.id}`,
          type: item.role === 'user'
            ? 'question'
            : item.role === 'ai'
              ? 'answer'
              : isVisual
                ? 'visual'
                : 'result',
          kind: mergedItem.kind || mergedItem.type,
          title: item.role === 'user' ? '질문' : mergedItem.title || (item.role === 'ai' ? 'AI 답변' : '분석 결과'),
          text: mergedItem.text || '',
          rows: mergedItem.rows,
          projectId: project.id,
          projectTitle: project.title,
          sourceType,
        };
        return nextAsset.type === 'visual' ? coerceGraphAsset(nextAsset, promptText) : nextAsset;
      })
      .filter((item) => {
        if (item.type === 'visual') {
          visualIdsFromThread.add(normalizeVisualId(item.id));
        }
        return hasTimelineAssetContent(item);
      });

    const orphanVisuals = asArray(project.visuals)
      .filter((visual) => !visualIdsFromThread.has(normalizeVisualId(visual.id)))
      .map((visual) => ({
        ...visual,
        id: visual.id,
        type: 'visual',
        kind: visual.kind || visual.type || 'chart',
        title: visual.title || '시각화 자료',
        text: visual.desc || '분석 페이지에서 저장된 시각화 자료입니다.',
        details: visual.details || [],
        rows: visual.rows,
        projectId: project.id,
        projectTitle: project.title,
        sourceType,
      }));

    return [...threadItems, ...orphanVisuals, ...images].filter(hasTimelineAssetContent);
  }, [imageDataUrls]);

  const projectAssets = useMemo(() => {
    if (!activeProject) return [];
    return [
      ...supportProjects.flatMap((project) => collectProjectAssets(project, 'support')),
      ...collectProjectAssets(activeProject, 'main'),
    ];
  }, [activeProject, collectProjectAssets, supportProjects]);

  useEffect(() => {
    if (!activeShareCode || !activeProject?.id) return;
    const latestProject =
      allProjects.find((project) => project.id === activeProject.id) ||
      allProjects.find((project) => project.inviteCode === activeProject.inviteCode);
    if (!latestProject) return;
    if (JSON.stringify(latestProject.thread || []) === JSON.stringify(activeProject.thread || [])) return;
    setRoom((prev) => ({
      ...prev,
      mainProjectId: latestProject.id,
      loadedProjectIds: Array.from(new Set([...asArray(prev.loadedProjectIds), latestProject.id])),
    }));
  }, [activeProject?.id, activeProject?.inviteCode, activeProject?.thread, activeShareCode, allProjects]);

  const updateProjectEverywhere = (projectId, updater) => {
    const projectsKey = getProjectsKey();
    const ownProjects = readJson(projectsKey, []);
    const sharedProjects = readJson(SHARED_PROJECTS_KEY, []);
    let updatedProject = null;

    if (Array.isArray(ownProjects)) {
      const nextOwnProjects = asArray(ownProjects).map((project) => {
        if (project.id !== projectId) return project;
        updatedProject = updater(project);
        return updatedProject;
      });
      if (updatedProject) writeJson(projectsKey, nextOwnProjects);
    }

    if (Array.isArray(sharedProjects)) {
      let sharedUpdated = false;
      const nextSharedProjects = asArray(sharedProjects).map((project) => {
        if (project.id !== projectId) return project;
        sharedUpdated = true;
        const nextProject = updater(project);
        updatedProject = nextProject;
        return nextProject;
      });

      if (sharedUpdated) {
        writeJson(SHARED_PROJECTS_KEY, nextSharedProjects);
      } else {
        const sourceProject = updatedProject || activeProject;
        if (sourceProject?.id === projectId) {
          updatedProject = updatedProject || updater(sourceProject);
          writeJson(SHARED_PROJECTS_KEY, [stripImageDataUrls(updatedProject), ...asArray(sharedProjects)].slice(0, 100));
        }
      }
    }

    setProjects(loadOwnProjects());
    setSharedProjects(loadSharedProjects());
    return updatedProject;
  };

  // room 상태가 변경될 때 로컬 저장소에도 업데이트합니다.
  // 활성 초대코드가 있으면 공유 방과 일반 방 둘 다 동기화합니다.
  useEffect(() => {
    const roomKey = activeShareCode ? getSharedRoomKey(activeShareCode) : getShareRoomKey();
    const nextRoom = {
      ...room,
      inviteCode: activeShareCode || room.inviteCode,
      joinedCode: activeShareCode || room.joinedCode,
    };
    if (JSON.stringify(readJson(roomKey, null)) !== JSON.stringify(nextRoom)) {
      writeJson(roomKey, nextRoom);
    }
    if (activeShareCode) {
      writeJson(getShareRoomKey(), {
        ...nextRoom,
        inviteCode: activeShareCode,
        joinedCode: activeShareCode,
      });
    }
  }, [room, activeShareCode]);

  // 다른 탭이나 저장소 이벤트로 프로젝트/공유 방 정보가 바뀌면 동기화합니다.
  useEffect(() => {
    const syncProjects = (event) => {
      const activeRoomKey = activeShareCode ? getSharedRoomKey(activeShareCode) : getShareRoomKey();
      if (event.detail?.key && ![getProjectsKey(), SHARED_PROJECTS_KEY, activeRoomKey].includes(event.detail.key)) return;
      setProjects(loadOwnProjects());
      setSharedProjects(loadSharedProjects());
      if (!event.detail?.key || event.detail.key === activeRoomKey) {
        setRoom(sanitizeRoom(readJson(activeRoomKey, fallbackRoom)));
      }
    };

    window.addEventListener('storage', syncProjects);
    window.addEventListener('papermate-storage-updated', syncProjects);
    return () => {
      window.removeEventListener('storage', syncProjects);
      window.removeEventListener('papermate-storage-updated', syncProjects);
    };
  }, [activeShareCode]);

  // 사용자 이름이나 공유 코드가 바뀌면 최신 프로젝트/방 데이터를 다시 로드합니다.
  useEffect(() => {
    setProjects(loadOwnProjects());
    setSharedProjects(loadSharedProjects());
    if (!activeShareCode) setRoom(loadLastRoom());
  }, [username, activeShareCode]);

  useEffect(() => {
    if (!initialProject?.inviteCode || !initialProject?.projectId) return;

    const normalizedCode = initialProject.inviteCode;
    const sharedRoom = sanitizeRoom(readJson(getSharedRoomKey(normalizedCode), fallbackRoom));
    const nextIds = Array.from(new Set([
      ...asArray(sharedRoom.loadedProjectIds),
      initialProject.projectId,
    ]));
    const alreadyJoined = asArray(sharedRoom.members).some((member) => member.name === username);

    setActiveShareCode(normalizedCode);
    setSelectedProjectId(initialProject.projectId);
    setRoom({
      ...sharedRoom,
      inviteCode: normalizedCode,
      joinedCode: normalizedCode,
      mainProjectId: initialProject.projectId,
      loadedProjectIds: nextIds,
      comments: asArray(sharedRoom.comments),
      members: alreadyJoined ? asArray(sharedRoom.members) : [...asArray(sharedRoom.members), { id: Date.now(), name: username }],
    });
    setNotice(`"${initialProject.projectTitle || '공유 분석'}" 공유 토론방을 불러왔습니다.`);
  }, [initialProject, username]);

  useEffect(() => {
    if (!chatFeedRef.current) return;
    requestAnimationFrame(() => {
      if (!chatFeedRef.current) return;
      chatFeedRef.current.scrollTop = chatFeedRef.current.scrollHeight;
    });
  }, [projectComments]);

  useEffect(() => {
    if (!shouldScrollToAssetsRef.current || !assetStartRef.current) return;
    shouldScrollToAssetsRef.current = false;
    requestAnimationFrame(() => {
      assetStartRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }, [projectAssets.length, room.loadedProjectIds]);

  useEffect(() => {
    const imagesWithData = allProjects.flatMap((project) =>
      asArray(project.discussionImages)
        .filter((image) => image?.id && image?.dataUrl)
        .map((image) => ({ id: image.id, dataUrl: image.dataUrl }))
    );
    if (imagesWithData.length === 0) return;

    Promise.all(imagesWithData.map((image) => putSharedImage(image.id, image.dataUrl))).catch(() => {
      setNotice('이미지 임시 저장소 동기화 중 일부 항목을 저장하지 못했습니다.');
    });
  }, [allProjects]);

  useEffect(() => {
    const missingImages = projectAssets.filter(
      (asset) => asset.type === 'image' && !asset.dataUrl && asset.id && !imageDataUrls[asset.id]
    );
    if (missingImages.length === 0) return;

    let cancelled = false;
    Promise.all(
      missingImages.map(async (asset) => [asset.id, await getSharedImage(asset.id)])
    ).then((entries) => {
      if (cancelled) return;
      const foundImages = Object.fromEntries(entries.filter(([, dataUrl]) => dataUrl));
      if (Object.keys(foundImages).length > 0) {
        setImageDataUrls((prev) => ({ ...prev, ...foundImages }));
      }
    });

    return () => {
      cancelled = true;
    };
  }, [imageDataUrls, projectAssets]);

  const joinWithCode = () => {
    const normalizedCode = room.joinedCode.trim();
    const matchedProject = allProjects.find((project) => project.inviteCode === normalizedCode);

    if (!matchedProject) {
      setNotice('초대코드를 정확히 입력해야 프로젝트 토론방에 참여할 수 있습니다.');
      return;
    }

    const sharedRoom = sanitizeRoom(readJson(getSharedRoomKey(normalizedCode), fallbackRoom));
    const projectCommentIds = new Set(asArray(matchedProject.discussionComments).map((comment) => comment.id));
    const mergedComments = [
      ...asArray(matchedProject.discussionComments),
      ...asArray(sharedRoom.comments).filter((comment) => !projectCommentIds.has(comment.id)),
    ];
    const nextIds = sharedRoom.loadedProjectIds.includes(matchedProject.id)
      ? sharedRoom.loadedProjectIds
      : [...sharedRoom.loadedProjectIds, matchedProject.id];
    const alreadyJoined = asArray(sharedRoom.members).some((member) => member.name === username);

    setActiveShareCode(normalizedCode);
    setSelectedProjectId(matchedProject.id);
    setRoom({
      ...sharedRoom,
      inviteCode: normalizedCode,
      joinedCode: normalizedCode,
      mainProjectId: matchedProject.id,
      loadedProjectIds: nextIds,
      comments: mergedComments,
      members: alreadyJoined ? asArray(sharedRoom.members) : [...asArray(sharedRoom.members), { id: Date.now(), name: username }],
    });
    setNotice(`참여 완료: "${matchedProject.title}" 결과 토론방을 불러왔습니다.`);
  };

  const loadSupportProjectByCode = () => {
    const normalizedCode = supportInviteCode.trim();
    if (!normalizedCode) {
      setNotice('비교할 보조 프로젝트의 초대코드를 입력해주세요.');
      return;
    }

    if (!activeProject) {
      setNotice('먼저 오른쪽 초대코드로 메인 프로젝트 토론방에 참여해주세요.');
      return;
    }

    const supportProject = allProjects.find((project) => project.inviteCode === normalizedCode);
    if (!supportProject) {
      setNotice('보조 프로젝트 초대코드를 찾을 수 없습니다.');
      return;
    }

    if (supportProject.id === activeProject.id) {
      setNotice('메인 프로젝트와 같은 프로젝트입니다. 다른 프로젝트 초대코드를 입력해주세요.');
      return;
    }

    shouldScrollToAssetsRef.current = false;
    setRoom((prev) => ({
      ...prev,
      mainProjectId: activeProject.id,
      loadedProjectIds: Array.from(new Set([...prev.loadedProjectIds, activeProject.id, supportProject.id])),
    }));
    setSupportInviteCode('');
    setNotice(`비교 자료 추가: "${supportProject.title}" 프로젝트 내용을 본문에 붙였습니다.`);
  };

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const imageFiles = Array.from(event.target.files || []).filter((file: File) => file.type.startsWith('image/'));
    event.target.value = '';

    if (!activeProject) {
      setNotice('먼저 초대코드로 프로젝트를 불러온 뒤 이미지를 추가해주세요.');
      return;
    }
    if (imageFiles.length === 0) {
      setNotice('이미지 파일만 추가할 수 있습니다.');
      return;
    }

    const images = await Promise.all(
      imageFiles.map(async (file, index) => ({
        id: `share-image-${Date.now()}-${index}`,
        projectId: activeProject.id,
        title: file.name,
        dataUrl: await readFileAsDataUrl(file),
        time: formatTime(),
        uploadedBy: username,
      }))
    );

    await Promise.all(images.map((image) => putSharedImage(image.id, image.dataUrl)));
    setImageDataUrls((prev) => ({
      ...prev,
      ...Object.fromEntries(images.map((image) => [image.id, image.dataUrl])),
    }));
    const storedImages = images.map(({ dataUrl, ...image }) => ({ ...image, hasImage: true }));

    const updatedProject = updateProjectEverywhere(activeProject.id, (project) => ({
      ...project,
      discussionImages: [...storedImages, ...asArray(project.discussionImages)].slice(0, 30),
      updatedAt: new Date().toLocaleDateString('ko-KR').replace(/. /g, '.').slice(0, -1),
    }));

    shouldScrollToAssetsRef.current = true;
    setRoom((prev) => ({
      ...prev,
      loadedProjectIds: Array.from(new Set([...prev.loadedProjectIds, activeProject.id])),
    }));
    setNotice(`이미지 ${images.length}개를 "${updatedProject?.title || activeProject.title}" 토론 자료에 추가했습니다.`);
  };

  const handleSendComment = () => {
    const text = typedMsg.trim();
    if (!text) return;
    if (!activeProject) {
      setNotice('먼저 초대코드로 프로젝트를 불러온 뒤 코멘트를 작성해주세요.');
      return;
    }

    const nextComment = {
      id: `comment-${Date.now()}`,
      projectId: activeProject.id,
      projectTitle: activeProject.title,
      user: username,
      text,
      time: formatTime(),
    };

    updateProjectEverywhere(activeProject.id, (project) => ({
      ...project,
      discussionComments: [...asArray(project.discussionComments), nextComment],
      updatedAt: new Date().toLocaleDateString('ko-KR').replace(/. /g, '.').slice(0, -1),
    }));

    setRoom((prev) => ({
      ...prev,
      comments: [...asArray(prev.comments).filter((comment) => comment.id !== nextComment.id), nextComment],
    }));
    setTypedMsg('');
  };

  const handleDeleteComment = (commentId) => {
    if (!activeProject) return;

    updateProjectEverywhere(activeProject.id, (project) => ({
      ...project,
      discussionComments: asArray(project.discussionComments).filter(
        (comment) => comment.id !== commentId || comment.user !== username
      ),
    }));

    setRoom((prev) => ({
      ...prev,
      comments: asArray(prev.comments).filter((comment) => comment.id !== commentId || comment.user !== username),
    }));
  };

  const handleContinueProject = () => {
    if (!activeProject || !onRestoreTrigger) return;
    const thread = Array.isArray(activeProject.thread) ? activeProject.thread : [];
    const lastUserMessage = [...thread].reverse().find((item) => item.role === 'user');
    const lastAiMessage = [...thread].reverse().find((item) => item.role === 'ai' || item.role === 'asset');

    onRestoreTrigger({
      projectId: activeProject.id,
      q: lastUserMessage?.text || activeProject.title,
      a: lastAiMessage?.text || '저장된 프로젝트를 이어서 작업합니다.',
      projectTitle: activeProject.title,
      inviteCode: activeProject.inviteCode,
      files: asArray(activeProject.files),
      thread,
    });
  };

  const handleSaveSharedProjectCard = async () => {
    if (!activeProject) {
      setNotice('먼저 초대코드로 메인 프로젝트 토론방에 참여해주세요.');
      return;
    }

    const title = window.prompt('공유 분석 프로젝트 제목을 입력하세요.', `${activeProject.title} 공유 분석`);
    if (!title?.trim()) return;

    const projectId = `shared-analysis-${Date.now()}`;
    const inviteCode = createInviteCode();
    const today = formatDate();
    const supportTitles = supportProjects.map((project) => project.title).join(', ');
    const mergedFiles = Array.from(
      new Set([
        ...asArray(activeProject.files),
        ...supportProjects.flatMap((project) => asArray(project.files)),
      ])
    );
    const savedAssets = projectAssets.map((asset) => ({
      ...asset,
      id: `saved-${asset.id}`,
      role: 'asset',
      title: asset.title,
      text: asset.text || '',
      rows: asset.rows,
      sourceProjectTitle: asset.projectTitle,
      sourceType: asset.sourceType,
    }));

    const sharedProject = {
      id: projectId,
      source: 'shared-discussion',
      type: '공유 분석',
      title: title.trim(),
      updatedAt: today,
      date: today,
      charts: projectAssets.length,
      isHwp: false,
      inviteCode,
      owner: username,
      files: mergedFiles,
      sourceProjects: [
        { id: activeProject.id, title: activeProject.title, inviteCode: activeProject.inviteCode },
        ...supportProjects.map((project) => ({
          id: project.id,
          title: project.title,
          inviteCode: project.inviteCode,
        })),
      ],
      discussionImages: projectAssets
        .filter((asset) => asset.type === 'image')
        .map((asset) => ({
          id: `copied-${asset.id}`,
          title: asset.title,
          dataUrl: asset.dataUrl,
          hasImage: Boolean(asset.dataUrl || asset.hasImage),
          time: asset.time,
          uploadedBy: asset.uploadedBy,
        })),
      discussionComments: projectComments.map((comment) => ({
        ...comment,
        projectId,
        projectTitle: title.trim(),
      })),
      thread: [
        ...(asArray(activeProject.thread).length
          ? asArray(activeProject.thread)
          : [
              {
                id: `user-${projectId}`,
                role: 'user',
                text: `${activeProject.title}${supportTitles ? ` / ${supportTitles}` : ''} 공유 분석 저장`,
              },
              {
                id: `ai-${projectId}`,
                role: 'ai',
                text: `공유 토론방에서 저장한 분석 카드입니다. 자료 ${projectAssets.length}개와 코멘트 ${projectComments.length}개를 포함합니다.`,
              },
            ]),
        ...supportProjects.flatMap((project) => asArray(project.thread)),
        ...savedAssets,
      ],
      visuals: projectAssets
        .filter((asset) => asset.type === 'visual')
        .map((asset) => ({
          ...asset,
          id: `visual-${asset.id}`,
          kind: asset.kind,
          type: asset.kind || asset.type,
          title: asset.title,
          desc: asset.text,
          details: asset.details,
          rows: asset.rows,
          columns: asset.columns,
          series: asset.series,
          data: asset.data,
          chartType: asset.chartType,
          xAxisKey: asset.xAxisKey,
          theme: asset.theme,
          date: today,
          projectId,
          projectTitle: title.trim(),
        })),
      createdAt: new Date().toISOString(),
    };

    await Promise.all(
      sharedProject.discussionImages
        .filter((image) => image.dataUrl)
        .map((image) => putSharedImage(image.id, image.dataUrl))
    );
    setImageDataUrls((prev) => ({
      ...prev,
      ...Object.fromEntries(
        sharedProject.discussionImages
          .filter((image) => image.dataUrl)
          .map((image) => [image.id, image.dataUrl])
      ),
    }));

    const storableSharedProject = stripImageDataUrls(sharedProject);

    const projectsKey = getProjectsKey();
    const savedProjects = readJson(projectsKey, []);
    const nextProjects = [storableSharedProject, ...(Array.isArray(savedProjects) ? savedProjects : [])].slice(0, 10);
    writeJson(projectsKey, nextProjects);

    const sharedProjectsIndex = readJson(SHARED_PROJECTS_KEY, []);
    writeJson(
      SHARED_PROJECTS_KEY,
      [
        storableSharedProject,
        ...(Array.isArray(sharedProjectsIndex)
          ? sharedProjectsIndex.filter((project) => project.id !== projectId && project.inviteCode !== inviteCode)
          : []),
      ].slice(0, 100)
    );

    writeJson(getSharedRoomKey(inviteCode), {
      inviteCode,
      joinedCode: inviteCode,
      mainProjectId: projectId,
      loadedProjectIds: [projectId],
      members: [{ id: Date.now(), name: username, role: 'owner' }],
      comments: storableSharedProject.discussionComments,
    });

    const recentConversationsKey = getRecentConversationsKey();
    const savedRecents = readJson(recentConversationsKey, []);
    const lastUserMessage = [...asArray(storableSharedProject.thread)].reverse().find((item) => item.role === 'user');
    writeJson(recentConversationsKey, [
      {
        id: projectId,
        projectId,
        title: storableSharedProject.title,
        question: lastUserMessage?.text || storableSharedProject.title,
        thread: storableSharedProject.thread,
        inviteCode,
        createdAt: storableSharedProject.createdAt,
      },
      ...(Array.isArray(savedRecents) ? savedRecents.filter((item) => item.projectId !== projectId && item.id !== projectId) : []),
    ].slice(0, MAX_RECENT_CONVERSATIONS));

    setProjects(loadOwnProjects());
    setSharedProjects(loadSharedProjects());
    setNotice(`"${storableSharedProject.title}" 공유 분석 프로젝트 카드를 저장했습니다. 초대코드: ${inviteCode}`);
  };

  const renderVisualPreview = (asset) => {
    if (asset.data || asset.columns || asset.series || ['chart', 'table'].includes(asset.kind || asset.type)) {
      return <DynamicVisualizer config={asset} fallbackTitle={asset.title} />;
    }
    if (asset.kind === 'table') {
      return (
        <div className="mini-visual table">
          <span></span><span></span><span></span>
          <span></span><span></span><span></span>
          <span></span><span></span><span></span>
        </div>
      );
    }
    if (asset.kind === 'graph') {
      return (
        <div className="mini-visual graph">
          <i></i><i></i><i></i><i></i>
        </div>
      );
    }
    return (
      <div className="mini-visual chart">
        <span style={{ height: '34%' }}></span>
        <span style={{ height: '68%' }}></span>
        <span style={{ height: '48%' }}></span>
        <span style={{ height: '82%' }}></span>
      </div>
    );
  };

  const renderCompactAnswer = (text = '') => {
    const { main, evidence } = splitEvidenceSections(text);
    return (
      <>
        {main && <div className="body">{main}</div>}
        {evidence.length > 0 && (
          <div className="answer-evidence-panel">
            {evidence.map((section) => (
              <details className="answer-evidence-section" key={section.title}>
                <summary>
                  <span>{section.title}</span>
                  <b>열어서 보기</b>
                </summary>
                <div className="answer-evidence-content">{section.body}</div>
              </details>
            ))}
          </div>
        )}
      </>
    );
  };

  const renderAssetTable = (rows) => {
    if (!Array.isArray(rows) || rows.length === 0 || !Array.isArray(rows[0])) return null;

    return (
      <ResultTable>
        <thead>
          <tr>
            {rows[0].map((cell, cellIndex) => <th key={`${cell}-${cellIndex}`}>{cell}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.slice(1).filter(Array.isArray).map((row, rowIndex) => (
            <tr key={`${row.join('-')}-${rowIndex}`}>
              {row.map((cell, cellIndex) => <td key={`${cell}-${cellIndex}`}>{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </ResultTable>
    );
  };

  // 페이지 전체 레이아웃: 왼쪽은 프로젝트 토론 자료, 오른쪽은 초대코드 및 댓글 입력 패널.
  return (
    <Container>
      <MainTimelineContent>
        <TimelineInner>
          <div className="header-area">
            <i className="fa-solid fa-comments menu-toggle"></i>
            <h2>{activeProject?.title || '공유 토론방'}</h2>
          </div>

          <ProjectLoadBar>
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleImageUpload}
            />
            <button type="button" className="image-load-btn" onClick={() => imageInputRef.current?.click()}>
              <i className="fa-regular fa-image"></i>
              이미지 불러오기
            </button>
            <div className="support-code-box">
              <input
                className="support-code-input"
                value={supportInviteCode}
                placeholder="비교 프로젝트 초대코드"
                onChange={(event) => setSupportInviteCode(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && loadSupportProjectByCode()}
              />
              <button type="button" className="support-load-btn" onClick={loadSupportProjectByCode}>
                <i className="fa-regular fa-folder-open"></i>
                프로젝트 카드 불러오기
              </button>
            </div>
            <span className="hint">메인 토론방에 보조 프로젝트를 붙여 비교합니다.</span>
          </ProjectLoadBar>

          {activeProject && (
            <div className="share-project-card">
              <div className="tag-row">
                <span className="tag">{activeProject.type || '프로젝트'}</span>
                <span className="invite">초대코드 {activeProject.inviteCode || activeShareCode}</span>
              </div>
              <h3>{activeProject.title}</h3>
              <div className="project-meta">
                <span>{asArray(activeProject.files).length}개 문서</span>
                <span>{asArray(activeProject.thread).length}개 분석 기록</span>
                <span>{projectAssets.length}개 토론 자료</span>
                <span>{supportProjects.length}개 비교 프로젝트</span>
                <span>{projectComments.length}개 코멘트</span>
              </div>
              <div className="project-actions">
                <button type="button" onClick={handleContinueProject}>분석 페이지에서 이어서 작업</button>
                <button type="button" className="save-shared-card" onClick={handleSaveSharedProjectCard}>
                  공유 분석 카드 저장
                </button>
              </div>
            </div>
          )}

          <SectionTitle ref={assetStartRef}>프로젝트 결과 토론 자료</SectionTitle>
          <TimelineWrapper>
            {!activeProject ? (
              <div className="empty-state">오른쪽 초대코드를 입력하면 프로젝트 결과와 토론 기록이 표시됩니다.</div>
            ) : projectAssets.length === 0 ? (
              <div className="empty-state">아직 저장된 결과 자료가 없습니다. 분석 페이지에서 표/차트/그래프를 저장하거나 이미지를 추가해보세요.</div>
            ) : projectAssets.map((asset, index) => (
              <TimelineNode key={`${asset.id}-${index}`} $active={index === 0}>
                <div className="dot"></div>
                <div className="card">
                  <div className={`project-label ${asset.sourceType === 'support' ? 'support' : ''}`}>
                    {asset.sourceType === 'support' ? '비교 프로젝트' : '메인 프로젝트'} · {asset.projectTitle}
                  </div>
                  <h4>{asset.title}</h4>
                  {asset.type === 'question' && (
                    <div className="question-card">{asset.text}</div>
                  )}
                  {asset.type === 'image' && (
                    <img className="discussion-image" src={asset.dataUrl} alt={asset.title} />
                  )}
                  {asset.type === 'visual' && (
                    <button
                      type="button"
                      className="visual-preview visual-preview-button"
                      onClick={() => setSelectedVisualAsset(asset)}
                      aria-label={`${asset.title} 크게 보기`}
                    >
                      {renderVisualPreview(asset)}
                    </button>
                  )}
                  {asset.type === 'answer' && asset.text && (
                    <details className="answer-fold">
                      <summary>
                        <span>{splitEvidenceSections(asset.text).main.replace(/\s+/g, ' ').slice(0, 120)}{splitEvidenceSections(asset.text).main.length > 120 ? '...' : ''}</span>
                        <b>열어서 보기</b>
                      </summary>
                      {renderCompactAnswer(asset.text)}
                    </details>
                  )}
                  {asset.text && !['question', 'visual', 'answer'].includes(asset.type) && <div className="body">{asset.text}</div>}
                  {Array.isArray(asset.details) && asset.details.length > 0 && (
                    <div className="detail-list">
                      {asset.details.map((item, itemIndex) => (
                        <div className="detail-item" key={`${asset.id}-detail-${itemIndex}`}>
                          <span>{item?.lbl || '항목'}</span>
                          <strong>{item?.val || '-'}</strong>
                        </div>
                      ))}
                    </div>
                  )}
                  {asset.type !== 'visual' && renderAssetTable(asset.rows)}
                  {asset.uploadedBy && <div className="meta">{asset.uploadedBy} · {asset.time}</div>}
                </div>
              </TimelineNode>
            ))}
          </TimelineWrapper>
        </TimelineInner>
      </MainTimelineContent>

      <RightCoopPanel $error={notice.includes('정확히')}>
        <div className="invite-help">초대코드로 프로젝트를 불러옵니다</div>
        <div className="code-row top-code">
          <div className="code-label">초대코드</div>
          <input
            className="code-input"
            value={room.joinedCode}
            placeholder={activeInviteCode || '프로젝트 초대코드'}
            onChange={(event) => setRoom((prev) => ({ ...prev, joinedCode: event.target.value }))}
            onKeyDown={(event) => event.key === 'Enter' && joinWithCode()}
          />
          <button className="join-action" type="button" onClick={joinWithCode}>
            입력
          </button>
        </div>
        <div className="notice">{notice}</div>

        <MembersBox>
          <h5>참여 인원</h5>
          {sortedMembers.length === 0 ? (
            <div className="empty">초대코드 입력 후 표시됩니다.</div>
          ) : (
            sortedMembers.map((member) => (
              <div
                className={`m-item ${member.name === projectOwner ? 'owner' : ''}`}
                key={`${member.id}-${member.name}`}
              >
                <i className={member.name === projectOwner ? 'fa-solid fa-crown' : 'fa-regular fa-circle-user'}></i>
                <span>{member.name}</span>
              </div>
            ))
          )}
        </MembersBox>

        <ChatTimelineFeed ref={chatFeedRef}>
          {projectComments.length === 0 ? (
            <div className="chat-empty">프로젝트 결과를 보며 코멘트를 남겨보세요.</div>
          ) : projectComments.map((comment) => (
            <TalkBubble key={comment.id} $isMe={comment.user === username}>
              {comment.user !== username && (
                <div className="user-id">
                  <i className="fa-regular fa-circle-user"></i> {comment.user}
                </div>
              )}
              <div className="msg-row">
                <div className="message-actions">
                  <div className="bubble">{comment.text}</div>
                  {comment.user === username && (
                    <button
                      className="delete-btn"
                      type="button"
                      aria-label="내 코멘트 삭제"
                      onClick={() => handleDeleteComment(comment.id)}
                    >
                      ×
                    </button>
                  )}
                </div>
                <div className="timestamp">{comment.time}</div>
              </div>
            </TalkBubble>
          ))}
        </ChatTimelineFeed>

        <FooterInputBox>
          <input
            type="text"
            placeholder={activeProject ? '프로젝트 결과에 대한 코멘트 작성' : '먼저 초대코드를 입력하세요'}
            value={typedMsg}
            onChange={(event) => setTypedMsg(event.target.value)}
            onCompositionStart={() => setIsComposingMessage(true)}
            onCompositionEnd={() => setIsComposingMessage(false)}
            onKeyDown={(event) => {
              const isComposing = event.nativeEvent.isComposing || isComposingMessage;
              if (event.key === 'Enter' && !isComposing) handleSendComment();
            }}
          />
          <button type="button" onClick={handleSendComment}>
            저장
          </button>
        </FooterInputBox>
      </RightCoopPanel>

      {selectedVisualAsset && (
        <VisualModalOverlay onClick={() => setSelectedVisualAsset(null)}>
          <VisualModalPanel onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <span>{selectedVisualAsset.projectTitle || '공유 프로젝트'}</span>
                <h3>{selectedVisualAsset.title || '시각화 자료'}</h3>
              </div>
              <button type="button" onClick={() => setSelectedVisualAsset(null)} aria-label="닫기">×</button>
            </div>
            <div className="modal-body">
              <DynamicVisualizer config={selectedVisualAsset} fallbackTitle={selectedVisualAsset.title} />
            </div>
          </VisualModalPanel>
        </VisualModalOverlay>
      )}
    </Container>
  );
}

export default ShareC;
