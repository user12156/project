// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 JS 로직은 유지하면서 함수 인자와 화면 props에 실제 타입을 붙여 TypeScript 검사를 통과하게 했습니다.
// 초보자 안내: 사용자가 실제로 보게 되는 한 화면 단위의 React 페이지 컴포넌트입니다.

import React, { useCallback, useEffect, useState } from 'react';
import { FiUser } from 'react-icons/fi';
import ProfileEditModal from '../components/ProfileEditModal';
import PasswordChangeModal from '../components/PasswordChangeModal';
import { useAuth } from '../context/AuthContext';
import {
  getProjectsKey,
  getRecentConversationsKey,
  getShareRoomKey,
  readJson,
  SHARED_PROJECTS_KEY,
  SHARED_ROOM_PREFIX,
} from '../utils/storageKeys';
import { MypageWrapper, ProfileCard } from './styles/Mypage.styles';

const asArray = (value) => (Array.isArray(value) ? value : []);

const mergeUniqueRecords = (...groups) => {
  const records = [];
  const seen = new Set();
  groups.flatMap(asArray).forEach((record) => {
    if (!record) return;
    const key = record.id || record.projectId || record.conversationId || record.inviteCode || record.title;
    if (key && seen.has(key)) return;
    if (key) seen.add(key);
    records.push(record);
  });
  return records;
};

const getRecordThread = (record) =>
  asArray(record?.thread).length
    ? asArray(record.thread)
    : asArray(record?.messages).length
      ? asArray(record.messages)
      : asArray(record?.conversation);

const countProjectResources = (project) => {
  const files = asArray(project?.files);
  const visuals = asArray(project?.visuals);
  const images = asArray(project?.discussionImages);
  const threadAssets = getRecordThread(project).filter(
    (item) => item?.role === 'asset' || Array.isArray(item?.rows)
  );

  return files.length + visuals.length + images.length + threadAssets.length;
};

const readSharedRooms = () => {
  const rooms = [];
  const keys = new Set([getShareRoomKey()]);

  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index);
    if (key?.startsWith(`${SHARED_ROOM_PREFIX}.`)) keys.add(key);
  }

  keys.forEach((key) => {
    const room = readJson(key, null);
    if (room && typeof room === 'object') rooms.push(room);
  });

  return rooms;
};

function Mypage({ onLogoutClick }) {
  const { user, updateProfile, changePassword, withdrawAccount, logout } = useAuth();
  const [activeModal, setActiveModal] = useState(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    projects: 0,
    analysisQuestions: 0,
    resources: 0,
    teams: 0,
  });

  const calculateStats = useCallback(() => {
    const projects = asArray(readJson(getProjectsKey(), []));
    const recents = asArray(readJson(getRecentConversationsKey(), []));
    const sharedProjects = asArray(readJson(SHARED_PROJECTS_KEY, []));
    const records = mergeUniqueRecords(projects, recents, sharedProjects);
    const username = user?.username;
    const teamCodes = new Set();

    readSharedRooms().forEach((room) => {
      const members = asArray(room.members);
      const isMember = username && members.some((member) => member?.name === username);
      const hasActivity = members.length > 0 || asArray(room.loadedProjectIds).length > 0;
      const code = room.inviteCode || room.joinedCode;
      if (code && hasActivity && (!username || isMember)) teamCodes.add(code);
    });

    setStats({
      projects: projects.length,
      analysisQuestions: records.reduce(
        (total, record) => total + getRecordThread(record).filter((item) => item?.role === 'user').length,
        0
      ),
      resources: records.reduce((total, record) => total + countProjectResources(record), 0),
      teams: teamCodes.size,
    });
  }, [user?.username]);

  useEffect(() => {
    calculateStats();

    const syncStats = () => calculateStats();
    window.addEventListener('storage', syncStats);
    window.addEventListener('papermate-storage-updated', syncStats);
    return () => {
      window.removeEventListener('storage', syncStats);
      window.removeEventListener('papermate-storage-updated', syncStats);
    };
  }, [calculateStats]);

  const closeModal = () => {
    setActiveModal(null);
    setError('');
  };

  const handleProfileSave = async (profileData) => {
    setSaving(true);
    setError('');
    setFeedback('');

    try {
      await updateProfile(profileData);
      setFeedback('프로필이 변경되었습니다.');
      closeModal();
    } catch (saveError) {
      setError(saveError.response?.data?.detail || saveError.message || '프로필 변경에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordSave = async (currentPassword, newPassword) => {
    setSaving(true);
    setError('');
    setFeedback('');

    try {
      await changePassword(currentPassword, newPassword);
      closeModal();
      window.alert('비밀번호가 변경되었습니다. 새 비밀번호로 다시 로그인해주세요.');
      logout();
    } catch (saveError) {
      setError(saveError.response?.data?.detail || saveError.message || '비밀번호 변경에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handleWithdraw = async () => {
    if (!window.confirm('정말로 탈퇴하시겠습니까?')) return;
    if (!window.confirm('계정과 서버에 저장된 프로젝트가 삭제됩니다. 그래도 탈퇴하시겠습니까?')) return;

    setSaving(true);
    setError('');
    setFeedback('');

    try {
      await withdrawAccount();
    } catch (withdrawError) {
      setError(withdrawError.response?.data?.detail || withdrawError.message || '회원 탈퇴에 실패했습니다.');
      setSaving(false);
    }
  };

  return (
    <MypageWrapper>
      <ProfileCard>
        <div className="avatar">
          {user?.profileImage ? <img src={user.profileImage} alt="프로필 사진" /> : <FiUser />}
        </div>
        <div className="username">{user?.username || 'Guest'}</div>

        {feedback && <div className="feedback success">{feedback}</div>}
        {error && <div className="feedback error">{error}</div>}

        <button className="btn-full" type="button" onClick={() => setActiveModal('profile')}>
          프로필 수정
        </button>
        <button className="btn-full" type="button" onClick={() => setActiveModal('password')}>
          비밀번호 변경
        </button>

        <div className="stats-grid">
          <div className="stat-item"><div className="val">{stats.projects}</div><div className="lbl">프로젝트</div></div>
          <div className="stat-item"><div className="val">{stats.analysisQuestions}</div><div className="lbl">분석 질문</div></div>
          <div className="stat-item"><div className="val">{stats.resources}</div><div className="lbl">자료</div></div>
          <div className="stat-item"><div className="val">{stats.teams}</div><div className="lbl">참여 팀</div></div>
        </div>

        <div className="bottom-btns">
          <button className="logout" type="button" onClick={onLogoutClick} disabled={saving}>로그아웃</button>
          <button className="withdraw" type="button" onClick={handleWithdraw} disabled={saving}>
            {saving ? '처리 중...' : '회원탈퇴'}
          </button>
        </div>
      </ProfileCard>

      {activeModal === 'profile' && (
        <ProfileEditModal
          currentUser={user}
          onClose={closeModal}
          onSave={handleProfileSave}
          saving={saving}
          error={error}
        />
      )}

      {activeModal === 'password' && (
        <PasswordChangeModal
          onClose={closeModal}
          onSave={handlePasswordSave}
          saving={saving}
          error={error}
        />
      )}
    </MypageWrapper>
  );
}

export default Mypage;
