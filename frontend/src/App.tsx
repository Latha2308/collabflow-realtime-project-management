import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { useAppStore } from './stores/appStore'

// Pages - will be created
import LoginPage from './features/auth/LoginPage'
import RegisterPage from './features/auth/RegisterPage'
import DashboardLayout from './components/layout/DashboardLayout'
import WorkspacesPage from './features/workspaces/WorkspacesPage'
import ProjectsPage from './features/projects/ProjectsPage'
import BoardPage from './features/board/BoardPage'
import AnalyticsPage from './features/analytics/AnalyticsPage'

function App() {
  const { loadUser, isLoading, isAuthenticated } = useAuthStore()
  const { theme } = useAppStore()

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading CollabFlow...</div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/" />} />
      <Route path="/register" element={!isAuthenticated ? <RegisterPage /> : <Navigate to="/" />} />
      
      <Route path="/" element={isAuthenticated ? <DashboardLayout /> : <Navigate to="/login" />}>
        <Route index element={<WorkspacesPage />} />
        <Route path="workspaces/:workspaceId" element={<ProjectsPage />} />
        <Route path="projects/:projectId/board" element={<BoardPage />} />
        <Route path="projects/:projectId/analytics" element={<AnalyticsPage />} />
      </Route>
    </Routes>
  )
}

export default App
