// src/App.js
import React from 'react';
// 팀장님 폴더 경로에 맞춰서 불러오기 (경로 예시)
import LoginPage from './members/팀장님/LoginPage'; 

function App() {
  return (
    <div className="App">
      {/* 내가 만든 로그인 페이지가 화면에 뜹니다! */}
      <LoginPage />
    </div>
  );
}

export default App;