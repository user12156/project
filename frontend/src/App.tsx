// TypeScript 변경 표시: JSX가 들어 있는 React 파일이라 .js에서 .tsx로 바꾼 파일입니다.
// TypeScript 변경 표시: 기존 JS 로직은 유지하면서 함수 인자와 화면 props에 실제 타입을 붙여 TypeScript 검사를 통과하게 했습니다.
// 초보자 안내: PaperMate 프론트엔드의 최상위 컴포넌트입니다. 로그인 상태와 메인 화면을 감쌉니다.

import React from 'react';
import Home from './pages/Home';
import { AuthProvider } from './context/AuthContext';

interface AppErrorBoundaryProps {
  children: React.ReactNode;
}

interface AppErrorBoundaryState {
  error: Error | null;
  resetKey: number;
}

class AppErrorBoundary extends React.Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  constructor(props: AppErrorBoundaryProps) {
    super(props);
    this.state = { error: null, resetKey: 0 };
  }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error, resetKey: 0 };
  }

  handleScreenRefresh = () => {
    this.setState((prev) => ({
      error: null,
      resetKey: prev.resetKey + 1,
    }));
  };

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 32, fontFamily: 'sans-serif', color: '#0f172a' }}>
          <h2>화면을 불러오지 못했습니다.</h2>
          <p>저장된 임시 데이터 형식이 맞지 않아 화면이 멈췄을 수 있습니다.</p>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#dc2626' }}>
            {this.state.error.message}
          </pre>
          <button type="button" onClick={this.handleScreenRefresh}>
            다시 불러오기
          </button>
        </div>
      );
    }

    return <React.Fragment key={this.state.resetKey}>{this.props.children}</React.Fragment>;
  }
}

function App() {
  return (
    <AuthProvider>
      <AppErrorBoundary>
        <div className="App">
          <Home />
        </div>
      </AppErrorBoundary>
    </AuthProvider>
  );
}

export default App;
