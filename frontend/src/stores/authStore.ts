import { create } from 'zustand';
import type { User } from '@/types';
import { authApi } from '@/services/api';

interface RegisterData {
  email: string;
  username: string;
  full_name: string;
  password: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  
  setUser: (user: User | null) => void;
  loadUser: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  setUser: (user) => set({ 
    user, 
    isAuthenticated: !!user,
    isLoading: false 
  }),

  loadUser: async () => {
    try {
      const user = await authApi.getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  login: async (username, password) => {
    await authApi.login({ username, password });
    // Token is stored in HttpOnly cookie by backend - don't store in localStorage
    const user = await authApi.getCurrentUser();
    set({ user, isAuthenticated: true });
  },

  logout: async () => {
    await authApi.logout();
    // Cookie is cleared by backend
    set({ user: null, isAuthenticated: false });
  },

  register: async (data) => {
    await authApi.register(data);
  },
}));
