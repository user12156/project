import {Route, Routes} from 'react-router-dom';
import LoginPage from './이인희 src 코드 생성/Login/pages/LoginPage';
import RegisterPage from './이인희 src 코드 생성/Login/pages/RegisterPage';

const App = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/RegisterPage" element={<RegisterPage />} />
    </Routes>
  );
};

export default App;