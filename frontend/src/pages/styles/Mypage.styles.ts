// 초보자 안내: styled-components로 화면의 색상, 간격, 배치 같은 스타일을 정의하는 파일입니다.

import styled from 'styled-components';

export const MypageWrapper = styled.div`
  display: flex; 
  width: 100%; 
  min-height: 100dvh; 
  background: #f8fafc;
  justify-content: center; 
  align-items: center; 
  box-sizing: border-box;
  padding: 24px;
`;

export const ProfileCard = styled.div`
  width: min(320px, 100%);
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05);

  .avatar {
    width: 80px; height: 80px; border-radius: 50%;
    background: #e2e8f0; margin-bottom: 15px;
    display: flex; align-items: center; justify-content: center;
    font-size: 40px; color: #94a3b8;
    overflow: hidden;
  }

  .avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar svg {
    width: 40px;
    height: 40px;
  }

  .username { font-size: 20px; font-weight: 800; margin-bottom: 20px; }

  .feedback {
    width: 100%;
    padding: 10px 12px;
    border-radius: 8px;
    margin-bottom: 12px;
    font-size: 12.5px;
    font-weight: 700;
    box-sizing: border-box;
    text-align: center;
  }

  .feedback.success {
    background: #ecfdf5;
    color: #047857;
    border: 1px solid #a7f3d0;
  }

  .feedback.error {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
  }

  .btn-full {
    width: 100%; padding: 12px; margin-bottom: 8px;
    border: 1px solid #e2e8f0; border-radius: 8px;
    background: white; font-weight: 700; cursor: pointer;
    &:hover { background: #f8fafc; }
  }

  .stats-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
    width: 100%; margin: 20px 0;
  }

  .stat-item {
    border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px; text-align: center;
    .val { color: #0ea5a4; font-weight: 800; font-size: 16px; }
    .lbl { font-size: 11px; color: #64748b; margin-top: 2px; }
  }

  .bottom-btns {
    width: 100%; display: flex; gap: 10px; margin-top: 10px;
    button { flex: 1; padding: 10px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; }
    button:disabled { opacity: 0.65; cursor: not-allowed; }
    .logout { background: #f1f5f9; }
    .withdraw { background: #fee2e2; color: #ef4444; }
  }
`;
