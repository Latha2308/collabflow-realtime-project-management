// Core types for CollabFlow application

export enum TaskStatus {
  BACKLOG = 'backlog',
  TODO = 'todo',
  IN_PROGRESS = 'in_progress',
  IN_REVIEW = 'in_review',
  DONE = 'done',
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
}

export enum WorkspaceRole {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer',
}

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  role: WorkspaceRole;
  joined_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  assignee_id?: string;
  created_by_id: string;
  due_date?: string;
  estimated_hours?: number;
  position: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface TaskDependency {
  id: string;
  task_id: string;
  depends_on_id: string;
  created_at: string;
}

export interface Comment {
  id: string;
  task_id: string;
  author_id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Analytics {
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  overdue_tasks: number;
  completion_rate: number;
  tasks_by_status: Record<string, number>;
  tasks_by_priority: Record<string, number>;
  team_workload: Array<{ assignee_id: string; task_count: number }>;
  completion_trend: Array<{ date: string; completed: number }>;
}

export interface GraphAnalysis {
  topological_order: string[];
  critical_path: string[];
  critical_path_duration: number;
  blocked_tasks: Record<string, string[]>;
  has_cycle: boolean;
}

// WebSocket message types
export interface WSMessage {
  type: string;
  user_id?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}

// API request types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  full_name: string;
  password: string;
}

export interface CreateWorkspaceRequest {
  name: string;
  description?: string;
}

export interface CreateProjectRequest {
  workspace_id: string;
  name: string;
  description?: string;
}

export interface CreateTaskRequest {
  project_id: string;
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string;
  due_date?: string;
  estimated_hours?: number;
}

export interface UpdateTaskRequest {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string;
  due_date?: string;
  estimated_hours?: number;
  position?: number;
  version: number;
}

export interface CreateDependencyRequest {
  task_id: string;
  depends_on_id: string;
}

export interface CreateCommentRequest {
  task_id: string;
  content: string;
}
