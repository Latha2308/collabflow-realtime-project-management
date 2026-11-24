/**
 * API service for communicating with the CollabFlow backend.
 * Uses fetch with credentials for cookie-based authentication.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
const API_V1 = `${API_URL}/api/v1`;

class ApiError extends Error {
  constructor(public status: number, message: string, public data?: any) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || response.statusText,
      errorData
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

// Authentication
export const authApi = {
  register: (data: any) => fetchWithAuth(`${API_V1}/auth/register`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  login: (data: any) => fetchWithAuth(`${API_V1}/auth/login`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  logout: () => fetchWithAuth(`${API_V1}/auth/logout`, {
    method: 'POST',
  }),

  getCurrentUser: () => fetchWithAuth(`${API_V1}/auth/me`),
};

// Workspaces
export const workspacesApi = {
  list: () => fetchWithAuth(`${API_V1}/workspaces`),
  
  create: (data: any) => fetchWithAuth(`${API_V1}/workspaces`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  get: (id: string) => fetchWithAuth(`${API_V1}/workspaces/${id}`),

  update: (id: string, data: any) => fetchWithAuth(`${API_V1}/workspaces/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  delete: (id: string) => fetchWithAuth(`${API_V1}/workspaces/${id}`, {
    method: 'DELETE',
  }),

  listMembers: (id: string) => fetchWithAuth(`${API_V1}/workspaces/${id}/members`),

  addMember: (id: string, data: any) => fetchWithAuth(`${API_V1}/workspaces/${id}/members`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateMember: (workspaceId: string, memberId: string, data: any) =>
    fetchWithAuth(`${API_V1}/workspaces/${workspaceId}/members/${memberId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  removeMember: (workspaceId: string, memberId: string) =>
    fetchWithAuth(`${API_V1}/workspaces/${workspaceId}/members/${memberId}`, {
      method: 'DELETE',
    }),
};

// Projects
export const projectsApi = {
  list: (workspaceId: string) => fetchWithAuth(`${API_V1}/projects?workspace_id=${workspaceId}`),

  create: (data: any) => fetchWithAuth(`${API_V1}/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  get: (id: string) => fetchWithAuth(`${API_V1}/projects/${id}`),

  update: (id: string, data: any) => fetchWithAuth(`${API_V1}/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  delete: (id: string) => fetchWithAuth(`${API_V1}/projects/${id}`, {
    method: 'DELETE',
  }),
};

// Tasks
export const tasksApi = {
  list: (projectId: string, status?: string) => {
    const url = status
      ? `${API_V1}/tasks?project_id=${projectId}&status=${status}`
      : `${API_V1}/tasks?project_id=${projectId}`;
    return fetchWithAuth(url);
  },

  create: (data: any) => fetchWithAuth(`${API_V1}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  get: (id: string) => fetchWithAuth(`${API_V1}/tasks/${id}`),

  update: (id: string, data: any) => fetchWithAuth(`${API_V1}/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  delete: (id: string) => fetchWithAuth(`${API_V1}/tasks/${id}`, {
    method: 'DELETE',
  }),

  // Dependencies
  listDependencies: (projectId: string) =>
    fetchWithAuth(`${API_V1}/tasks/dependencies?project_id=${projectId}`),

  createDependency: (data: any) => fetchWithAuth(`${API_V1}/tasks/dependencies`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  deleteDependency: (id: string) => fetchWithAuth(`${API_V1}/tasks/dependencies/${id}`, {
    method: 'DELETE',
  }),

  // Comments
  listComments: (taskId: string) => fetchWithAuth(`${API_V1}/tasks/${taskId}/comments`),

  createComment: (data: any) => fetchWithAuth(`${API_V1}/tasks/comments`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};

// Analytics
export const analyticsApi = {
  getProjectOverview: (projectId: string) =>
    fetchWithAuth(`${API_V1}/analytics/projects/${projectId}/overview`),

  getGraphAnalysis: (projectId: string) =>
    fetchWithAuth(`${API_V1}/analytics/projects/${projectId}/graph-analysis`),
};

export { ApiError };
