/**
 * Tests for API service CSRF token handling
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('API Service CSRF Token Handling', () => {
  beforeEach(() => {
    // Clear cookies before each test
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';

    // Clear fetch mocks
    vi.clearAllMocks();
  });

  it('should include X-CSRF-Token header on POST requests when cookie is present', async () => {
    // Set CSRF cookie
    document.cookie = 'csrf_token=test-csrf-token-123';

    // Mock fetch
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: '123', title: 'Test Task' }),
    });
    global.fetch = mockFetch;

    // Import after setting up mocks
    const { tasksApi } = await import('./api');

    // Make a POST request
    await tasksApi.create({
      project_id: 'proj-123',
      title: 'Test Task',
      status: 'todo',
    });

    // Verify fetch was called with CSRF header
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/tasks'),
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: expect.objectContaining({
          'X-CSRF-Token': 'test-csrf-token-123',
          'Content-Type': 'application/json',
        }),
      })
    );
  });

  it('should include X-CSRF-Token header on PATCH requests', async () => {
    document.cookie = 'csrf_token=test-csrf-token-456';

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: '123', status: 'done' }),
    });
    global.fetch = mockFetch;

    const { tasksApi } = await import('./api');

    await tasksApi.update('123', { status: 'done', version: 1 });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/tasks/123'),
      expect.objectContaining({
        method: 'PATCH',
        headers: expect.objectContaining({
          'X-CSRF-Token': 'test-csrf-token-456',
        }),
      })
    );
  });

  it('should include X-CSRF-Token header on DELETE requests', async () => {
    document.cookie = 'csrf_token=test-csrf-token-789';

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
    });
    global.fetch = mockFetch;

    const { tasksApi } = await import('./api');

    await tasksApi.delete('123');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/tasks/123'),
      expect.objectContaining({
        method: 'DELETE',
        headers: expect.objectContaining({
          'X-CSRF-Token': 'test-csrf-token-789',
        }),
      })
    );
  });

  it('should NOT include X-CSRF-Token header on GET requests', async () => {
    document.cookie = 'csrf_token=test-csrf-token-999';

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [{ id: '123' }],
    });
    global.fetch = mockFetch;

    const { tasksApi } = await import('./api');

    await tasksApi.list('proj-123');

    // GET request should not have CSRF token
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/tasks'),
      expect.objectContaining({
        credentials: 'include',
        headers: expect.not.objectContaining({
          'X-CSRF-Token': expect.anything(),
        }),
      })
    );
  });

  it('should handle missing CSRF cookie gracefully', async () => {
    // No CSRF cookie set

    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ detail: 'CSRF token missing' }),
    });
    global.fetch = mockFetch;

    const { tasksApi } = await import('./api');

    // Should attempt the request even without CSRF token
    // Backend will return 403
    await expect(tasksApi.create({ title: 'Test' })).rejects.toThrow();

    // Verify request was made (without CSRF header)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/tasks'),
      expect.objectContaining({
        method: 'POST',
        // Headers should not contain X-CSRF-Token
        headers: expect.not.objectContaining({
          'X-CSRF-Token': expect.anything(),
        }),
      })
    );
  });
});
