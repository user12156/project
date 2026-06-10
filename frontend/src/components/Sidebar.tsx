// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 JS 로직은 유지하면서 함수 인자와 화면 props에 실제 타입을 붙여 TypeScript 검사를 통과하게 했습니다.
// 초보자 안내: 화면에서 재사용되는 UI 조각을 정의한 React 컴포넌트 파일입니다.

import React from 'react';
import {
  FiChevronLeft,
  FiFolder,
  FiMessageSquare,
  FiPieChart,
  FiSettings,
  FiShare2,
  FiTrash2,
  FiUser,
} from 'react-icons/fi';
import { TbMessagePlus } from 'react-icons/tb';
import papermateLogo from '../assets/papermate-logo-sidebar.png';
import {
  BottomMenuGroup,
  BottomUserCard,
  BrandRow,
  CollapseButton,
  MenuBtn,
  NavIcon,
  NavList,
  RecentDeleteButton,
  SidebarContainer,
  SidebarFooter,
  SidebarMain,
  TopBrandSection,
} from './styles/Sidebar.styles';

interface SidebarIconProps {
  active?: boolean;
  children: React.ReactNode;
}

function SidebarIcon({ active = false, children }: SidebarIconProps) {
  return <NavIcon $active={active}>{children}</NavIcon>;
}

function Sidebar({
  viewMode,
  onMenuClick,
  onLogoClick,
  isLoggedIn,
  username,
  userProfileImage,
  onProfileClick,
  collapsed,
  onCollapse,
  recentConversations = [],
  onRecentConversationClick,
  onDeleteRecent,
  activeConversationId,
}) {
  return (
    <SidebarContainer $collapsed={collapsed}>
      <SidebarMain>
        <BrandRow>
          <TopBrandSection onClick={onLogoClick}>
            <img className="logo" src={papermateLogo} alt="PaperMate" />
          </TopBrandSection>
          <CollapseButton type="button" onClick={onCollapse} aria-label="사이드바 접기">
            <FiChevronLeft />
          </CollapseButton>
        </BrandRow>

        <NavList>
          <MenuBtn $active={viewMode === 'main'} onClick={() => onMenuClick('새 채팅')}>
            <SidebarIcon active={viewMode === 'main'}><TbMessagePlus /></SidebarIcon>
            <span className="menu-text">새 채팅</span>
          </MenuBtn>

          {isLoggedIn && (
            <>
              <div className="section-lbl">최근 대화</div>
              {recentConversations.length === 0 && (
                <MenuBtn $active={false}>
                  <SidebarIcon><FiMessageSquare /></SidebarIcon>
                  <span className="menu-text">최근 대화 없음</span>
                </MenuBtn>
              )}

              {recentConversations.map((conversation) => {
                const conversationId = conversation.conversationId || conversation.projectId || conversation.id;
                return (
                  <MenuBtn
                    key={conversation.id}
                    $active={activeConversationId === conversationId}
                    onClick={() => onRecentConversationClick?.(conversation)}
                  >
                    <SidebarIcon active={activeConversationId === conversationId}><FiMessageSquare /></SidebarIcon>
                    <span className="menu-text">{conversation.title}</span>
                    <RecentDeleteButton
                      type="button"
                      aria-label={`${conversation.title} 삭제`}
                      title="최근 대화 삭제"
                      onClick={(event) => onDeleteRecent?.(conversation.id, event)}
                    >
                      <FiTrash2 />
                    </RecentDeleteButton>
                  </MenuBtn>
                );
              })}
            </>
          )}
        </NavList>
      </SidebarMain>

      <SidebarFooter>
        <BottomMenuGroup>
          <MenuBtn $active={viewMode === '분석 비교'} onClick={() => onMenuClick('분석 비교')}>
            <SidebarIcon active={viewMode === '분석 비교'}><FiPieChart /></SidebarIcon>
            <span className="menu-text">분석 · 요약</span>
          </MenuBtn>
          <MenuBtn $active={viewMode === '내 프로젝트'} onClick={() => onMenuClick('내 프로젝트')}>
            <SidebarIcon active={viewMode === '내 프로젝트'}><FiFolder /></SidebarIcon>
            <span className="menu-text">프로젝트</span>
          </MenuBtn>
          <MenuBtn $active={viewMode === '공유'} onClick={() => onMenuClick('공유')}>
            <SidebarIcon active={viewMode === '공유'}><FiShare2 /></SidebarIcon>
            <span className="menu-text">작업공간</span>
          </MenuBtn>
        </BottomMenuGroup>

        {isLoggedIn && (
          <BottomUserCard onClick={onProfileClick}>
            <div className="profile-circle">
              {userProfileImage ? (
                <img src={userProfileImage} alt={`${username} 프로필`} />
              ) : (
                <FiUser className="account-icon" />
              )}
            </div>
            <div className="name">{username}</div>
            <FiSettings className="gear-icon" />
          </BottomUserCard>
        )}
      </SidebarFooter>
    </SidebarContainer>
  );
}

export default Sidebar;
