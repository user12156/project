// 초보자 안내: styled-components로 화면의 색상, 간격, 배치 같은 스타일을 정의하는 파일입니다.

import styled from 'styled-components';

export const MainLayout = styled.div`
  display: flex;
  flex: 1;
  overflow: hidden;
  height: 100%;
  min-width: 0;

  @media (max-width: 900px) {
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
  }
`;

export const VisualPanel = styled.div<{ $libraryCollapsed?: boolean }>`
  flex: 0 0 60%;
  min-width: 0;
  border-right: 1px solid #e2e8f0;
  padding: 12px;
  overflow: hidden;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 0;

  > .title,
  > .hint,
  > .asset-list {
    display: none;
  }

  .compare-shell {
    display: grid;
    grid-template-columns: ${(props) =>
      props.$libraryCollapsed
        ? 'minmax(0, 1fr)'
        : 'minmax(360px, var(--source-pane-width, 72%)) 10px minmax(220px, 1fr)'};
    gap: 8px;
    min-height: 0;
    height: 100%;
  }

  .compare-shell.is-resizing {
    cursor: col-resize;
  }

  .source-pane,
  .visual-library {
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    overflow: hidden;
  }

  .panel-head {
    min-height: 48px;
    padding: 8px 10px 8px 12px;
    border-bottom: 1px solid #e2e8f0;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .title {
    font-size: 14px;
    font-weight: 850;
    color: #0f172a;
  }

  .hint {
    margin: 2px 0 0 0;
    color: #64748b;
    font-size: 11px;
    font-weight: 650;
    line-height: 1.35;
  }

  .library-toggle {
    min-width: 78px;
    height: 32px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #ffffff;
    color: #334155;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    font-size: 12px;
    font-weight: 850;
    cursor: pointer;
    flex: 0 0 auto;
  }

  .library-toggle:hover {
    border-color: #0ea5a4;
    color: #0f766e;
    background: #f0fdfa;
  }

  .library-toggle svg {
    width: 15px;
    height: 15px;
  }

  .pane-resizer {
    position: relative;
    min-width: 10px;
    cursor: col-resize;
    border-radius: 8px;
    background: transparent;
    touch-action: none;
    z-index: 2;
  }

  .library-collapsed .pane-resizer,
  .library-collapsed .visual-library {
    display: none;
  }

  .pane-resizer::before {
    content: "";
    position: absolute;
    top: 12px;
    bottom: 12px;
    left: 50%;
    width: 2px;
    transform: translateX(-50%);
    border-radius: 999px;
    background: #cbd5e1;
    transition: width 0.15s ease, background 0.15s ease;
  }

  .pane-resizer:hover::before,
  .compare-shell.is-resizing .pane-resizer::before {
    width: 4px;
    background: #0ea5a4;
  }

  .resize-shield {
    position: fixed;
    inset: 0;
    z-index: 70;
    cursor: col-resize;
    background: transparent;
    touch-action: none;
  }

  .source-file-list {
    display: flex;
    flex-wrap: nowrap;
    gap: 6px;
    padding: 8px 10px 10px;
    border-bottom: 1px solid #e2e8f0;
    flex: 0 0 auto;
    overflow-x: auto;
    overflow-y: hidden;
    background: #f8fafc;
    scroll-snap-type: x proximity;
    scrollbar-gutter: stable;
    scrollbar-width: thin;
  }

  .source-file-item {
    flex: 0 0 calc((100% - 12px) / 3);
    min-width: 92px;
    max-width: calc((100% - 12px) / 3);
    min-height: 36px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    background: #ffffff;
    color: #475569;
    padding: 0 7px;
    font-size: 11px;
    font-weight: 800;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 5px;
    text-align: left;
    scroll-snap-align: start;
    transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
  }

  .source-file-item:hover,
  .source-file-item.active {
    border-color: #0ea5a4;
    background: #f0fdfa;
    color: #0f766e;
  }

  .source-file-item > svg {
    width: 13px;
    height: 13px;
    color: #0ea5a4;
    flex: 0 0 auto;
  }

  .source-file-item > span:not(.source-file-remove) {
    min-width: 0;
    flex: 1;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    line-height: 1.25;
    white-space: normal;
    word-break: break-all;
  }

  .source-preview {
    flex: 1;
    min-height: 0;
    background: #f8fafc;
    overflow: auto;
  }

  .source-frame {
    width: 100%;
    height: 100%;
    min-height: 620px;
    border: 0;
    background: #ffffff;
  }

  .source-image {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 0 auto;
  }

  .source-text {
    margin: 0;
    min-height: 100%;
    padding: 14px;
    color: #334155;
    background: #ffffff;
    font-family: Consolas, Monaco, monospace;
    font-size: 12px;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .source-empty {
    min-height: 360px;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 24px;
    text-align: center;
    color: #64748b;
  }

  .source-empty strong {
    color: #0f172a;
    font-size: 13px;
    font-weight: 850;
  }

  .source-empty span {
    max-width: 320px;
    color: #64748b;
    font-size: 12px;
    font-weight: 650;
    line-height: 1.55;
  }

  .asset-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px;
  }

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    width: 100%;
    min-height: 38px;
    padding: 9px 10px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 850;
    color: #334155;
    transition: all 0.15s ease;

    &:hover {
      border-color: #0ea5a4;
      color: #0f766e;
      background: #f0fdfa;
    }
  }

  .visual-actions {
    border-top: 1px solid #e2e8f0;
    padding-top: 12px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .asset-item {
    font-size: 12px;
    padding: 10px 11px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    color: #475569;
    font-weight: 750;
    line-height: 1.45;

    &.expanded {
      background: #f8fafc;
    }

    .asset-title-button {
      width: 100%;
      min-width: 0;
      border: 0;
      background: transparent;
      color: inherit;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      text-align: left;
      cursor: pointer;
    }

    strong {
      display: block;
      color: #0f172a;
      font-size: 12.5px;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    > span {
      display: block;
      margin-top: 4px;
      color: #94a3b8;
      font-size: 11px;
    }

    .toggle-indicator {
      flex: 0 0 auto;
      color: #0ea5a4;
      font-size: 11px;
      font-weight: 850;
    }

    .artifact-head {
      padding: 12px 14px;
    }

    .artifact-body {
      padding: 12px;
    }
  }

  @media (max-width: 900px) {
    flex: none;
    width: 100%;
    max-width: none;
    min-width: 0;
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
    max-height: none;
    min-height: 68vh;
    overflow: visible;

    .compare-shell {
      grid-template-columns: 1fr;
      grid-auto-rows: auto;
      height: auto;
      min-height: 68vh;
    }

    .pane-resizer {
      display: none;
    }

    .source-pane {
      min-height: 68vh;
    }

    .source-frame {
      min-height: 58vh;
    }

    .source-empty {
      min-height: 48vh;
    }

    .visual-library {
      max-height: 42vh;
    }
  }
`;

export const VisualArtifact = styled.div`
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);

  &.is-clickable .artifact-body {
    cursor: zoom-in;
  }

  &.is-clickable .artifact-body:focus {
    outline: 3px solid rgba(14, 165, 164, 0.22);
    outline-offset: -3px;
  }

  .artifact-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;

    h4 {
      margin: 0;
      color: #0f172a;
      font-size: 15px;
      font-weight: 850;
    }

    .artifact-meta {
      flex: 0 0 auto;
      display: grid;
      justify-items: end;
      gap: 3px;
      min-width: fit-content;
    }

    span {
      color: #0ea5a4;
      font-size: 11px;
      font-weight: 850;
    }

    time {
      color: #64748b;
      font-size: 10.5px;
      font-weight: 800;
      white-space: nowrap;
    }
  }

  .artifact-body {
    padding: 16px;
  }

  .artifact-desc {
    margin: 0 0 12px 0;
    color: #475569;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.55;
  }

  .save-container {
    width: 100%;
  }

  .save-visual {
    width: 100%;
    min-height: 38px;
    border: none;
    border-top: 1px solid #e2e8f0;
    background: #0ea5a4;
    color: #ffffff;
    font-size: 13px;
    font-weight: 850;
    cursor: pointer;
    
    &:disabled {
      background: #94a3b8;
      cursor: not-allowed;
    }
  }

  &.is-modal {
    height: 100%;
    display: flex;
    flex-direction: column;

    .artifact-body {
      flex: 1;
      min-height: 0;
      overflow: auto;
    }

    .dynamic-visualizer {
      min-height: 420px !important;
    }

    .recharts-responsive-container {
      height: 420px !important;
    }

    .save-container {
      display: flex;
      justify-content: flex-end;
      padding: 12px 24px;
      border-top: 1px solid #e2e8f0;
      background: #f8fafc;
    }

    .save-visual {
      width: auto;
      min-height: 34px;
      border: 1px solid #0ea5a4;
      border-radius: 6px;
      background: #0ea5a4;
      color: #ffffff;
      padding: 0 16px;
      font-size: 12px;
      font-weight: 800;
      border-top: none;

      &:hover {
        background: #0d9488;
        border-color: #0d9488;
      }

      &:disabled {
        background: #f1f5f9;
        border-color: #cbd5e1;
        color: #94a3b8;
        cursor: not-allowed;
      }
    }
  }

  .mini-table {
    display: grid;
    gap: 1px;
    background: #e2e8f0; /* 얇은 회색 테두리 효과 */
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);

    div {
      background: #ffffff;
      padding: 12px 16px;
      color: #334155;
      font-size: 13px;
      font-weight: 500;
      min-height: 44px;
      line-height: 1.5;
      display: flex;
      align-items: center;
      justify-content: flex-start;
      word-break: keep-all;
      transition: background-color 0.2s ease;
    }

    div:hover {
      background: #f8fafc; /* 살짝 호버 효과 */
    }

    .th {
      background: #f1f5f9; /* 헤더를 깔끔한 연한 회색으로 변경 */
      color: #0f172a;
      font-weight: 800;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 2px solid #cbd5e1;
    }
  }

  .mini-graph {
    position: relative;
    height: 220px;
    display: flex;
    align-items: flex-end;
    gap: 14px;
    padding: 32px 22px 34px 42px;
    border: 2px solid #cbd5e1;
    border-radius: 10px;
    background:
      linear-gradient(#e2e8f0 1px, transparent 1px) 0 0 / 100% 25%,
      linear-gradient(90deg, #e2e8f0 1px, transparent 1px) 0 0 / 20% 100%,
      linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);

    &::before {
      content: '';
      position: absolute;
      left: 34px;
      top: 18px;
      bottom: 30px;
      width: 2px;
      background: #334155;
      border-radius: 999px;
    }

    &::after {
      content: '';
      position: absolute;
      left: 34px;
      right: 16px;
      bottom: 30px;
      height: 2px;
      background: #334155;
      border-radius: 999px;
    }

    .axis {
      position: absolute;
      color: #64748b;
      font-size: 10px;
      font-weight: 900;
    }

    .y-axis {
      top: 10px;
      left: 10px;
    }

    .x-axis {
      right: 14px;
      bottom: 8px;
    }

    .graph-line {
      display: none; /* 기존의 못생긴 붉은 꺾은선 그래프는 제거하고 깔끔한 막대 그래프로 통일합니다. */
    }

    .bar-wrap {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      min-width: 0;
      height: 100%;
      position: relative;
      z-index: 1;
      cursor: pointer;
    }

    .bar {
      width: 100%;
      max-width: 42px;
      border-radius: 6px 6px 0 0;
      background: linear-gradient(180deg, rgba(14, 165, 164, 0.85) 0%, rgba(14, 165, 164, 0.15) 100%);
      border: 1px solid rgba(14, 165, 164, 0.4);
      border-bottom: none;
      box-shadow: 0 -4px 16px rgba(14, 165, 164, 0.15);
      transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
    }

    .bar-wrap:hover .bar {
      background: linear-gradient(180deg, rgba(14, 165, 164, 1) 0%, rgba(14, 165, 164, 0.3) 100%);
      transform: translateY(-4px);
      box-shadow: 0 -6px 20px rgba(14, 165, 164, 0.3);
    }

    strong {
      color: #0f172a;
      font-size: 11px;
      font-weight: 900;
      font-variant-numeric: tabular-nums;
    }

    span {
      max-width: 70px;
      color: #64748b;
      font-size: 11px;
      font-weight: 750;
      text-align: center;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mini-image {
    min-height: 180px;
    border: 1px solid #dbeafe;
    border-radius: 12px;
    background:
      radial-gradient(circle at 20% 18%, rgba(20, 184, 166, 0.18), transparent 28%),
      linear-gradient(135deg, #eff6ff 0%, #ffffff 52%, #f0fdfa 100%);
    padding: 18px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 16px;

    .image-title {
      color: #0f172a;
      font-size: 18px;
      font-weight: 900;
      line-height: 1.35;
    }

    &::before {
      content: '';
      width: 100%;
      height: 54px;
      border-radius: 10px;
      background:
        linear-gradient(135deg, rgba(14, 165, 164, 0.2), rgba(37, 99, 235, 0.12)),
        repeating-linear-gradient(135deg, transparent 0 8px, rgba(14, 165, 164, 0.08) 8px 12px);
      border: 1px solid #bfdbfe;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .chips span {
      padding: 6px 9px;
      border-radius: 999px;
      background: #ffffff;
      border: 1px solid #bae6fd;
      color: #0369a1;
      font-size: 11px;
      font-weight: 850;
    }
  }

`;

export const InviteCodePill = styled.button`
  min-height: 36px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  display: inline-flex;
  align-items: center;
  overflow: hidden;
  padding: 0;
  cursor: copy;

  span {
    align-self: stretch;
    display: inline-flex;
    align-items: center;
    padding: 0 10px;
    background: #64748b;
    color: #ffffff;
    font-size: 12px;
    font-weight: 850;
  }

  strong {
    min-width: 86px;
    padding: 0 12px;
    font-family: monospace;
    font-size: 13px;
    color: #0f172a;
  }

  &:hover {
    border-color: #0ea5a4;
  }

  @media (max-width: 680px) {
    width: 100%;
    flex: 1 1 100%;

    span {
      white-space: nowrap;
    }

    strong {
      flex: 1;
      min-width: 0;
      text-align: center;
    }
  }
`;

export const SaveInlinePanel = styled.div`
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 32px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;

  input {
    flex: 1;
    min-width: 0;
    height: 38px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 0 12px;
    outline: none;
    color: #0f172a;
    font-size: 13px;
    font-weight: 750;

    &:focus {
      border-color: #0ea5a4;
      box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.12);
    }
  }

  button {
    min-height: 38px;
    border-radius: 8px;
    padding: 0 14px;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #334155;
    font-size: 13px;
    font-weight: 850;
    cursor: pointer;
  }

  .primary {
    border-color: #0ea5a4;
    background: #0ea5a4;
    color: #ffffff;
  }

  @media (max-width: 680px) {
    padding: 10px 16px;
    flex-wrap: wrap;

    input {
      flex-basis: 100%;
    }
  }
`;

export const PreviewModalContainer = styled.div`
  width: 90%;
  max-width: 1120px;
  height: min(760px, calc(100vh - 48px));
  max-height: calc(100vh - 48px);
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.2);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  
  /* 뷰어 내부 스타일 조정 (기존 VisualArtifact 디자인을 상속하되 더 넓게) */
  .artifact-head {
    padding: 20px 24px;
    h4 {
      font-size: 18px;
    }
  }

  .artifact-body {
    padding: 24px 28px;
  }

  .artifact-desc {
    font-size: 15px;
    margin-bottom: 18px;
  }
`;

