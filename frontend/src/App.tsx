import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute, GuestRoute } from './components/layout/ProtectedRoute';

import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { ChatPage } from './pages/ChatPage';
import { QuizzesPage } from './pages/QuizzesPage';
import { QuizCreatePage } from './pages/QuizCreatePage';
import { QuizTakePage } from './pages/QuizTakePage';
import { QuizResultPage } from './pages/QuizResultPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ImprovementPlanPage } from './pages/ImprovementPlanPage';
import { NotFoundPage } from './pages/NotFoundPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Guest-only routes (redirect to / if logged in) */}
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* Protected routes (redirect to /login if not authenticated) */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/quizzes" element={<QuizzesPage />} />
            <Route path="/quizzes/new" element={<QuizCreatePage />} />
            <Route path="/quizzes/:quizId/take" element={<QuizTakePage />} />
            <Route path="/quizzes/:quizId/result" element={<QuizResultPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/improvement/:planId" element={<ImprovementPlanPage />} />
          </Route>

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
