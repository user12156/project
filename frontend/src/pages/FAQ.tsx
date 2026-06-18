import React, { useState } from "react";
import { FiGrid, FiImage, FiPaperclip } from "react-icons/fi";
import styled from "styled-components";
import papermateLogo from "../assets/papermate-logo.png";

const FAQContainer = styled.div`
  height: 100%;
  width: 100%;
  overflow-y: auto;
  padding: 40px 32px 40px 72px;
  color: #1f2937;
  position: relative;
  box-sizing: border-box;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.32) transparent;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.32);
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: content-box;
  }

  &::-webkit-scrollbar-thumb:hover {
    background-color: rgba(100, 116, 139, 0.42);
  }

  .popup-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 80;
    padding: 18px;
  }

  .popup-card {
    width: min(640px, 100%);
    background: #ffffff;
    border-radius: 22px;
    padding: 28px;
    box-shadow: 0 28px 60px rgba(15, 23, 42, 0.18);
    position: relative;
  }

  .popup-card h3 {
    margin: 0 0 16px;
    font-size: 22px;
    color: #0f172a;
  }

  .popup-card p {
    margin: 0 0 18px;
    color: #475569;
    line-height: 1.8;
  }

  .popup-card textarea {
    width: 100%;
    min-height: 140px;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 16px;
    resize: vertical;
    font-size: 14px;
    color: #0f172a;
    background: #f8fafc;
    box-sizing: border-box;
  }

  .popup-card .contact-info {
    margin: 20px 0;
    padding: 16px;
    background: #f1f5f9;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
    word-break: break-all;
    color: #0f172a;
  }

  .popup-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 18px;
  }

  .popup-button {
    cursor: pointer;
    border: none;
    border-radius: 12px;
    padding: 12px 18px;
    font-weight: 700;
  }

  .popup-button.primary {
    background: #0f766e;
    color: #ffffff;
  }

  .popup-button.secondary {
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid #cbd5e1;
  }

  .home-logo-button {
    position: absolute;
    top: 24px;
    left: 96px;
    width: 210px;
    height: 84px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 0;
    background: transparent;
    cursor: pointer;
    transition: transform 0.16s ease, filter 0.16s ease;
  }

  .home-logo-button:hover {
    transform: translateY(-1px);
    filter: drop-shadow(0 12px 18px rgba(15, 118, 110, 0.16));
  }

  .home-logo-button:focus-visible {
    outline: 3px solid rgba(20, 184, 166, 0.35);
    outline-offset: 3px;
  }

  .home-logo-button img {
    display: block;
    width: 210px;
    height: 84px;
    object-fit: contain;
  }

  @media (max-width: 1360px) {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    padding: 32px 28px;

    .home-logo-button {
      position: relative;
      top: 0;
      left: 0;
      width: 180px;
      height: 72px;
      margin: 0 auto 22px;
      flex-shrink: 0;
    }

    .home-logo-button img {
      width: 180px;
      height: 72px;
    }
  }

  @media (max-width: 640px) {
    padding: 32px 20px;

    .home-logo-button {
      width: 150px;
      height: 60px;
    }

    .home-logo-button img {
      width: 150px;
      height: 60px;
    }
  }
`;

const FAQContent = styled.div`
  width: 100%;
  max-width: 950px;
  margin: 0 auto;
  transform: translateX(50px);

  h2 {
    font-size: 32px;
    margin: 0 0 24px;
    color: #0f172a;
  }

  p.description {
    font-size: 15px;
    color: #475569;
    margin-bottom: 30px;
    line-height: 1.8;
  }

  .tab-list {
    display: flex;
    gap: 10px;
    margin-bottom: 28px;
    flex-wrap: wrap;
  }

  .tab-button {
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 700;
    border-radius: 999px;
    border: 1px solid #cbd5e1;
    background: #f8fafc;
    color: #0f172a;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .tab-button.active {
    background: #0f766e;
    color: #f8fafc;
    border-color: #0f766e;
  }

  .tab-button:hover {
    background: #e2e8f0;
  }

  .tab-panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 28px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
  }

  .question {
    margin-top: 24px;
  }

  .question h3 {
    font-size: 18px;
    margin-bottom: 10px;
    color: #111827;
  }

  .question p {
    margin: 0;
    font-size: 15px;
    color: #475569;
    line-height: 1.8;
  }

  .question ul {
    margin: 12px 0 0 20px;
    color: #475569;
  }

  .question li {
    margin-bottom: 10px;
  }

  .question a {
    color: #0f766e;
    font-weight: 800;
    text-decoration: none;
  }

  .question a:hover {
    text-decoration: underline;
  }

  .inline-clip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin: 0 2px;
    padding: 2px 7px;
    border: 1px solid rgba(15, 118, 110, 0.18);
    border-radius: 999px;
    background: rgba(240, 253, 250, 0.9);
    color: #0f766e;
    font-weight: 800;
    white-space: nowrap;
    vertical-align: baseline;
  }

  .inline-clip svg {
    width: 15px;
    height: 15px;
    stroke-width: 2.4;
  }

  .popup-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 50;
    padding: 18px;
  }

  .popup-card {
    width: min(640px, 100%);
    background: #ffffff;
    border-radius: 22px;
    padding: 28px;
    box-shadow: 0 28px 60px rgba(15, 23, 42, 0.18);
    position: relative;
  }

  .popup-card h3 {
    margin: 0 0 16px;
    font-size: 22px;
    color: #0f172a;
  }

  .popup-card p {
    margin: 0 0 18px;
    color: #475569;
    line-height: 1.8;
  }

  .popup-card textarea {
    width: 100%;
    min-height: 140px;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 16px;
    resize: vertical;
    font-size: 14px;
    color: #0f172a;
    background: #f8fafc;
  }

  .popup-card .contact-info {
    margin: 20px 0;
    padding: 16px;
    background: #f1f5f9;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
    word-break: break-all;
    color: #0f172a;
  }

  .popup-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 18px;
  }

  .popup-button {
    cursor: pointer;
    border: none;
    border-radius: 12px;
    padding: 12px 18px;
    font-weight: 700;
  }

  .popup-button.primary {
    background: #0f766e;
    color: #ffffff;
  }

  .popup-button.secondary {
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid #cbd5e1;
  }

  @media (max-width: 1360px) {
    max-width: 100%;
    margin: 0;
    transform: translateX(50px);

    h2 {
      font-size: 24px;
      line-height: 1.25;
      text-align: center;
      margin-bottom: 14px;
    }

    p.description {
      font-size: 13.5px;
      line-height: 1.65;
      text-align: center;
      margin-bottom: 22px;
    }

    .tab-list {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 18px;
    }

    .tab-button {
      width: 100%;
      padding: 10px 12px;
      font-size: 13px;
      border-radius: 12px;
      white-space: normal;
      word-break: keep-all;
    }

    .tab-panel {
      border-radius: 14px;
      padding: 20px;
    }

    .question {
      margin-top: 18px;
    }

    .question h3 {
      font-size: 16px;
      line-height: 1.4;
    }

    .question p,
    .question li {
      font-size: 13.5px;
      line-height: 1.7;
    }
  }

  @media (min-width: 761px) and (max-width: 1360px) {
    max-width: 820px;

    h2 {
      font-size: 28px;
    }

    p.description {
      font-size: 14px;
    }

    .tab-list {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }
`;

const tabItems = [
  { id: "usage", label: "사용법" },
  { id: "security", label: "보안" },
  { id: "other", label: "기타 질문" },
  { id: "contact", label: "관리자 문의" },
];

interface FAQProps {
  onBackHome?: () => void;
  showHomeLogo?: boolean;
}

function FAQC({ onBackHome, showHomeLogo = true }: FAQProps) {
  const [activeTab, setActiveTab] = useState("usage");
  const [isContactOpen, setIsContactOpen] = useState(false);
  const [contactMessage, setContactMessage] = useState("");
  const adminContact = "https://github.com/pokfamadm/project_v1";

  const handleOpenContact = () => setIsContactOpen(true);
  const handleCloseContact = () => setIsContactOpen(false);
  const handleSendMail = () => {
    const subject = encodeURIComponent("PaperMate 관리자 문의");
    const body = encodeURIComponent(
      `${contactMessage}\n\n관리자 GitHub 주소: ${adminContact}`,
    );
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  return (
    <FAQContainer>
      {showHomeLogo && (
        <button
          type="button"
          className="home-logo-button"
          onClick={onBackHome}
          aria-label="메인 화면으로 이동"
          title="메인 화면으로 이동"
        >
          <img src={papermateLogo} alt="PaperMate" />
        </button>
      )}
      <FAQContent>
      <h2>자주 묻는 질문 (FAQ)</h2>
      <p className="description">
        PaperMate 사용 중 필요한 정보를 빠르게 찾을 수 있도록 질문을 분류해 두었습니다.
      </p>

      <div className="tab-list">
        {tabItems.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`tab-button ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-panel">
        {activeTab === "usage" && (
          <>
            <div className="question">
              <h3>Q1. HWP 파일을 HWPX로 어떻게 변환하나요?</h3>
              <p>
                HWP 파일은 PaperMate에서 기본 분석만 가능합니다. 문서 미리보기, 이미지·차트 추출 등 전체 기능을 사용하려면 한글 프로그램에서 파일을 연 뒤 <strong>다른 이름으로 저장</strong>을 선택하고 파일 형식을 <strong>HWPX</strong>로 저장해 업로드해주세요.
              </p>
              <p>
                한글 프로그램이 없다면 한컴 다운로드 센터에서 필요한 뷰어 또는 설치 파일을 확인할 수 있습니다.{" "}
                <a
                  href="https://www.hancom.com/support/downloadCenter/download"
                  target="_blank"
                  rel="noreferrer"
                >
                  한컴 다운로드 센터 열기
                </a>
              </p>
              <p>
                다운로드 센터가 열리면 검색창에 <strong>HWPX 변환기</strong>를 입력해 변환 도구를 찾아주세요.
              </p>
            </div>

            <div className="question">
              <h3>Q2. 문서를 어떻게 업로드하고 저장하나요?</h3>
              <p>
                분석 화면의
                <span className="inline-clip">
                  <FiPaperclip aria-hidden="true" />
                  클립 버튼
                </span>
                을 눌러 문서를 업로드하시면 AI가 문서 내용을 자동으로 분석 및 요약합니다. 업로드 가능한 파일 형식은 PDF, HWP, HWPX, DOCX, 이미지 등입니다.
              </p>
              <p>
                모든 분석을 마친 뒤 초대코드로 프로젝트를 저장할 수 있습니다. 프로젝트를 저장해야 공유 기능을 사용할 수 있으니, 팀원과 함께 보려면 먼저 프로젝트 저장을 완료해주세요.
              </p>
            </div>

            <div className="question">
              <h3>Q3. 표 만들기와 이미지 추출은 어떻게 하나요?</h3>
              <p>
                문서를 업로드한 뒤 클립 메뉴를 열고
                <span className="inline-clip">
                  <FiGrid aria-hidden="true" />
                  표 만들기
                </span>
                를 누르면 문서 내용에서 표로 정리할 수 있는 정보를 추출해 표를 생성합니다.
              </p>
              <p>
                같은 메뉴에서
                <span className="inline-clip">
                  <FiImage aria-hidden="true" />
                  이미지 파일 추출
                </span>
                을 누르면 문서에 포함된 이미지나 시각 자료를 찾아 결과 영역에 정리합니다.
              </p>
              <p>
                PaperMate는 미리보기에 표시된 문서를 기준으로 내용을 요약하고 답변합니다. 분석 전에 미리보기에서 올바른 문서가 열렸는지 확인해주세요.
              </p>
            </div>

            <div className="question">
              <h3>Q4. 생성된 표, 이미지, 그래프는 어디서 확인하고 저장하나요?</h3>
              <p>
                생성된 표, 이미지 추출 결과, 그래프는 미리보기창 옆의 <strong>보관함</strong> 버튼을 눌러 확인할 수 있습니다. 보관함에서 원하는 자료를 선택하면 전체 보기로 크게 열어볼 수 있습니다.
              </p>
              <p>
                전체 보기 화면에서 필요한 자료를 <strong>시각화 보관함</strong>에 저장할 수 있습니다. 저장한 시각화 자료는 공유작업공간의 <strong>시각화 불러오기</strong> 버튼으로 다시 불러와 팀원과 함께 확인할 수 있습니다.
              </p>
            </div>

            <div className="question">
              <h3>Q5. 팀원과 공유작업공간에서 어떻게 협업하나요?</h3>
              <p>
                공유작업공간에서 초대 코드를 생성하거나 입력하여 팀원을 초대하실 수 있습니다. 프로젝트를 함께 열람하고 협업할 수 있습니다.
              </p>
            </div>

            <div className="question">
              <h3>Q6. FAQ에 없는 문의는 어디로 하나요?</h3>
              <p>
                추가 문의가 필요하시면 서비스 제공자에게 문의하거나 앱 내 지원 채널을 통해 질문을 남겨주세요.
              </p>
            </div>
          </>
        )}

        {activeTab === "security" && (
          <>
            <div className="question">
              <h3>Q1. 문서는 어떻게 저장되나요?</h3>
              <p>
                업로드된 문서는 서버에 임시 저장되며, 로그인한 사용자의 경우 프로젝트로 저장하면 해당 계정과 연결됩니다. 비로그인 상태에서는 분석 결과만 임시로 유지되며 브라우저를 닫거나 새로고침하면 사라질 수 있습니다.
              </p>
            </div>

            <div className="question">
              <h3>Q2. 로그아웃이나 탈퇴 시 내 데이터는 어떻게 되나요?</h3>
              <p>
                로그아웃하면 현재 세션 정보가 종료되고, 저장된 프로젝트와 기록은 계정에 남아 있습니다. 탈퇴 시에는 계정에 연결된 데이터가 삭제될 수 있으므로, 탈퇴 전에 필요한 문서나 프로젝트를 별도로 백업해 두는 것이 좋습니다.
              </p>
            </div>

            <div className="question">
              <h3>Q3. 문서를 다운로드할 수 있나요?</h3>
              <p>
                현재 PaperMate는 문서 자체를 직접 다운로드하는 방식보다는 분석 결과와 요약을 제공합니다. 업로드한 원본 파일은 서비스 정책에 따라 보관되며, 필요한 경우 별도 요청을 통해 파일을 받을 수 있는지 확인해야 합니다.
              </p>
            </div>

            <div className="question">
              <h3>Q4. 누구나 내 문서를 다운로드할 수 있나요?</h3>
              <p>
                아니요. 문서와 프로젝트는 초대 코드나 공유 권한이 있는 사용자만 접근할 수 있습니다. 공개하지 않은 프로젝트는 외부 사용자에게 노출되지 않습니다.
              </p>
            </div>
          </>
        )}

        {activeTab === "other" && (
          <>
            <div className="question">
              <h3>Q1. 로그인 없이도 사용할 수 있나요?</h3>
              <p>
                네, 일부 기능은 로그인 없이도 사용할 수 있습니다. 다만 프로젝트 저장, 공유, 최근 기록 복원 등은 로그인 후에 이용하실 수 있습니다.
              </p>
            </div>

            <div className="question">
              <h3>Q2. 모바일에서도 사용할 수 있나요?</h3>
              <p>
                현재는 웹 브라우저 기반 서비스로, 모바일 브라우저에서도 접속 가능합니다. 하지만 데스크톱 환경에 최적화되어 있어 작은 화면에서는 일부 UI가 제한될 수 있습니다.
              </p>
            </div>

            <div className="question">
              <h3>Q3. 사용 시 유의할 점이 있나요?</h3>
              <p>
                분석 결과는 AI 기반 요약이므로 중요한 공식이나 표, 이미지 내용은 일부 누락될 수 있습니다. 중요한 문서는 원본 파일을 보관하고, 결과를 검토 후 직접 확인하는 것이 안전합니다.
              </p>
            </div>

            <div className="question">
              <h3>Q4. 다른 고객 문의는 어떻게 하나요?</h3>
              <p>
                고객 문의가 필요한 경우 서비스 제공자의 연락처 또는 앱 내 지원 채널을 통해 문의해 주세요. 문의 시 가능한 자세한 내용을 함께 전달하면 빠른 답변을 받을 수 있습니다.
              </p>
            </div>
          </>
        )}

        {activeTab === "contact" && (
          <>
            <div className="question">
              <h3>관리자 문의</h3>
              <p>
                관리자 문의는 아래 팝업에서 메시지를 작성하신 뒤 메일 클라이언트로 연결해 주세요.
              </p>
              <button type="button" className="tab-button active" onClick={handleOpenContact}>
                이메일 문의 열기
              </button>
            </div>
          </>
        )}
      </div>

      </FAQContent>

      {isContactOpen && (
        <div className="popup-overlay" onClick={handleCloseContact}>
          <div className="popup-card" onClick={(event) => event.stopPropagation()}>
            <h3>관리자 이메일 문의</h3>
            <p>아래에 문의 내용을 작성한 뒤 메일 클라이언트를 통해 발송할 수 있습니다.</p>
            <div className="contact-info">관리자 GitHub 주소: {adminContact}</div>
            <textarea
              value={contactMessage}
              onChange={(event) => setContactMessage(event.target.value)}
              placeholder="문의 내용을 입력하세요..."
            />
            <div className="popup-actions">
              <button type="button" className="popup-button secondary" onClick={handleCloseContact}>
                닫기
              </button>
              <button type="button" className="popup-button primary" onClick={handleSendMail}>
                메일 보내기
              </button>
            </div>
          </div>
        </div>
      )}
    </FAQContainer>
  );
}

export default FAQC;
