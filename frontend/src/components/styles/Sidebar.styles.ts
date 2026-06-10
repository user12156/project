// 초보자 안내: styled-components로 화면의 색상, 간격, 배치 같은 스타일을 정의하는 파일입니다.

import styled from 'styled-components';

export const SidebarContainer = styled.aside<{ $collapsed?: boolean }>`
  width: clamp(232px, 19vw, 280px);
  height: 100dvh;
  background: linear-gradient(180deg, #d8f0d9 0%, #c8e6c9 52%, #bfe0c0 100%);
  border-right: 1px solid rgba(46, 125, 50, 0.14);
  display: flex;
  flex-direction: column;
  padding: 24px 14px 16px;
  box-sizing: border-box;
  justify-content: space-between;
  flex-shrink: 0;
  transform: ${(props) => (props.$collapsed ? 'translateX(-100%)' : 'translateX(0)')};
  transition: transform 0.22s ease;
  box-shadow: 10px 0 28px rgba(15, 23, 42, 0.04);

  @media (min-width: 1440px) {
    padding: 28px 16px 18px;
  }

  @media (max-width: 900px) {
    width: min(300px, 86vw);
    box-shadow: 18px 0 44px rgba(15, 23, 42, 0.18);
  }
`;

export const TopBrandSection = styled.div`
  display: flex;
  align-items: center;
  min-width: 0;
  cursor: pointer;
  transition: opacity 0.15s;

  &:hover {
    opacity: 0.9;
  }

  .logo {
    width: 166px;
    height: 64px;
    display: block;
    object-fit: contain;
  }

  @media (min-width: 1440px) {
    .logo {
      width: 178px;
      height: 68px;
    }
  }
`;

export const SidebarMain = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  flex: 1;
  min-height: 0;
`;

export const BrandRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 22px;
`;

export const CollapseButton = styled.button`
  width: 30px;
  height: 30px;
  border: 1px solid rgba(33, 113, 102, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.62);
  color: #2f6f68;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;

  &:hover {
    background: #ffffff;
    color: #147d73;
    border-color: rgba(20, 125, 115, 0.2);
  }

  svg {
    width: 17px;
    height: 17px;
  }
`;

export const NavList = styled.nav`
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 3px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(71, 85, 105, 0.22);
    border-radius: 999px;
  }

  .section-lbl {
    font-size: 11px;
    font-weight: 800;
    color: rgba(47, 111, 104, 0.74);
    margin: 18px 0 7px 12px;
    letter-spacing: 0.5px;
  }
`;

export const SidebarFooter = styled.div`
  width: 100%;
  flex-shrink: 0;
`;

export const BottomMenuGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 12px;
  border-top: 1px solid rgba(47, 111, 104, 0.14);
`;

export const NavIcon = styled.span<{ $active?: boolean }>`
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: ${(props) => (props.$active ? '#147d73' : '#4f746f')};
  transition: color 0.15s;

  svg {
    width: 18px;
    height: 18px;
    stroke-width: 2.2;
  }
`;

export const MenuBtn = styled.div<{ $active?: boolean }>`
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 10px 13px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  box-sizing: border-box;
  color: ${(props) => (props.$active ? '#126f67' : '#335f5a')};
  background: ${(props) => (props.$active ? 'rgba(255, 255, 255, 0.78)' : 'transparent')};
  border: 1px solid ${(props) => (props.$active ? 'rgba(20, 125, 115, 0.14)' : 'transparent')};
  box-shadow: ${(props) => (props.$active ? '0 8px 18px rgba(33, 113, 102, 0.08)' : 'none')};
  cursor: pointer;
  transition: all 0.15s ease-in-out;

  &:hover {
    background: rgba(255, 255, 255, 0.7);
    color: #126f67;

    ${NavIcon} {
      color: #147d73;
    }
  }

  .menu-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

export const RecentDeleteButton = styled.button`
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(51, 95, 90, 0.58);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s ease;

  svg {
    width: 15px;
    height: 15px;
    stroke-width: 2.2;
  }

  ${MenuBtn}:hover &,
  &:focus-visible {
    opacity: 1;
  }

  &:hover {
    background: rgba(220, 38, 38, 0.1);
    color: #dc2626;
  }
`;

export const BottomUserCard = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 9px 9px 9px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
  margin-top: 10px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(20, 125, 115, 0.12);
  box-shadow: 0 10px 22px rgba(33, 113, 102, 0.09);
  box-sizing: border-box;

  &:hover {
    background: rgba(255, 255, 255, 0.88);
    transform: translateY(-1px);
  }

  .profile-circle {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    flex-shrink: 0;
    background: #ffffff;
    border: 1px solid rgba(20, 125, 115, 0.18);
    box-shadow: inset 0 0 0 2px rgba(216, 240, 217, 0.58);
  }

  .account-icon {
    width: 23px;
    height: 23px;
    color: #147d73;
    stroke-width: 1.9;
  }

  img {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
  }

  .name {
    font-size: 13.5px;
    font-weight: 700;
    color: #24423f;
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .gear-icon {
    color: #126f67;
    width: 21px;
    height: 21px;
    flex-shrink: 0;
    padding: 7px;
    border-radius: 8px;
    background: rgba(20, 125, 115, 0.12);
    box-sizing: content-box;

    &:hover {
      background: rgba(20, 125, 115, 0.18);
    }
  }

  @media (min-width: 1440px) {
    min-height: 62px;

    .profile-circle {
      width: 40px;
      height: 40px;
    }
  }
`;
