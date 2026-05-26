import styled from 'styled-components';
import { palette } from '../../shared/palette';

/* Share 페이지 전용 스타일 모음입니다.
   페이지 컴포넌트에는 화면 흐름과 이벤트 로직만 남기기 위해 styled-components를 이 파일로 분리했습니다. */
export const Container = styled.div`
  display: flex;
  width: 100%;
  height: 100vh;
  background: #ffffff;
  box-sizing: border-box;

  @media (max-width: 1000px) {
    flex-direction: column;
    height: auto;
    min-height: 100vh;
  }
`;

export const MainTimelineContent = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 10px 40px 28px 40px;
  box-sizing: border-box;
  overflow-y: auto;

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

  @media (max-width: 760px) {
    padding: 8px 18px 24px 18px;

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
    padding: 8px 14px 22px 14px;
  }
`;

export const TimelineInner = styled.div`
  width: 100%;
  max-width: 980px;

  .share-project-card {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    padding: 18px;
    margin-bottom: 24px;
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

  @media (max-width: 560px) {
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

  .storage-load-btn {
    min-width: 126px;
    background: #2563eb;
  }

  .storage-load-btn:hover {
    background: #1d4ed8;
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
    flex: 1;
    min-width: 360px;
  }

  .support-code-input {
    height: 32px;
    flex: 1;
    min-width: 160px;
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

    select,
    button,
    .support-code-box,
    .support-code-input {
      width: 100%;
    }

    .support-code-box {
      flex-direction: column;
      align-items: stretch;
      min-width: 0;
    }

    .hint {
      margin-left: 0;
      line-height: 1.45;
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

export const TimelineNode = styled.article`
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
    height: 160px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #f8fafc;
    margin: 8px 0 12px 0;
    display: flex;
    align-items: center;
    justify-content: center;
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

  .mini-visual.mindmap {
    width: min(420px, 86%);
    height: auto;
    min-height: 116px;
    display: grid;
    grid-template-columns: minmax(86px, 0.8fr) 1.2fr;
    gap: 8px;
    align-items: center;
  }

  .mini-visual.mindmap strong {
    min-height: 74px;
    border-radius: 999px;
    background: #0ea5a4;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px;
    text-align: center;
    font-size: 12px;
    line-height: 1.35;
  }

  .mini-visual.mindmap span {
    display: block;
    margin-bottom: 6px;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #2563eb;
    border-radius: 7px;
    background: #ffffff;
    color: #334155;
    padding: 7px 9px;
    font-size: 11.5px;
    font-weight: 800;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mini-visual.image-card {
    width: min(420px, 86%);
    height: auto;
    min-height: 116px;
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 14px;
    background:
      radial-gradient(circle at 16% 18%, rgba(14, 165, 164, 0.18), transparent 28%),
      linear-gradient(135deg, #eff6ff 0%, #ffffff 54%, #f0fdfa 100%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 12px;
  }

  .mini-visual.image-card strong {
    color: #0f172a;
    font-size: 14px;
    font-weight: 900;
    line-height: 1.4;
  }

  .mini-visual.image-card div {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .mini-visual.image-card span,
  .keyword-row span {
    display: inline-flex;
    align-items: center;
    min-height: 24px;
    border-radius: 999px;
    border: 1px solid #bae6fd;
    background: #f0f9ff;
    color: #0369a1;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 850;
  }

  .summary-box {
    margin-top: 12px;
    border: 1px solid #dbeafe;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
    background: #eff6ff;
    color: #1e3a8a;
    padding: 10px 12px;
    font-size: 12.5px;
    font-weight: 750;
    line-height: 1.55;
  }

  .keyword-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
  }

  .branch-list {
    display: grid;
    gap: 7px;
    margin-top: 12px;
  }

  .branch-list div {
    border: 1px solid #e2e8f0;
    border-left: 4px solid #0ea5a4;
    border-radius: 7px;
    background: #f8fafc;
    color: #334155;
    padding: 8px 10px;
    font-size: 12.5px;
    font-weight: 750;
    line-height: 1.45;
  }

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

export const RightCoopPanel = styled.aside`
  width: 340px;
  background: #f8fafc;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;

  .load-btn {
    background: #0ea5a4;
    color: white;
    border: none;
    margin: 24px 22px 18px 22px;
    padding: 13px;
    border-radius: 8px;
    font-weight: 800;
    font-size: 14px;
    cursor: pointer;
  }

  .invite-help {
    width: calc(100% - 64px);
    margin: 18px auto 8px auto;
    color: #92400e;
    font-size: 11.5px;
    font-weight: 800;
    line-height: 1.35;
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
    margin: -10px 22px 16px 22px;
    color: ${(props) => (props.$error ? '#dc2626' : '#64748b')};
    font-size: 11.5px;
    font-weight: 700;
    min-height: 16px;
  }

  @media (max-width: 1000px) {
    width: 100%;
    min-height: 420px;
    border-left: none;
    border-top: 1px solid #e2e8f0;
  }

  @media (max-width: 520px) {
    .code-row {
      flex-wrap: wrap;
    }

    .code-label,
    .join-action {
      min-height: 38px;
    }
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
`;

export const TalkBubble = styled.div`
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

export const ProjectPickerCard = styled.button`
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

export const VisualPickerOverlay = styled.div`
  position: fixed;
  inset: 0;
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.34);
  padding: 24px;

  @media (max-width: 560px) {
    padding: 12px;
  }
`;

export const VisualPickerPanel = styled.div`
  width: min(980px, 100%);
  max-height: min(760px, calc(100vh - 48px));
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.22);

  .picker-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 20px 24px;
    border-bottom: 1px solid #e2e8f0;
    background: #f8fafc;
  }

  h3 {
    margin: 0 0 5px 0;
    color: #0f172a;
    font-size: 19px;
    font-weight: 900;
  }

  p {
    margin: 0;
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
    font-size: 20px;
    font-weight: 850;
    cursor: pointer;
  }

  .picker-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    padding: 16px 24px;
    border-top: 1px solid #e2e8f0;
    background: #ffffff;
  }

  .picker-footer span {
    margin-right: auto;
    color: #64748b;
    font-size: 12.5px;
    font-weight: 800;
  }

  .picker-footer button {
    min-height: 38px;
    border-radius: 8px;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #475569;
    padding: 0 15px;
    font-size: 13px;
    font-weight: 850;
    cursor: pointer;
  }

  .picker-footer .primary {
    border-color: #0ea5a4;
    background: #0ea5a4;
    color: #ffffff;
  }

  @media (max-width: 560px) {
    max-height: calc(100vh - 24px);

    .picker-header,
    .picker-footer {
      padding: 16px;
    }

    .picker-footer {
      flex-wrap: wrap;
    }

    .picker-footer span {
      flex-basis: 100%;
    }
  }
`;

export const VisualPickerGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  padding: 20px 24px;
  overflow-y: auto;
  background: #ffffff;

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
    padding: 16px;
  }
`;

export const VisualPickerCard = styled.button`
  position: relative;
  border: 1px solid ${(props) => (props.$selected ? '#0ea5a4' : '#e2e8f0')};
  border-left: 5px solid ${(props) => (props.$selected ? '#0ea5a4' : '#cbd5e1')};
  border-radius: 10px;
  background: ${(props) => (props.$selected ? '#f0fdfa' : '#ffffff')};
  padding: 14px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.14s ease;

  &:hover {
    transform: translateY(-2px);
    border-color: #0ea5a4;
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  }

  .select-mark {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 24px;
    height: 24px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: ${(props) => (props.$selected ? '#0ea5a4' : '#f1f5f9')};
    color: ${(props) => (props.$selected ? '#ffffff' : '#64748b')};
    font-size: 13px;
    font-weight: 900;
  }

  .project-name {
    max-width: calc(100% - 34px);
    color: #0ea5a4;
    font-size: 11.5px;
    font-weight: 850;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  h4 {
    margin: 0;
    color: #0f172a;
    font-size: 14px;
    font-weight: 900;
    line-height: 1.35;
  }

  .kind {
    color: #94a3b8;
    font-size: 11.5px;
    font-weight: 800;
  }

  .preview {
    min-height: 130px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .preview .mini-visual {
    transform: scale(0.86);
    transform-origin: center;
  }
`;
