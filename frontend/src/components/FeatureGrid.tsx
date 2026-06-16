// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 이 컴포넌트는 별도 props가 없어서 함수 선언만 TSX 형태로 유지하면 됩니다.
// 초보자 안내: 메인 화면에서 기능 소개 카드들을 한 번에 보여주는 재사용 컴포넌트입니다.

import { FeatureCard, GridSection } from './styles/FeatureGrid.styles';

function FeatureGrid() {
  return (
    <GridSection>
      <FeatureCard>
        <div className="icon-wrap"><i className="fa-solid fa-file-invoice"></i></div>
        <div>
          <h3>문서 분석 · 요약</h3>
          <p>HWP, HWPX, PDF 문서의 핵심 내용을 추출하고 요약합니다.</p>
        </div>
      </FeatureCard>

      <FeatureCard>
        <div className="icon-wrap"><i className="fa-solid fa-copy"></i></div>
        <div>
          <h3>다중문서 비교</h3>
          <p>여러 문서를 비교하고 차이점을 시각화합니다.</p>
        </div>
      </FeatureCard>

      <FeatureCard>
        <div className="icon-wrap"><i className="fa-solid fa-chart-bar"></i></div>
        <div>
          <h3>데이터 시각화</h3>
          <p>문서 속 데이터를 차트와 그래프로 변환합니다.</p>
        </div>
      </FeatureCard>

      <FeatureCard>
        <div className="icon-wrap"><i className="fa-solid fa-user-group"></i></div>
        <div>
          <h3>공유작업공간</h3>
          <p>초대 코드로 팀원을 초대하고 분석 결과를 함께 검토합니다.</p>
        </div>
      </FeatureCard>
    </GridSection>
  );
}

export default FeatureGrid;
