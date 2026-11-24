import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
    });
  });

  it('should have initial state', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('should set user', () => {
    const mockUser = {
      id: '123',
      email: 'test@test.com',
      username: 'testuser',
      full_name: 'Test User',
      is_active: true,
      created_at: '2026-11-23',
      updated_at: '2026-11-23',
    };

    useAuthStore.getState().setUser(mockUser);
    
    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
  });

  it('should clear user', () => {
    const mockUser = {
      id: '123',
      email: 'test@test.com',
      username: 'testuser',
      full_name: 'Test User',
      is_active: true,
      created_at: '2026-11-23',
      updated_at: '2026-11-23',
    };

    useAuthStore.getState().setUser(mockUser);
    expect(useAuthStore.getState().user).toEqual(mockUser);

    useAuthStore.getState().setUser(null);
    expect(useAuthStore.getState().user).toBeNull();
  });
});
