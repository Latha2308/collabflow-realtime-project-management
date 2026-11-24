import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useAppStore } from '@/stores/appStore'
import { Button } from '@/components/ui/button'
import { LayoutDashboard, LogOut, Menu, X } from 'lucide-react'

export default function DashboardLayout() {
  const { user, logout } = useAuthStore()
  const { sidebarOpen, toggleSidebar } = useAppStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-0'
        } transition-all duration-300 overflow-hidden bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700`}
      >
        <div className="flex flex-col h-full">
          <div className="p-6">
            <h1 className="text-2xl font-bold text-primary">CollabFlow</h1>
            <p className="text-sm text-muted-foreground mt-1">{user?.full_name}</p>
          </div>

          <nav className="flex-1 px-4 space-y-2">
            <Link
              to="/"
              className="flex items-center px-4 py-2 text-sm font-medium rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <LayoutDashboard className="w-5 h-5 mr-3" />
              Workspaces
            </Link>
          </nav>

          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={handleLogout}
            >
              <LogOut className="w-5 h-5 mr-3" />
              Logout
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation */}
        <header className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center px-6">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="mr-4"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <h2 className="text-xl font-semibold">Dashboard</h2>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
