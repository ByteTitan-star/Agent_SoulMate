import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { DashboardPage } from '@/components/DashboardPage';
import { HomePage } from '@/pages/HomePage';
import { PlazaPage } from '@/pages/PlazaPage';
import { CreateCharacterPage } from '@/pages/CreateCharacterPage';
import { ChatPage } from '@/pages/ChatPage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { RequireAuth } from '@/components/RequireAuth';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="plaza" element={<PlazaPage />} />
          <Route path="create" element={<RequireAuth><CreateCharacterPage /></RequireAuth>} />
          <Route path="chat/:characterId" element={<ChatPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route
            path="dashboard"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
