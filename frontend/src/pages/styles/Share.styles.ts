// 초보자 안내: styled-components로 화면의 색상, 간격, 배치 같은 스타일을 정의하는 파일입니다.

import styled from 'styled-components';
import { palette } from '../../shared/palette';

/* Share 페이지 전용 스타일 모음입니다.
   페이지 컴포넌트에는 화면 흐름과 이벤트 로직만 남기기 위해 styled-components를 이 파일로 분리했습니다. */
export const Container = styled.div`
  display: flex;
  width: 100%;
  height: 100dvh;
  background: #ffffff;
  box-sizing: border-box;
  overflow: hidden;

  /* Header area styles */
  .header-area {
    position: sticky;
    top: 0;
    z-index: 8;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
    padding: 0 0 6px 0;
    background: linear-gradient(180deg, #ffffff 0%, rgba(255, 255, 255, 0.94) 100%);
    border-bottom: 1px solid #eef2f7;
    width: 100%;
  }

  .menu-toggle {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #e0f2fe;
    color: #0369a1;
    font-size: 14px;
  }

  h2 {
    font-size: 19px;
    font-weight: 800;
    color: #1e293b;
    margin: 0;
  }

  /* Share project card styles */
  .share-project-card {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    padding: 18px;
    margin-bottom: 24px;
    width: 100%;
    box-sizing: border-box;
  }

  .share-project-card .tag-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .share-project-card .tag,
  .share-project-card .invite {
    display: inline-flex;
    align-items: center;
    min-height: 26px;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 11.5px;
    font-weight: 850;
  }

  .share-project-card .tag {
    background: #e6f4f4;
    color: #0ea5a4;
  }

  .share-project-card .invite {
    background: #f1f5f9;
    color: #475569;
    font-family: monospace;
  }

  .share-project-card h3 {
    margin: 0 0 12px 0;
    color: #0f172a;
    font-size: 18px;
    font-weight: 850;
  }

  .share-project-card .project-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 14px;
  }

  .share-project-card .project-meta span {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 9px;
    color: #64748b;
    font-size: 12px;
    font-weight: 750;
  }

  .share-project-card .project-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .share-project-card button {
    border: none;
    border-radius: 6px;
    background: #0ea5a4;
    color: #ffffff;
    padding: 9px 14px;
    font-size: 12.5px;
    font-weight: 850;
    cursor: pointer;
  }

  .share-project-card .save-shared-card {
    background: #475569;
  }

  /* Cooperation Settings styles */
  .load-btn {
    background: #0ea5a4;
    color: white;
    border: none;
    margin: 0 22px 18px 22px;
    padding: 13px;
    border-radius: 8px;
    font-weight: 800;
    font-size: 14px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .invite-help {
    width: calc(100% - 64px);
    margin: 22px auto 8px auto;
    color: #92400e;
    font-size: 11.5px;
    font-weight: 800;
    line-height: 1.35;
    box-sizing: border-box;
  }

  .code-row {
    width: calc(100% - 64px);
    max-width: 276px;
    margin: 0 auto 16px auto;
    display: flex;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #facc15;
    background: #ffffff;
    box-shadow: 0 8px 18px rgba(180, 83, 9, 0.08);
    box-sizing: border-box;
  }

  .top-code {
    margin-top: 0;
  }

  .code-label {
    background: #f59e0b;
    color: #ffffff;
    padding: 8px 10px;
    font-weight: 800;
    font-size: 12px;
  }

  .code-input {
    min-width: 0;
    flex: 1;
    border: none;
    padding: 0 8px;
    color: #92400e;
    font-family: monospace;
    font-size: 13px;
    font-weight: 800;
    outline: none;
    text-align: center;
    background: #fffbeb;
  }

  .join-action {
    background: #ffffff;
    color: #b45309;
    border: none;
    border-left: 1px solid #fde68a;
    padding: 0 10px;
    font-weight: 800;
    font-size: 12px;
    cursor: pointer;
  }

  .join-action:hover {
    background: #fef3c7;
  }

  .notice {
    margin: -8px 22px 14px 22px;
    color: #64748b;
    font-size: 11.5px;
    font-weight: 700;
    min-height: 16px;
  }

  .notice.error {
    color: #dc2626;
  }

  @media (max-width: 1000px) {
    flex-direction: column;
    height: auto;
    min-height: 100dvh;
    overflow-y: auto;
    padding: 16px;
    gap: 16px;

    .header-area {
      margin-bottom: 0;
    }

    .share-project-card {
      margin-bottom: 0;
    }

    .load-btn {
      margin: 0;
      width: 100%;
    }

    .invite-help {
      margin: 0;
      width: 100%;
    }

    .code-row {
      margin: 0;
      width: 100%;
      max-width: none;
    }

    .notice {
      margin: 0;
      width: 100%;
    }

    /* Responsive overrides for inner share card */
    .share-project-card .tag-row {
      align-items: flex-start;
      flex-direction: column;
    }

    .share-project-card button {
      width: 100%;
    }

    .share-project-card .project-actions {
      flex-direction: column;
    }
  }

  @media (max-width: 760px) {
    padding: 12px;
    gap: 12px;

    .header-area {
      align-items: flex-start;
      gap: 10px;
    }

    h2 {
      font-size: 19px;
      line-height: 1.35;
    }
  }

  @media (max-width: 520px) {
    padding: 8px;
    gap: 10px;

    .code-row {
      flex-wrap: wrap;
    }

    .code-label,
    .join-action {
      min-height: 38px;
    }
  }
`;

export const MainTimelineContent = styled.div`
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 10px 40px 28px 40px;
  box-sizing: border-box;
  overflow-y: auto;
  order: 1;

  @media (max-width: 1000px) {
    order: 2;
    overflow-y: visible;
  }

  @media (max-width: 760px) {
    padding: 8px 18px 24px 18px;
  }

  @media (max-width: 520px) {
    padding: 8px 14px 22px 14px;
  }
`;

export const CoopPanelToggle = styled.button<{ $collapsed?: boolean }>`
  position: fixed;
  top: 50%;
  right: ${(props) => (props.$collapsed ? '0' : '340px')};
  z-index: 35;
  transform: translateY(-50%);
  width: 34px;
  min-height: 94px;
  border: 1px solid #cbd5e1;
  border-right: none;
  border-radius: 10px 0 0 10px;
  background: #ffffff;
  color: #334155;
  writing-mode: vertical-rl;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);

  &:hover {
    color: #0f766e;
    border-color: #0ea5a4;
    background: #f0fdfa;
  }

  @media (max-width: 1000px) {
    display: none;
  }
`;

export const TimelineInner = styled.div`
  width: 100%;
  max-width: 980px;
`;


export const ProjectLoadBar = styled.div`
  position: sticky;
  top: 35px;
  z-index: 7;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 7px 10px;
  margin-bottom: 14px;
  width: 100%;
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.07);

  input[type='file'] {
    display: none;
  }

  select {
    min-width: 240px;
    height: 36px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 0 10px;
    color: #1e293b;
    font-size: 13px;
    font-weight: 700;
    outline: none;
    background: #ffffff;
  }

  button {
    height: 32px;
    border: none;
    border-radius: 6px;
    padding: 0 12px;
    background: #0ea5a4;
    color: #ffffff;
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    white-space: nowrap;
  }

  .image-load-btn {
    min-width: 122px;
    background: #0f766e;
  }

  .image-load-btn:hover {
    background: #115e59;
  }

  .support-load-btn {
    min-width: 152px;
    background: #4f46e5;
  }

  .support-load-btn:hover {
    background: #4338ca;
  }

  .support-code-box {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 0 0 auto;
    min-width: 0;
    margin-left: auto;
  }

  .support-code-input {
    height: 32px;
    flex: 0 0 190px;
    width: 190px;
    min-width: 190px;
    max-width: 190px;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 0 12px;
    color: #1e293b;
    font-family: monospace;
    font-size: 13px;
    font-weight: 800;
    outline: none;
    background: #f8fbff;
    box-sizing: border-box;
  }

  .support-code-input:focus {
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
    background: #ffffff;
  }

  .support-code-input::placeholder {
    color: #94a3b8;
    font-family: inherit;
  }

  .hint {
    max-width: 180px;
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    line-height: 1.35;
  }

  @media (max-width: 760px) {
    align-items: stretch;
    flex-direction: column;
    top: 0;

    select,
    button,
    .support-code-box {
      width: 100%;
    }

    .support-code-box {
      flex-direction: row;
      align-items: center;
      margin-left: 0;
      min-width: 0;
    }

    .support-code-input {
      flex: 0 0 168px;
      width: 168px;
      min-width: 168px;
      max-width: 168px;
      height: 34px;
    }

    .support-load-btn {
      flex: 1;
      min-width: 0;
    }

    .hint {
      margin-left: 0;
      line-height: 1.45;
    }
  }

  @media (max-width: 420px) {
    .support-code-box {
      flex-direction: column;
      align-items: center;
    }

    .support-code-input {
      flex: 0 0 34px;
      width: 210px;
      min-width: 210px;
      max-width: 210px;
    }
  }
`;

export const SectionTitle = styled.div`
  font-size: 14px;
  font-weight: 800;
  color: #64748b;
  margin-bottom: 20px;
  scroll-margin-top: 92px;
`;

export const TimelineWrapper = styled.div`
  position: relative;
  margin-left: 10px;
  padding-left: 30px;

  &::before {
    content: '';
    position: absolute;
    left: 6px;
    top: 12px;
    bottom: 12px;
    width: 2px;
    background: #e2e8f0;
  }

  .empty-state {
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
    background: #ffffff;
    padding: 28px 20px;
    color: #94a3b8;
    font-size: 13px;
    font-weight: 750;
    text-align: center;
  }

  @media (max-width: 520px) {
    margin-left: 0;
    padding-left: 22px;

    &::before {
      left: 4px;
    }
  }
`;

export const TimelineNode = styled.article<{ $active?: boolean }>`
  position: relative;
  margin-bottom: 20px;

  .dot {
    position: absolute;
    left: -30px;
    top: 8px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: ${(props) => (props.$active ? '#0ea5a4' : '#cbd5e1')};
    border: 2px solid white;
    box-shadow: ${(props) => (props.$active ? '0 0 0 4px rgba(14, 165, 164, 0.14)' : 'none')};
    box-sizing: border-box;
  }

  .card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px 18px;
  }

  .project-label {
    color: #0ea5a4;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 8px;
  }

  .project-label.support {
    color: #64748b;
  }

  h4 {
    margin: 0 0 6px 0;
    color: #0f172a;
    font-size: 15px;
    font-weight: 800;
  }

  .meta {
    color: #94a3b8;
    font-size: 11.5px;
    font-weight: 700;
    margin-bottom: 10px;
  }

  .body {
    color: #334155;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.6;
    white-space: pre-wrap;
  }

  .question-card {
    display: inline-flex;
    max-width: 100%;
    margin: 8px 0 12px 0;
    padding: 11px 15px;
    border-radius: 10px;
    background: #0ea5a4;
    color: #ffffff;
    font-size: 14px;
    font-weight: 850;
    line-height: 1.45;
    white-space: pre-wrap;
    box-shadow: 0 8px 18px rgba(14, 165, 164, 0.18);
  }

  .answer-fold {
    margin: 8px 0 12px 0;
    border: 1px solid #dbe7f0;
    border-radius: 8px;
    background: #f8fafc;
    overflow: hidden;
  }

  .answer-fold summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 11px 13px;
    cursor: pointer;
    list-style: none;
    color: #334155;
    font-size: 13px;
    font-weight: 750;
  }

  .answer-fold summary::-webkit-details-marker {
    display: none;
  }

  .answer-fold summary span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .answer-fold summary b {
    flex: 0 0 auto;
    color: #0ea5a4;
    font-size: 12px;
    font-weight: 850;
  }

  .answer-fold[open] summary {
    border-bottom: 1px solid #e2e8f0;
  }

  .answer-fold .body {
    padding: 13px;
    background: #ffffff;
  }

  .answer-evidence-panel {
    display: grid;
    gap: 8px;
    padding: 0 13px 13px 13px;
    background: #ffffff;
  }

  .answer-evidence-section {
    border: 1px solid #8deee1;
    border-radius: 8px;
    background: #d7fbf5;
    overflow: hidden;
  }

  .answer-evidence-section summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 9px 12px;
    list-style: none;
    cursor: pointer;
    color: #00746f;
    font-size: 13.5px;
    font-weight: 850;
  }

  .answer-evidence-section summary::-webkit-details-marker {
    display: none;
  }

  .answer-evidence-section summary b {
    flex: 0 0 auto;
    padding: 5px 10px;
    border: 1px solid #55ddcf;
    border-radius: 999px;
    background: #ffffff;
    color: #00746f;
    font-size: 11.5px;
    font-weight: 850;
  }

  .answer-evidence-content {
    border-top: 1px solid #8deee1;
    background: #ffffff;
    padding: 11px 12px;
    color: #334155;
    font-size: 12.5px;
    font-weight: 650;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .discussion-image {
    width: 100%;
    max-height: 360px;
    object-fit: contain;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #f8fafc;
    margin: 8px 0 12px 0;
  }

  .visual-preview {
    min-height: 220px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #f8fafc;
    margin: 8px 0 12px 0;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    width: 100%;
  }

  .visual-preview-button {
    padding: 0;
    cursor: zoom-in;
    text-align: left;
  }

  .visual-preview .dynamic-visualizer {
    min-height: 220px !important;
    padding: 8px 10px 14px 10px !important;
  }

  .mini-visual {
    width: min(360px, 78%);
    height: 110px;
    color: #0ea5a4;
  }

  .mini-visual.chart {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    gap: 16px;
  }

  .mini-visual.chart span {
    width: 18%;
    border-radius: 10px 10px 2px 2px;
    background: #0ea5a4;
  }

  .mini-visual.table {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .mini-visual.table span {
    border-radius: 5px;
    background: #d9eeee;
  }

  .mini-visual.table span:nth-child(-n + 3) {
    background: #0ea5a4;
  }

  .mini-visual.graph {
    position: relative;
  }

  .mini-visual.graph::before {
    content: '';
    position: absolute;
    left: 8%;
    right: 8%;
    top: 48%;
    height: 4px;
    border-radius: 999px;
    background: linear-gradient(135deg, transparent 0 18%, #0ea5a4 18% 28%, transparent 28% 42%, #0ea5a4 42% 55%, transparent 55% 68%, #0ea5a4 68% 100%);
    transform: rotate(-10deg);
  }

  .mini-visual.graph i {
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #0ea5a4;
  }

  .mini-visual.graph i:nth-child(1) { left: 9%; bottom: 20%; }
  .mini-visual.graph i:nth-child(2) { left: 34%; top: 18%; }
  .mini-visual.graph i:nth-child(3) { left: 58%; bottom: 30%; }
  .mini-visual.graph i:nth-child(4) { right: 10%; top: 12%; }

  .detail-list {
    margin-top: 12px;
    display: grid;
    gap: 8px;
  }

  .detail-item {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background: #f8fafc;
    padding: 8px 10px;
    color: #64748b;
    font-size: 12px;
    font-weight: 750;
  }

  .detail-item strong {
    color: #0f172a;
    text-align: right;
  }

  .actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }

  .restore-btn {
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #475569;
    font-weight: 800;
    font-size: 12px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 6px 12px;
    border-radius: 6px;
  }

  .restore-btn:hover {
    background: #e6f4f4;
    color: #0ea5a4;
    border-color: #bce3e3;
  }

  @media (max-width: 520px) {
    .dot {
      left: -24px;
    }

    .card {
      padding: 14px;
    }

    h4 {
      font-size: 14px;
      line-height: 1.4;
    }

    .restore-btn {
      width: 100%;
      justify-content: center;
    }
  }
`;

export const ShareProjectCard = styled.div``;

export const ResultTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
  font-size: 12px;

  th,
  td {
    border: 1px solid #e2e8f0;
    padding: 8px 10px;
    text-align: left;
  }

  th {
    background: #f8fafc;
    color: #475569;
    font-weight: 800;
  }

  td {
    color: #334155;
    font-weight: 650;
  }

  @media (max-width: 560px) {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
`;

export const VisualModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  background: rgba(15, 23, 42, 0.48);
`;

export const VisualModalPanel = styled.div`
  width: min(980px, 100%);
  max-height: min(760px, calc(100vh - 56px));
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 28px 90px rgba(15, 23, 42, 0.28);
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding: 18px 22px;
    border-bottom: 1px solid #e2e8f0;
  }

  .modal-header span {
    color: #0ea5a4;
    font-size: 12px;
    font-weight: 850;
  }

  .modal-header h3 {
    margin: 3px 0 0 0;
    color: #0f172a;
    font-size: 19px;
    font-weight: 900;
  }

  .modal-header button {
    width: 36px;
    height: 36px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #ffffff;
    color: #475569;
    font-size: 22px;
    font-weight: 800;
    cursor: pointer;
  }

  .modal-body {
    padding: 16px 22px 22px 22px;
    overflow-y: auto;
  }

  .modal-body .dynamic-visualizer {
    min-height: 460px !important;
  }

  @media (max-width: 640px) {
    max-height: calc(100vh - 24px);

    .modal-header {
      padding: 16px;
    }

    .modal-body {
      padding: 12px 14px 18px 14px;
    }
  }
`;

export const RightCoopPanel = styled.aside<{ $collapsed?: boolean }>`
  width: 340px;
  background: #f8fafc;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  flex: 0 0 340px;
  min-height: 0;
  order: 2;
  transform: ${(props) => (props.$collapsed ? 'translateX(100%)' : 'translateX(0)')};
  margin-right: ${(props) => (props.$collapsed ? '-340px' : '0')};
  transition: transform 0.22s ease, margin-right 0.22s ease;

  @media (max-width: 1000px) {
    order: 1;
    width: 100%;
    flex: none;
    min-height: auto;
    max-height: none;
    border-left: none;
    border-bottom: 1px solid #e2e8f0;
    margin-right: 0;
    transform: none;
    overflow: visible;
  }
`;

export const MembersBox = styled.div`
  padding: 0 22px 18px 22px;
  border-bottom: 1px solid #e2e8f0;

  h5 {
    margin: 0 0 12px 0;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
  }

  .m-item,
  .empty {
    display: grid;
    grid-template-columns: 20px minmax(0, 1fr);
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    color: #334155;
    font-size: 13px;
    font-weight: 750;
  }

  .m-item.owner {
    margin: 0 0 12px 0;
    padding: 9px 10px;
    border: 1px solid #fde68a;
    border-radius: 8px;
    background: #fffbeb;
    color: #92400e;
  }

  .m-item.owner i {
    color: #f59e0b;
  }

  .m-item i,
  .empty i {
    width: 20px;
    text-align: center;
  }

  .m-item span {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty {
    color: #94a3b8;
  }

  i {
    color: ${palette.slate[4]};
  }

  @media (max-width: 1000px) {
    padding: 0 16px 16px 16px;
  }
`;

export const ChatTimelineFeed = styled.div`
  flex: 1;
  padding: 16px 18px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #ffffff;

  .chat-empty {
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
    padding: 18px 14px;
    color: #94a3b8;
    font-size: 12.5px;
    font-weight: 750;
    text-align: center;
  }

  @media (max-width: 1000px) {
    flex: none;
    min-height: 160px;
    max-height: 280px;
  }
`;

export const TalkBubble = styled.div<{ $isMe?: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: ${(props) => (props.$isMe ? 'flex-end' : 'flex-start')};
  align-self: ${(props) => (props.$isMe ? 'flex-end' : 'flex-start')};
  max-width: 88%;

  .user-id {
    display: flex;
    align-items: center;
    gap: 5px;
    color: #64748b;
    font-size: 11.5px;
    font-weight: 800;
    margin-bottom: 6px;
  }

  .msg-row {
    display: flex;
    align-items: flex-end;
    gap: 6px;
    flex-direction: ${(props) => (props.$isMe ? 'row-reverse' : 'row')};
  }

  .message-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-direction: ${(props) => (props.$isMe ? 'row-reverse' : 'row')};
  }

  .bubble {
    background: ${(props) => (props.$isMe ? '#0ea5a4' : '#f1f5f9')};
    color: ${(props) => (props.$isMe ? 'white' : '#1e293b')};
    padding: 10px 14px;
    border-radius: ${(props) => (props.$isMe ? '12px 2px 12px 12px' : '2px 12px 12px 12px')};
    font-size: 13px;
    font-weight: 700;
    line-height: 1.45;
    white-space: pre-wrap;
  }

  .timestamp {
    min-width: 48px;
    color: #94a3b8;
    font-size: 10px;
    font-weight: 700;
    text-align: ${(props) => (props.$isMe ? 'right' : 'left')};
  }

  .delete-btn {
    width: 22px;
    height: 22px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background: #ffffff;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 900;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    opacity: 0;
    transition: all 0.12s ease;
  }

  &:hover .delete-btn {
    opacity: 1;
  }

  .delete-btn:hover {
    color: #dc2626;
    border-color: #fecaca;
    background: #fef2f2;
  }

  @media (max-width: 520px) {
    max-width: 96%;

    .msg-row {
      align-items: flex-start;
      flex-direction: column;
    }

    .message-actions {
      align-items: flex-start;
    }

    .bubble {
      font-size: 12.5px;
    }

    .timestamp {
      min-width: 0;
    }

    .delete-btn {
      opacity: 1;
    }
  }
`;

export const FooterInputBox = styled.div`
  display: flex;
  gap: 8px;
  padding: 16px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;

  input {
    flex: 1;
    min-width: 0;
    padding: 10px 14px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    color: #1e293b;
    font-size: 13px;
    font-weight: 700;
    outline: none;
  }

  input::placeholder {
    color: #94a3b8;
  }

  button {
    background: #0ea5a4;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0 14px;
    font-weight: 800;
    font-size: 13px;
    cursor: pointer;
  }

  @media (max-width: 520px) {
    padding: 12px;

    button {
      padding: 0 12px;
    }
  }
`;

export const ProjectPickerOverlay = styled.div`
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.28);
  padding: 32px;

  @media (max-width: 560px) {
    padding: 14px;
  }
`;

export const ProjectPickerPanel = styled.div`
  width: min(860px, 100%);
  max-height: min(680px, calc(100vh - 64px));
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.18);

  .picker-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 20px 24px;
    border-bottom: 1px solid #e2e8f0;
  }

  .picker-title {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  h3 {
    margin: 0;
    color: #0f172a;
    font-size: 18px;
    font-weight: 850;
  }

  .picker-desc {
    color: #64748b;
    font-size: 12.5px;
    font-weight: 700;
  }

  .close-btn {
    width: 34px;
    height: 34px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #ffffff;
    color: #475569;
    font-size: 18px;
    font-weight: 800;
    cursor: pointer;
  }

  .close-btn:hover {
    background: #f8fafc;
    color: #0f172a;
  }

  @media (max-width: 560px) {
    max-height: calc(100vh - 28px);
    border-radius: 8px;

    .picker-header {
      align-items: flex-start;
      padding: 18px;
    }

    h3 {
      font-size: 16px;
    }
  }
`;

export const ProjectPickerGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 16px;
  padding: 24px;
  overflow-y: auto;

  .empty-state {
    grid-column: 1 / -1;
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
    padding: 28px 20px;
    color: #94a3b8;
    font-size: 13px;
    font-weight: 750;
    text-align: center;
  }

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
    padding: 18px;
  }
`;

export const ProjectPickerCard = styled.button<{ $loaded?: boolean }>`
  min-height: 154px;
  border: 1px solid ${(props) => (props.$loaded ? '#bce3e3' : '#e2e8f0')};
  border-radius: 8px;
  background: ${(props) => (props.$loaded ? '#f0fdfa' : '#ffffff')};
  padding: 18px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.15s ease;

  &:hover {
    transform: translateY(-2px);
    border-color: #0ea5a4;
    box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
  }

  .tag-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    min-height: 24px;
    padding: 3px 10px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #475569;
    font-size: 11px;
    font-weight: 850;
  }

  .loaded-label {
    color: #0ea5a4;
    font-size: 11px;
    font-weight: 850;
  }

  .project-name {
    color: #0f172a;
    font-size: 15px;
    font-weight: 850;
    line-height: 1.35;
  }

  .updated {
    color: #94a3b8;
    font-size: 11.5px;
    font-weight: 750;
  }

  .meta {
    margin-top: auto;
    padding-top: 12px;
    border-top: 1px solid #e2e8f0;
    color: #64748b;
    font-size: 12px;
    font-weight: 750;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
`;