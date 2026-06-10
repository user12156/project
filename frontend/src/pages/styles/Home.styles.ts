// 초보자 안내: styled-components로 화면의 색상, 간격, 배치 같은 스타일을 정의하는 파일입니다.

import styled from 'styled-components';
import { palette } from '../../shared/palette';

/* Home 페이지 전용 스타일 모음입니다.
   페이지 컴포넌트에는 화면 흐름과 이벤트 로직만 남기기 위해 styled-components를 이 파일로 분리했습니다. */
export const Container = styled.div`
  display: flex;
  width: 100%;
  min-height: 100dvh;
  overflow: hidden;
  box-sizing: border-box;
  background: #f9fbe7;

  @media (max-width: 900px) {
    min-height: 100dvh;
  }
`;

export const SidebarSlot = styled.div<{ $collapsed?: boolean }>`
  width: ${props => props.$collapsed ? '0px' : 'clamp(232px, 19vw, 280px)'};
  height: 100dvh;
  flex-shrink: 0;
  overflow: visible;
  transition: width 0.22s ease;

  @media (max-width: 900px) {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 50;
    width: ${props => props.$collapsed ? '0px' : 'min(300px, 86vw)'};
    pointer-events: ${props => props.$collapsed ? 'none' : 'auto'};
  }
`;

export const SidebarOpenButton = styled.button<{ $visible?: boolean; $isFullView?: boolean }>`
  position: fixed;
  top: ${props => props.$isFullView ? '50%' : '18px'};
  left: ${props => props.$isFullView ? '0' : '12px'};
  transform: ${props => props.$isFullView ? 'translateY(-50%)' : 'none'};
  z-index: 30;
  width: ${props => props.$isFullView ? '36px' : '28px'};
  height: ${props => props.$isFullView ? '48px' : '28px'};
  border: 1px solid ${props => props.$isFullView ? 'rgba(20, 125, 115, 0.18)' : '#cbd5e1'};
  border-left: ${props => props.$isFullView ? 'none' : '1px solid #cbd5e1'};
  border-radius: ${props => props.$isFullView ? '0 12px 12px 0' : '8px'};
  background: #ffffff;
  color: ${props => props.$isFullView ? '#126f67' : '#0f172a'};
  display: ${props => props.$visible ? 'inline-flex' : 'none'};
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.1);

  &:hover {
    color: #0ea5a4;
    border-color: #94a3b8;
    transform: ${props => props.$isFullView ? 'translateY(-50%) translateX(2px)' : 'none'};
  }

  svg {
    width: ${props => props.$isFullView ? '18px' : '16px'};
    height: ${props => props.$isFullView ? '18px' : '16px'};
  }
`;

export const MainContent = styled.main<{ $isFullView?: boolean; $sidebarCollapsed?: boolean }>`
  flex: 1; display: flex; flex-direction: column; 
  background: #f9fbe7;      /* 💡 기본 베이스 미색 */
  padding: ${props => props.$isFullView ? '0px' : '24px 40px'}; 
  padding-left: ${props => {
    if (!props.$sidebarCollapsed) return props.$isFullView ? '0px' : '40px';
    return props.$isFullView ? '0px' : '68px';
  }};
  min-width: 0;
  box-sizing: border-box; height: 100dvh; overflow: hidden; position: relative;
  transition: padding-left 0.22s ease;

  @media (max-width: 900px) {
    overflow-y: auto;
    height: auto;
    min-height: 100dvh;
    padding: ${props => props.$isFullView ? '0px' : '20px'};
    padding-left: ${props => props.$isFullView ? '0px' : '52px'};
  }

  @media (max-width: 560px) {
    padding: ${props => props.$isFullView ? '0px' : '16px'};
    padding-left: ${props => props.$isFullView ? '0px' : '48px'};
  }
`;

export const TopAuth = styled.div`
  display: flex; justify-content: flex-end; gap: 24px; 
  font-size: 13.5px; 
  font-weight: 700; 
  color: ${palette.slate[5]};           
  margin: 4px 32px 0 0; flex-shrink: 0;
  position: relative;
  z-index: 2;
  span { cursor: pointer; transition: color 0.15s; &:hover { color: ${palette.teal[5]}; } }

  @media (max-width: 560px) {
    margin-right: 0;
    justify-content: center;
  }
`;

export const MainDashboard = styled.div`
  flex: 1; 
  display: flex; 
  flex-direction: column; 
  justify-content: center; 
  align-items: center; 
  padding: clamp(24px, 4vw, 44px) clamp(18px, 4vw, 40px) clamp(32px, 5vw, 56px); 
  box-sizing: border-box; 
  position: relative;
  
  h2 { 
    font-size: clamp(24px, 3.4vw, 32px); font-weight: 800; color: #1e293b; text-align: center; margin-bottom: 12px; line-height: 1.35; 
    letter-spacing: 0; 
  }
  
  .sub { 
    max-width: 680px;
    font-size: 14px; color: #475569; text-align: center; margin-bottom: 36px; line-height: 1.6; 
    word-break: keep-all;
  }

  @media (max-width: 760px) {
    justify-content: flex-start;
    /* 💡 화면이 작아졌을 때 위쪽 여백(padding-top)을 넉넉하게 줘서 답답함을 없앱니다. */
    padding: 44px 0 28px 0; 

    h2 {
      line-height: 1.35;
    }

    .sub {
      font-size: 13px;
      margin-bottom: 24px;

      br {
        display: none;
      }
    }
  }
`;

export const DashboardBrand = styled.div`
  position: absolute;
  top: 0;
  left: 28px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;

  .logo-image {
    display: block;
    width: 210px;
    height: 84px;
    object-fit: contain;
  }

  @media (max-width: 760px) {
    position: relative; 
    top: 0;
    left: 0;
    margin-bottom: 20px; /* 로고와 밑에 있는 H2 제목 사이의 간격 */
    align-self: center;  /* 로고를 화면 중앙으로 예쁘게 정렬 */

    .logo-image {
      width: 150px;
      height: 60px;
    }
  }
`;

export const GridContainer = styled.div`
  display: grid; 
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px; 
  width: 100%; 
  max-width: 1040px;
  margin-bottom: 36px;

  @media (max-width: 980px) {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

  @media (max-width: 760px) {
    gap: 14px;
    margin-bottom: 24px;
  }
`;

// Home.styles.ts 내 FeatureCard 부분 수정

export const FeatureCard = styled.div<{ $bgGradient?: string }>`
  background: ${props => props.$bgGradient || 'white'}; 
  border: 1px solid rgba(255, 255, 255, 0.5); 
  border-radius: 20px; 
  padding: 24px; 
  display: flex; 
  flex-direction: column; 
  justify-content: flex-end; 
  position: relative; /* 💡 이모지를 고정하기 위해 필수 */
  overflow: hidden;   /* 💡 이모지가 카드 밖으로 튀어나가지 않게 필수 */
  cursor: pointer; 
  min-height: 240px;
  transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s;

  &:hover { 
    box-shadow: 0 15px 30px -5px rgba(0,0,0,0.08); 
    transform: translateY(-4px); 
    border-color: rgba(255, 255, 255, 0.78);
  }

  .content-wrapper {
    position: relative;
    z-index: 2; /* 글자가 이모지 위로 오도록 */
  }

  .icon-box { 
    width: 44px; height: 44px; border-radius: 12px; 
    background: rgba(255, 255, 255, 0.6); 
    color: #0d9488;            
    display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;
    margin-bottom: 16px; 
    backdrop-filter: blur(4px); 
  }
  
  /* 💡 글자가 아이콘 영역을 침범하지 않도록 너비 제한 추가 */
  /* 💡 텍스트가 차지하는 최대 너비를 더 줄여서 여백 확보 */
  .text-box { 
    width: min(100%, 210px);
    word-break: keep-all; 
    
    h4 { margin: 0 0 8px 0; font-size: 18px; font-weight: 800; color: #1e293b; } 
    p { margin: 0; font-size: 13px; color: #475569; line-height: 1.5; font-weight: 600; } 
  }

  /* 💡 이모지 크기를 살짝 줄이고, 오른쪽 아래로 더 밀어냄 */
  .floating-emoji {
    position: absolute;
    right: -15px;    /* -15px -> -25px (더 오른쪽으로) */
    bottom: 0px;   /* -30px -> -40px (더 아래로) */
    font-size: 120px; /* 130px -> 110px (크기 살짝 축소) */
    line-height: 1;
    z-index: 0;      
    opacity: 0.3;    /* 평소엔 조금 더 연하게 설정 */
    user-select: none; 
    text-shadow: 10px 20px 25px rgba(0, 0, 0, 0.15); 
    transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.4s;
  }

  /* 마우스를 올렸을 때 애니메이션 */
  &:hover .floating-emoji {
    transform: translateY(-15px) scale(1.05) rotate(-8deg);
    opacity: 0.8;
  }

  @media (max-width: 760px) {
    min-height: 124px;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 16px;
    padding: 18px;

    &:hover {
      transform: translateY(-2px);
    }
    
    .icon-box { margin-bottom: 0; }
    
    .floating-emoji {
      font-size: 80px;
      right: 0px;
      bottom: -15px;
      opacity: 0.3; 
    }

    .content-wrapper {
      display: flex;
      align-items: center;
      gap: 14px;
      min-width: 0;
    }

    .text-box {
      width: min(100%, 360px);

      h4 {
        font-size: 16px;
      }

      p {
        font-size: 12.5px;
      }
    }
  }

  @media (max-width: 420px) {
    min-height: 136px;
    padding: 16px;

    .floating-emoji {
      font-size: 68px;
      right: -10px;
    }
  }
`;
