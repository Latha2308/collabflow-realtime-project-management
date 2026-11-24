import { create } from 'zustand';

interface AppState {
  currentWorkspaceId: string | null;
  currentProjectId: string | null;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  
  setCurrentWorkspace: (id: string | null) => void;
  setCurrentProject: (id: string | null) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentWorkspaceId: null,
  currentProjectId: null,
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  sidebarOpen: true,

  setCurrentWorkspace: (id) => set({ currentWorkspaceId: id }),
  
  setCurrentProject: (id) => set({ currentProjectId: id }),
  
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    set({ theme });
  },
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
