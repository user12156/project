// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 JS 로직은 유지하면서 함수 인자와 화면 props에 실제 타입을 붙여 TypeScript 검사를 통과하게 했습니다.
// 초보자 안내: 사용자가 실제로 보게 되는 한 화면 단위의 React 페이지 컴포넌트입니다.

import React, { useEffect, useMemo, useState } from 'react';
import {
  ProjectsContainer,
  HeaderSection,
  SectionTitleRow,
  VisualSection,
  VisualBoxContainer,
  VisualCard,
  ProjectGrid,
  ProjectCard,
  EmptyCard,
  ModalOverlay,
  ModalContent,
  DrawerBackdrop,
  DrawerContainer
} from './styles/Project.styles';
import { DynamicVisualizer } from '../components/DynamicVisualizer';
import {
  clearActiveAnalysisSessionIfMatched,
  getProjectsKey,
  getRecentConversationsKey,
  getSharedRoomKey,
  getShareRoomKey,
  mergeProjectsIntoSharedIndex,
  readJson,
  recordMatchesAnyId,
  SHARED_PROJECTS_KEY,
  upsertProjectByIdOrInvite,
  writeJson,
} from '../utils/storageKeys';
import { projectAPI } from '../services/api';
import { VisualArtifact } from './styles/AnalysisLocal.styles';

const MAX_PROJECTS = 10;
const MAX_VISUALS = 10;
const defaultProjects = [];

const splitMeaningfulLines = (text) =>
  String(text || '')
    .split(/\n+/)
    .map((line) => line.replace(/^[-\d.\s]+/, '').trim())
    .filter((line) => line.length > 8)
    .slice(0, 8);

const makeVisualRows = (fileNames, lines) => {
  const sources = fileNames.length > 0 ? fileNames : ['업로드 문서'];
  const baseLines = lines.length
    ? lines
    : ['핵심 주제와 연구 목적', '실험 결과와 수치 정보', '방법론 차이점', '추가 확인이 필요한 내용'];

  return Array.from({ length: Math.max(4, Math.min(6, sources.length + baseLines.length - 1)) }, (_, index) => ({
    label: sources[index % sources.length],
    point: baseLines[index % baseLines.length],
    score: Math.max(36, Math.min(96, 88 - index * 7 + ((index % 2) * 9))),
  }));
};

const renderDetailedVisualPreview = (asset: any) => {
  return <DynamicVisualizer config={asset} fallbackTitle={asset.title} />;
};

const makeSafeFilename = (name = 'papermate-report') =>
  String(name)
    .replace(/[\\/:*?"<>|]+/g, '_')
    .replace(/\s+/g, '_')
    .slice(0, 80) || 'papermate-report';

const downloadBlob = (content, filename, type) => {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

const escapeCsvCell = (value) => {
  const text = value == null ? '' : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

const getVisualColumns = (visual, rows) =>
  Array.isArray(visual?.columns) && visual.columns.length > 0
    ? visual.columns.map((column) => ({
        key: column.key,
        label: column.label || column.key,
      }))
    : Array.from(new Set(rows.flatMap((row) => Object.keys(row || {})))).map((key) => ({ key, label: key }));

const getVisualDownloadRows = (visual) => {
  if (Array.isArray(visual?.data) && visual.data.length > 0) return visual.data;
  if (Array.isArray(visual?.rows) && visual.rows.length > 0) return visual.rows;
  if (Array.isArray(visual?.details) && visual.details.length > 0) {
    return visual.details.map((item) => ({
      label: item.lbl || item.label || item.name || '',
      value: item.val || item.value || item.point || '',
    }));
  }
  return [];
};

const wrapCanvasText = (ctx, text, x, y, maxWidth, lineHeight) => {
  const words = String(text || '').split(/\s+/).filter(Boolean);
  let line = '';
  let cursorY = y;

  words.forEach((word) => {
    const nextLine = line ? `${line} ${word}` : word;
    if (ctx.measureText(nextLine).width > maxWidth && line) {
      ctx.fillText(line, x, cursorY);
      line = word;
      cursorY += lineHeight;
    } else {
      line = nextLine;
    }
  });

  if (line) {
    ctx.fillText(line, x, cursorY);
    cursorY += lineHeight;
  }

  return cursorY;
};

const downloadVisualReportPng = (visual) => {
  if (!visual) return;

  const rows = getVisualDownloadRows(visual);
  const columns = getVisualColumns(visual, rows);
  const detailRows = asArray(visual.details).map((item) => [
    item.lbl || item.label || item.name || '세부 정보',
    item.val || item.value || item.point || '',
  ]);
  const width = 1400;
  const rowHeight = 44;
  const tableRows = Math.max(1, Math.min(rows.length, 12));
  const height = Math.max(900, 520 + detailRows.length * 34 + tableRows * rowHeight);
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const left = 70;
  const contentWidth = width - left * 2;
  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(44, 44, width - 88, height - 88);
  ctx.strokeStyle = '#dbe4ef';
  ctx.lineWidth = 2;
  ctx.strokeRect(44, 44, width - 88, height - 88);

  let y = 96;
  ctx.fillStyle = '#0f172a';
  ctx.font = '700 34px Arial, sans-serif';
  y = wrapCanvasText(ctx, visual.title || 'PaperMate 시각화 보고서', left, y, contentWidth, 42) + 12;

  ctx.fillStyle = '#0f766e';
  ctx.font = '700 18px Arial, sans-serif';
  ctx.fillText(`종류: ${visual.kind || visual.type || '-'}   차트 유형: ${visual.chartType || '-'}   저장 일자: ${visual.date || '-'}`, left, y);
  y += 48;

  ctx.fillStyle = '#334155';
  ctx.font = '700 22px Arial, sans-serif';
  ctx.fillText('데이터 분석 요약', left, y);
  y += 34;
  ctx.font = '500 20px Arial, sans-serif';
  ctx.fillStyle = '#475569';
  y = wrapCanvasText(ctx, visual.desc || visual.text || '저장된 분석 요약이 없습니다.', left, y, contentWidth, 30) + 24;

  if (detailRows.length > 0) {
    ctx.fillStyle = '#334155';
    ctx.font = '700 22px Arial, sans-serif';
    ctx.fillText('세부 정보 필드', left, y);
    y += 28;
    ctx.font = '500 18px Arial, sans-serif';
    detailRows.forEach(([label, value]) => {
      ctx.fillStyle = '#64748b';
      ctx.fillText(String(label), left, y);
      ctx.fillStyle = '#1e293b';
      ctx.fillText(String(value), left + 260, y);
      y += 30;
    });
    y += 16;
  }

  ctx.fillStyle = '#334155';
  ctx.font = '700 22px Arial, sans-serif';
  ctx.fillText('보고서 데이터', left, y);
  y += 22;

  if (rows.length > 0 && columns.length > 0) {
    const colWidth = contentWidth / columns.length;
    ctx.font = '700 16px Arial, sans-serif';
    columns.forEach((column, index) => {
      ctx.fillStyle = '#0f766e';
      ctx.fillRect(left + index * colWidth, y, colWidth, rowHeight);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(String(column.label), left + index * colWidth + 12, y + 28);
    });
    y += rowHeight;

    ctx.font = '500 15px Arial, sans-serif';
    rows.slice(0, 12).forEach((row, rowIndex) => {
      columns.forEach((column, index) => {
        ctx.fillStyle = rowIndex % 2 === 0 ? '#ffffff' : '#f8fafc';
        ctx.fillRect(left + index * colWidth, y, colWidth, rowHeight);
        ctx.strokeStyle = '#e2e8f0';
        ctx.strokeRect(left + index * colWidth, y, colWidth, rowHeight);
        ctx.fillStyle = '#1e293b';
        ctx.fillText(String(row?.[column.key] ?? '-').slice(0, 26), left + index * colWidth + 12, y + 28);
      });
      y += rowHeight;
    });

    if (rows.length > 12) {
      ctx.fillStyle = '#64748b';
      ctx.font = '500 16px Arial, sans-serif';
      ctx.fillText(`외 ${rows.length - 12}개 행은 CSV 데이터 다운로드에서 확인할 수 있습니다.`, left, y + 28);
    }
  } else {
    ctx.fillStyle = '#64748b';
    ctx.font = '500 18px Arial, sans-serif';
    ctx.fillText('저장된 표/그래프 행 데이터가 없습니다.', left, y + 28);
  }

  const baseName = makeSafeFilename(visual.title || visual.kind || 'visual-report');
  const link = document.createElement('a');
  link.download = `${baseName}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
};

const downloadVisualReportData = (visual) => {
  if (!visual) return;

  const rows = getVisualDownloadRows(visual);
  const baseName = makeSafeFilename(visual.title || visual.kind || 'visual-report');

  if (rows.length > 0) {
    const columns = Array.isArray(visual.columns) && visual.columns.length > 0
      ? visual.columns.map((column) => ({
          key: column.key,
          label: column.label || column.key,
        }))
      : Array.from(new Set(rows.flatMap((row) => Object.keys(row || {})))).map((key) => ({ key, label: key }));

    const detailRows = asArray(visual.details).map((item) => [
      item.lbl || item.label || item.name || '세부 정보',
      item.val || item.value || item.point || '',
    ]);
    const metadataRows = [
      ['제목', visual.title || ''],
      ['종류', visual.kind || visual.type || ''],
      ['차트 유형', visual.chartType || ''],
      ['저장 일자', visual.date || ''],
      ['데이터 분석 요약', visual.desc || visual.text || ''],
      ...detailRows,
    ];
    const csv = [
      ['보고서 정보', '내용'].map(escapeCsvCell).join(','),
      ...metadataRows.map((row) => row.map(escapeCsvCell).join(',')),
      '',
      columns.map((column) => escapeCsvCell(column.label)).join(','),
      ...rows.map((row) => columns.map((column) => escapeCsvCell(row?.[column.key])).join(',')),
    ].join('\n');
    downloadBlob(`\uFEFF${csv}`, `${baseName}.csv`, 'text/csv;charset=utf-8');
    return;
  }

  const json = JSON.stringify(
    {
      title: visual.title,
      kind: visual.kind || visual.type,
      chartType: visual.chartType,
      description: visual.desc || visual.text,
      savedAt: visual.date,
      visual,
    },
    null,
    2
  );
  downloadBlob(json, `${baseName}.json`, 'application/json;charset=utf-8');
};

const legacyDummyProjectTitles = [
  '이미지 분류',
  '자연어 처리',
  '논문 분석 처리',
  '딥러닝 이미지 분류 연구 비교',
];

const asArray = (value) => (Array.isArray(value) ? value : []);

const sanitizeProjects = (projects) =>
  asArray(projects).filter((project) => project && !legacyDummyProjectTitles.includes(project.title));

const pickFirstArray = (...values) => values.find((value) => Array.isArray(value) && value.length > 0) || [];

const buildThreadFromSummary = (source) => {
  if (!source) return [];
  return [
    (source.q || source.question) && {
      id: `${source.id || source.projectId || 'restored'}-q`,
      role: 'user',
      text: source.q || source.question,
    },
    (source.a || source.answer || source.summary || source.analysis) && {
      id: `${source.id || source.projectId || 'restored'}-a`,
      role: 'ai',
      text: source.a || source.answer || source.summary || source.analysis,
    },
  ].filter(Boolean);
};

const findRecentConversationForProject = (project) => {
  const recentConversations = readJson(getRecentConversationsKey(), []);
  return asArray(recentConversations).find(
    (item) =>
      item.projectId === project.id ||
      item.id === project.id ||
      item.conversationId === project.id ||
      item.inviteCode === project.inviteCode ||
      (project.title && (item.title === project.title || item.projectTitle === project.title))
  );
};

const getProjectThread = (project, matchedRecent = null) => {
  const directThread = pickFirstArray(
    project.thread,
    project.messages,
    project.chat,
    project.conversation,
    project.conversationThread,
    project.history
  );
  if (directThread.length > 0) return directThread;

  const recentThread = pickFirstArray(
    matchedRecent?.thread,
    matchedRecent?.messages,
    matchedRecent?.chat,
    matchedRecent?.conversation,
    matchedRecent?.conversationThread,
    matchedRecent?.history
  );
  if (recentThread.length > 0) return recentThread;

  return buildThreadFromSummary(project).length > 0
    ? buildThreadFromSummary(project)
    : buildThreadFromSummary(matchedRecent);
};

const getProjectFiles = (project, matchedRecent = null) =>
  pickFirstArray(
    project.files,
    project.sourceFiles,
    project.uploadedFiles,
    matchedRecent?.files,
    matchedRecent?.sourceFiles,
    matchedRecent?.uploadedFiles
  );

const normalizeProject = (project) => {
  const visuals = asArray(project.visuals).slice(0, MAX_VISUALS);
  const matchedRecent = findRecentConversationForProject(project);
  return {
    ...project,
    files: getProjectFiles(project, matchedRecent),
    thread: getProjectThread(project, matchedRecent),
    visuals,
    charts: visuals.length,
  };
};

const normalizeProjects = (projects) =>
  sanitizeProjects(projects)
    .slice(0, MAX_PROJECTS)
    .map(normalizeProject);

const mergeProjectLists = (primaryProjects, fallbackProjects) => {
  const merged = [];
  asArray([...asArray(primaryProjects), ...asArray(fallbackProjects)]).forEach((project) => {
    if (!project?.id && !project?.inviteCode) return;
    const existingIndex = merged.findIndex((item) => item.id === project.id || item.inviteCode === project.inviteCode);
    if (existingIndex < 0) {
      merged.push(project);
      return;
    }
    const existing = merged[existingIndex];
    merged[existingIndex] = {
      ...existing,
      ...project,
      files: getProjectFiles(existing).length ? getProjectFiles(existing) : getProjectFiles(project),
      thread: getProjectThread(existing).length ? getProjectThread(existing) : getProjectThread(project),
      visuals: asArray(existing.visuals).length ? existing.visuals : project.visuals,
    };
  });
  return normalizeProjects(merged);
};

const createInviteCode = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  return Array.from({ length: 7 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
};

const loadProjects = () => {
  try {
    const saved = localStorage.getItem(getProjectsKey());
    if (!saved) return defaultProjects;
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? normalizeProjects(parsed) : defaultProjects;
  } catch {
    return defaultProjects;
  }
};

const persistProjects = (projects) => {
  const nextProjects = normalizeProjects(projects);
  writeJson(getProjectsKey(), nextProjects);
  mergeProjectsIntoSharedIndex(nextProjects);
  return nextProjects;
};

const deleteProjectEverywhere = (projectId) => {
  const projectsKey = getProjectsKey();
  const recentConversationsKey = getRecentConversationsKey();
  const shareRoomKey = getShareRoomKey();
  const savedProjects = readJson(projectsKey, []);
  const deletedProject = Array.isArray(savedProjects) ? savedProjects.find((project) => project.id === projectId) : null;
  const deletedIds = [
    projectId,
    deletedProject?.id,
    deletedProject?.projectId,
    deletedProject?.conversationId,
    deletedProject?.inviteCode,
  ].filter(Boolean);

  if (Array.isArray(savedProjects)) {
    writeJson(projectsKey, savedProjects.filter((project) => project.id !== projectId));
  }

  const sharedProjects = readJson(SHARED_PROJECTS_KEY, []);
  if (Array.isArray(sharedProjects)) {
    writeJson(
      SHARED_PROJECTS_KEY,
      sharedProjects.filter((project) => !recordMatchesAnyId(project, deletedIds))
    );
  }

  const savedRecents = readJson(recentConversationsKey, []);
  if (Array.isArray(savedRecents)) {
    writeJson(
      recentConversationsKey,
      savedRecents.filter((item) => !recordMatchesAnyId(item, deletedIds))
    );
  }

  clearActiveAnalysisSessionIfMatched(deletedIds);

  const savedRoom = readJson(shareRoomKey, null);
  if (savedRoom) {
    writeJson(shareRoomKey, {
      ...savedRoom,
      loadedProjectIds: asArray(savedRoom.loadedProjectIds).filter((id) => id !== projectId),
      comments: savedRoom.comments || [],
      members: savedRoom.members || [],
    });
  }

  if (deletedProject?.inviteCode) {
    writeJson(getSharedRoomKey(deletedProject.inviteCode), {
      inviteCode: deletedProject.inviteCode,
      joinedCode: deletedProject.inviteCode,
      loadedProjectIds: [],
      comments: [],
      members: [],
    });
  }
};

const copyText = async (text) => {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  }
  window.alert(`초대코드가 복사되었습니다: ${text}`);
};

function Projects({ onProjectRestore, onShareProjectOpen }) {
  const [projects, setProjects] = useState(loadProjects);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [selectedVisual, setSelectedVisual] = useState(null);
  const [expandedVisual, setExpandedVisual] = useState(null);
  const [isViewAllOpen, setIsViewAllOpen] = useState(false);
  const [limitNotice, setLimitNotice] = useState('');
  const [syncNotice, setSyncNotice] = useState('');

  const visuals = useMemo(
    () =>
      asArray(projects).flatMap((project) =>
        asArray(project.visuals).map((visual) => ({
          ...visual,
          projectId: project.id,
          projectTitle: visual.projectTitle || project.title,
        }))
      ),
    [projects]
  );

  const visualLimitReached = visuals.length >= MAX_VISUALS;

  const commitProjects = (nextProjects) => {
    const normalizedProjects = persistProjects(nextProjects);
    setProjects(normalizedProjects);
    projectAPI.sync(normalizedProjects).catch((error) => {
      console.warn('MongoDB project sync skipped:', error);
      setSyncNotice('백엔드 동기화에 실패해 브라우저 저장소에 먼저 보관했습니다.');
    });
    return normalizedProjects;
  };

  useEffect(() => {
    let isMounted = true;

    projectAPI.list()
      .then((response) => {
        if (!isMounted) return;
        const serverProjects = response.data?.projects;
        if (!Array.isArray(serverProjects)) return;

        const mergedProjects = mergeProjectLists(serverProjects, loadProjects());
        persistProjects(mergedProjects);
        setProjects(mergedProjects);
        setSyncNotice('');
      })
      .catch((error) => {
        console.warn('MongoDB project load skipped:', error);
        if (isMounted) setSyncNotice('백엔드 프로젝트 목록을 불러오지 못해 브라우저 저장소 기준으로 표시합니다.');
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    writeJson(getProjectsKey(), normalizeProjects(projects));
    mergeProjectsIntoSharedIndex(projects);
  }, [projects]);

  useEffect(() => {
    const syncProjects = (event) => {
      if (event.detail?.key && event.detail.key !== getProjectsKey()) return;
      const nextProjects = loadProjects();
      setProjects((prev) => (
        JSON.stringify(normalizeProjects(prev)) === JSON.stringify(nextProjects) ? prev : nextProjects
      ));
    };

    window.addEventListener('storage', syncProjects);
    window.addEventListener('papermate-storage-updated', syncProjects);
    return () => {
      window.removeEventListener('storage', syncProjects);
      window.removeEventListener('papermate-storage-updated', syncProjects);
    };
  }, []);

  const handleAddProject = (event) => {
    event.preventDefault();
    const currentProjects = asArray(projects);
    if (currentProjects.length >= MAX_PROJECTS) {
      const message = '프로젝트는 최대 10개까지만 만들 수 있습니다. 새 프로젝트를 추가하려면 기존 프로젝트를 삭제해주세요.';
      setLimitNotice(message);
      window.alert(message);
      return;
    }

    const today = new Date().toLocaleDateString('ko-KR').replace(/. /g, '.').slice(0, -1);
    commitProjects([
      ...currentProjects,
      {
        id: `project-${Date.now()}`,
        type: 'New',
        title: `새 프로젝트 ${currentProjects.length + 1}`,
        updatedAt: today,
        date: today,
        charts: 0,
        isHwp: false,
        inviteCode: createInviteCode(),
        files: [],
        thread: [],
        visuals: [],
      },
    ]);
    setLimitNotice('');
  };

  const handleDeleteProject = (event, project) => {
    event.preventDefault();
    event.stopPropagation();
    if (!window.confirm(`"${project.title}" 프로젝트를 삭제하시겠습니까?`)) return;

    deleteProjectEverywhere(project.id);
    commitProjects(asArray(projects).filter((item) => item.id !== project.id));
    projectAPI.delete(project.id).catch((error) => {
      console.warn('MongoDB project delete skipped:', error);
      setSyncNotice('백엔드 삭제 반영에 실패해 브라우저 저장소에서 먼저 삭제했습니다.');
    });
    if (editingProjectId === project.id) setEditingProjectId(null);
    setLimitNotice('');
  };

  const handleEditClick = (event, project) => {
    event.preventDefault();
    event.stopPropagation();
    setEditingProjectId(project.id);
    setEditTitle(project.title);
  };

  const handleTitleSave = () => {
    if (!editTitle.trim()) return;
    const today = new Date().toLocaleDateString('ko-KR').replace(/. /g, '.').slice(0, -1);
    commitProjects(
      asArray(projects).map((project) =>
        project.id === editingProjectId ? { ...project, title: editTitle.trim(), updatedAt: today, date: today } : project
      )
    );
    setEditingProjectId(null);
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') handleTitleSave();
    else if (event.key === 'Escape') setEditingProjectId(null);
  };

  const handleProjectRestore = (project) => {
    if (project.source === 'shared-discussion') {
      onShareProjectOpen?.({
        projectId: project.id,
        projectTitle: project.title,
        inviteCode: project.inviteCode,
      });
      return;
    }

    if (!onProjectRestore) return;
    const matchedRecent = findRecentConversationForProject(project);
    const thread = getProjectThread(project, matchedRecent);
    const lastUserMessage = [...thread].reverse().find((item) => item.role === 'user');
    const lastAiMessage = [...thread].reverse().find((item) => item.role === 'ai' || item.role === 'asset');

    onProjectRestore({
      ...project,
      projectId: project.id,
      id: project.id,
      q: lastUserMessage?.text || project.title,
      a: lastAiMessage?.text || '저장된 프로젝트를 이어서 작업합니다.',
      projectTitle: project.title,
      inviteCode: project.inviteCode,
      files: getProjectFiles(project, matchedRecent),
      thread,
      visuals: asArray(project.visuals),
    });
  };

  const handleInviteCopy = (event, inviteCode) => {
    event.preventDefault();
    event.stopPropagation();
    if (!inviteCode) {
      window.alert('복사할 초대코드가 없습니다.');
      return;
    }
    copyText(inviteCode);
  };

  const handleDeleteVisual = (event, id) => {
    event.preventDefault();
    event.stopPropagation();
    if (!window.confirm('이 시각화 데이터를 삭제하시겠습니까?')) return;

    commitProjects(
      asArray(projects).map((project) => {
        const nextVisuals = asArray(project.visuals).filter((visual) => visual.id !== id);
        return { ...project, visuals: nextVisuals, charts: nextVisuals.length };
      })
    );
    if (selectedVisual && selectedVisual.id === id) setSelectedVisual(null);
    setLimitNotice('');
  };

  const renderVisualPreview = (visual, isDrawer = false) => {
    // 메인 그리드 카드의 넓은 가로 비율(약 4:1)에 맞추기 위해 렌더링 영역의 가로폭을 크게 설정합니다.
    const containerWidth = isDrawer ? 350 : 400;
    const containerHeight = isDrawer ? 180 : 80;

    const width = isDrawer ? 600 : 1000;
    const height = isDrawer ? 300 : 250;
    
    // 칸에 맞게 꽉 채우기 위한 스케일 계산
    const scale = Math.max(containerWidth / width, containerHeight / height);

    return (
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        width: `${width}px`,
        height: `${height}px`,
        transform: `translate(-50%, -50%) scale(${scale})`,
        pointerEvents: 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#ffffff',
        boxSizing: 'border-box',
        padding: '16px'
      }}>
        <VisualArtifact style={{ border: 'none', boxShadow: 'none', margin: 0, padding: 0, width: '100%', height: '100%' }}>
          <div className="artifact-body" style={{ padding: 0, height: '100%' }}>
            {renderDetailedVisualPreview(visual)}
          </div>
        </VisualArtifact>
      </div>
    );
  };

  return (
    <ProjectsContainer>
      <HeaderSection><h2>내 프로젝트</h2></HeaderSection>

      {limitNotice && (
        <div style={{ margin: '0 0 18px 0', color: '#dc2626', fontSize: '13px', fontWeight: 700 }}>
          {limitNotice}
        </div>
      )}
      {syncNotice && (
        <div style={{ margin: '0 0 18px 0', color: '#64748b', fontSize: '13px', fontWeight: 700 }}>
          {syncNotice}
        </div>
      )}

      <VisualSection>
        <SectionTitleRow>
          <h3>
            저장된 시각화 보관함
            <span style={{ fontSize: '14px', color: '#94a3b8', fontWeight: '600', marginLeft: '6px' }}>
              ({Math.min(visuals.length, MAX_VISUALS)}/{MAX_VISUALS})
            </span>
          </h3>
          <div className="btn-group">
            <button type="button" className="sub-btn" onClick={() => setIsViewAllOpen(true)}>전체 보기</button>
          </div>
        </SectionTitleRow>

        {visualLimitReached && (
          <div style={{ margin: '-8px 0 16px 0', color: '#64748b', fontSize: '12.5px', fontWeight: 700 }}>
            시각화 보관함은 최대 10개까지 저장됩니다. 새 시각화를 저장하려면 기존 항목을 삭제해주세요.
          </div>
        )}

        <VisualBoxContainer>
          {visuals.length === 0 ? (
            <EmptyCard as="div"><span>저장된 시각화가 없습니다.</span></EmptyCard>
          ) : visuals.slice(0, 3).map((visual) => (
            <VisualCard key={visual.id} onClick={() => setSelectedVisual(visual)}>
              <button className="delete-visual-btn" onClick={(event) => handleDeleteVisual(event, visual.id)} title="삭제">
                <i className="fa-solid fa-trash"></i>
              </button>
              <div className="mock-img">{renderVisualPreview(visual)}</div>
              <h4>{visual.title}</h4>
              <span>{visual.projectTitle} · {visual.date}</span>
            </VisualCard>
          ))}
        </VisualBoxContainer>
      </VisualSection>

      <SectionTitleRow>
        <h3>
          진행 중인 프로젝트
          <span style={{ fontSize: '14px', color: '#94a3b8', fontWeight: '600', marginLeft: '8px' }}>
            ({asArray(projects).length}/{MAX_PROJECTS})
          </span>
        </h3>
        <button type="button" className="primary-btn" onClick={handleAddProject}>+ 새 프로젝트...</button>
      </SectionTitleRow>

      <ProjectGrid>
        {asArray(projects).length === 0 ? (
          <EmptyCard onClick={handleAddProject}>
            <span className="plus-icon">+</span>
            <span>새 프로젝트 추가</span>
          </EmptyCard>
        ) : asArray(projects).map((project) => (
          <ProjectCard
            key={project.id}
            $shared={project.source === 'shared-discussion'}
            onClick={() => handleProjectRestore(project)}
          >
            <div className={`tag ${project.isHwp ? 'hwp' : ''} ${project.source === 'shared-discussion' ? 'shared' : ''}`}>
              {project.type || (project.source === 'shared-discussion' ? 'Shared' : 'New')}
            </div>
            {editingProjectId === project.id ? (
              <input
                type="text"
                className="title-input"
                value={editTitle}
                onChange={(event) => setEditTitle(event.target.value)}
                onBlur={handleTitleSave}
                onKeyDown={handleKeyDown}
                autoFocus
                onClick={(event) => event.stopPropagation()}
              />
            ) : (
              <h3>{project.title}</h3>
            )}
            <div className="date">최근 수정 {project.date || project.updatedAt}</div>
            <button
              type="button"
              className="invite-code"
              title="클릭하면 초대코드가 복사됩니다"
              onClick={(event) => handleInviteCopy(event, project.inviteCode)}
            >
              <span>초대코드</span>
              <strong>{project.inviteCode || '없음'}</strong>
            </button>
            <div className="profile-thumbnail"><i className="fa-regular fa-circle-user"></i></div>
            <div className="card-footer">
              <div className="meta-info">
                <span><i className="fa-solid fa-user"></i> {project.source === 'shared-discussion' ? '공유' : '개인'}</span>
                {(project.charts || 0) > 0 && (
                  <span><i className="fa-solid fa-box-archive"></i> 차트 {project.charts}개</span>
                )}
              </div>
              <div className="action-btns">
                <button type="button" className="edit-icon-btn" onClick={(event) => handleEditClick(event, project)} title="프로젝트명 수정">
                  <i className="fa-solid fa-pen"></i>
                </button>
                <button type="button" className="delete-icon-btn" onClick={(event) => handleDeleteProject(event, project)} title="프로젝트 삭제">
                  <i className="fa-solid fa-trash"></i>
                </button>
              </div>
            </div>
          </ProjectCard>
        ))}
        {asArray(projects).length > 0 && asArray(projects).length < MAX_PROJECTS && (
          <EmptyCard onClick={handleAddProject}>
            <span className="plus-icon">+</span>
            <span>새 프로젝트 추가</span>
          </EmptyCard>
        )}
      </ProjectGrid>

      {isViewAllOpen && (
        <ModalOverlay onClick={() => setIsViewAllOpen(false)}>
          <ModalContent onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3>모든 시각화 보관함 ({Math.min(visuals.length, MAX_VISUALS)}/{MAX_VISUALS})</h3>
              <button type="button" onClick={() => setIsViewAllOpen(false)}><i className="fa-solid fa-xmark"></i></button>
            </div>
            <div className="modal-body">
              {visuals.length === 0 ? (
                <EmptyCard as="div"><span>저장된 시각화가 없습니다.</span></EmptyCard>
              ) : visuals.map((visual) => (
                <VisualCard key={visual.id} onClick={() => setSelectedVisual(visual)}>
                  <button className="delete-visual-btn" onClick={(event) => handleDeleteVisual(event, visual.id)} title="삭제">
                    <i className="fa-solid fa-trash"></i>
                  </button>
                  <div className="mock-img">{renderVisualPreview(visual)}</div>
                  <h4>{visual.title}</h4>
                  <span>{visual.projectTitle} · {visual.date}</span>
                </VisualCard>
              ))}
            </div>
          </ModalContent>
        </ModalOverlay>
      )}

      <DrawerBackdrop $show={!!selectedVisual} onClick={() => setSelectedVisual(null)} />
      <DrawerContainer $show={!!selectedVisual}>
        {selectedVisual && (
          <>
            <div className="drawer-header">
              <div className="title-wrap">
                <h3>{selectedVisual.title}</h3>
                <span>{selectedVisual.projectTitle} · 저장 일자: {selectedVisual.date}</span>
              </div>
              <button type="button" className="close-btn" onClick={() => setSelectedVisual(null)}>
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>
            <div className="drawer-body">
              <div 
                className="visual-preview" 
                onClick={() => setExpandedVisual(selectedVisual)}
                style={{ cursor: 'pointer', position: 'relative' }}
                title="클릭하여 크게 보기"
              >
                {renderVisualPreview(selectedVisual, true)}
                <div style={{ position: 'absolute', right: '12px', bottom: '12px', background: 'rgba(255,255,255,0.8)', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                  <i className="fa-solid fa-expand" style={{ color: '#0ea5a4' }}></i>
                </div>
              </div>
              <div className="info-section"><h5>데이터 분석 요약</h5><p>{selectedVisual.desc || selectedVisual.text || '저장된 분석 요약이 없습니다.'}</p></div>
              <div className="info-section">
                <h5>세부 정보 필드</h5>
                <div className="details-list">
                  {asArray(selectedVisual.details).map((item, index) => (
                    <div className="detail-item" key={index}>
                      <span className="lbl">{item.lbl}</span>
                      <span className="val">{item.val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="drawer-footer">
              <button type="button" className="action-btn" onClick={() => downloadVisualReportData(selectedVisual)}>
                보고서 데이터 다운로드
              </button>
              <button type="button" className="action-btn" onClick={() => downloadVisualReportPng(selectedVisual)}>
                PNG로 다운로드
              </button>
            </div>
          </>
        )}
      </DrawerContainer>

      {expandedVisual && (
        <ModalOverlay onClick={() => setExpandedVisual(null)} style={{ zIndex: 1100 }}>
          <ModalContent onClick={(e) => e.stopPropagation()} style={{ maxWidth: '850px', width: '90%' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <h3 style={{ margin: 0, fontSize: '20px' }}>{expandedVisual.title}</h3>
              </div>
              <button type="button" onClick={() => setExpandedVisual(null)}><i className="fa-solid fa-xmark"></i></button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', padding: '0' }}>
              <div style={{ width: '100%', minHeight: '400px', background: '#f8fafc', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px', boxSizing: 'border-box' }}>
                <VisualArtifact style={{ width: '100%', border: 'none', boxShadow: 'none', margin: 0, padding: 0 }}>
                  <div className="artifact-body" style={{ padding: 0 }}>
                    {renderDetailedVisualPreview(expandedVisual)}
                  </div>
                </VisualArtifact>
              </div>
            </div>
          </ModalContent>
        </ModalOverlay>
      )}
    </ProjectsContainer>
  );
}

export default Projects;
