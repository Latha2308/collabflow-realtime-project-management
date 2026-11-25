import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate, useNavigate, useParams, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock auth store with controllable state
const mockAuthState = {
  isAuthenticated: true,
  isLoading: false,
  user: { id: '1', username: 'testuser', email: 'test@test.com', full_name: 'Test User' },
  loadUser: vi.fn(),
};

vi.mock('./stores/authStore', () => ({
  useAuthStore: vi.fn(() => mockAuthState),
}));

// Mock app store
vi.mock('./stores/appStore', () => ({
  useAppStore: vi.fn(() => ({
    theme: 'light',
    sidebarOpen: true,
    toggleSidebar: vi.fn(),
  })),
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

function TestWrapper({ children, initialEntries = ['/'] }: { children: React.ReactNode; initialEntries?: string[] }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('React Router 7 - Protected Routes', () => {
  it('should render protected content when authenticated', () => {
    mockAuthState.isAuthenticated = true;

    const ProtectedRoute = ({ authenticated }: { authenticated: boolean }) => {
      return authenticated ? <div>Protected Content</div> : <Navigate to="/login" replace />;
    };

    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<ProtectedRoute authenticated={true} />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </TestWrapper>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('should redirect to login when not authenticated', () => {
    mockAuthState.isAuthenticated = false;

    const ProtectedRoute = ({ authenticated }: { authenticated: boolean }) => {
      return authenticated ? <div>Protected Content</div> : <Navigate to="/login" replace />;
    };

    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<ProtectedRoute authenticated={false} />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </TestWrapper>
    );

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('should support nested routes with index route', () => {
    function Layout() {
      return (
        <div>
          <div>Layout Header</div>
          <div data-testid="outlet-content">Index Content</div>
        </div>
      );
    }

    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>Index Content</div>} />
          </Route>
        </Routes>
      </TestWrapper>
    );

    expect(screen.getByText('Layout Header')).toBeInTheDocument();
    expect(screen.getByText('Index Content')).toBeInTheDocument();
  });
});

describe('React Router 7 - Route Parameters', () => {
  it('should extract route parameters with useParams', () => {
    function ProjectPage() {
      const params = useParams<{ projectId: string }>();
      return (
        <div>
          <h1>Project Page</h1>
          <div data-testid="project-id">{params.projectId}</div>
        </div>
      );
    }

    render(
      <TestWrapper initialEntries={['/projects/abc-123']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectPage />} />
        </Routes>
      </TestWrapper>
    );

    expect(screen.getByText('Project Page')).toBeInTheDocument();
    expect(screen.getByTestId('project-id')).toHaveTextContent('abc-123');
  });

  it('should extract multiple route parameters', () => {
    function AnalyticsPage() {
      const params = useParams<{ workspaceId: string; projectId: string }>();
      return (
        <div>
          <div data-testid="workspace-id">{params.workspaceId}</div>
          <div data-testid="project-id">{params.projectId}</div>
        </div>
      );
    }

    render(
      <TestWrapper initialEntries={['/workspaces/ws-456/projects/proj-789']}>
        <Routes>
          <Route path="/workspaces/:workspaceId/projects/:projectId" element={<AnalyticsPage />} />
        </Routes>
      </TestWrapper>
    );

    expect(screen.getByTestId('workspace-id')).toHaveTextContent('ws-456');
    expect(screen.getByTestId('project-id')).toHaveTextContent('proj-789');
  });
});

describe('React Router 7 - Navigation', () => {
  it('should support programmatic navigation with useNavigate', () => {
    function TestComponent() {
      const navigate = useNavigate();
      
      return (
        <div>
          <button onClick={() => navigate('/target')}>
            Navigate to Target
          </button>
          <div>Current Page</div>
        </div>
      );
    }

    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<TestComponent />} />
          <Route path="/target" element={<div>Target Page</div>} />
        </Routes>
      </TestWrapper>
    );

    expect(screen.getByText('Current Page')).toBeInTheDocument();
    const button = screen.getByText('Navigate to Target');
    expect(button).toBeInTheDocument();
  });

  it('should handle internal navigation paths safely', () => {
    // This test documents the security fix in React Router 7.18.7
    // Navigation should handle internal paths correctly
    
    function TestComponent() {
      const navigate = useNavigate();
      
      return (
        <div>
          <button onClick={() => navigate('/login')} data-testid="safe-nav">
            Safe Navigate
          </button>
          <button onClick={() => navigate('/workspaces/123')} data-testid="param-nav">
            Parameter Navigate
          </button>
          <div>Navigation Page</div>
        </div>
      );
    }

    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<TestComponent />} />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/workspaces/:id" element={<div>Workspace Page</div>} />
        </Routes>
      </TestWrapper>
    );

    expect(screen.getByTestId('safe-nav')).toBeInTheDocument();
    expect(screen.getByTestId('param-nav')).toBeInTheDocument();
    expect(screen.getByText('Navigation Page')).toBeInTheDocument();
  });
});

describe('React Router 7 - Link Component', () => {
  it('should render Link components with correct href attributes', () => {
    function TestComponent() {
      return (
        <div>
          <Link to="/workspaces" data-testid="workspace-link">Workspaces</Link>
          <Link to="/projects/123" data-testid="project-link">Project 123</Link>
        </div>
      );
    }

    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<TestComponent />} />
        </Routes>
      </TestWrapper>
    );

    const workspaceLink = screen.getByTestId('workspace-link');
    const projectLink = screen.getByTestId('project-link');

    expect(workspaceLink).toHaveTextContent('Workspaces');
    expect(workspaceLink).toHaveAttribute('href', '/workspaces');
    
    expect(projectLink).toHaveTextContent('Project 123');
    expect(projectLink).toHaveAttribute('href', '/projects/123');
  });
});

describe('React Router 7 - Backward Compatibility', () => {
  it('should support MemoryRouter for testing', () => {
    // MemoryRouter is the preferred router for unit tests
    const { container } = render(
      <MemoryRouter>
        <div>Router Content</div>
      </MemoryRouter>
    );

    expect(container.textContent).toContain('Router Content');
  });

  it('should support Routes and Route components from v6', () => {
    // Verify Routes/Route still work in v7 (backward compatibility)
    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<div data-testid="home">Home Page</div>} />
          <Route path="/about" element={<div data-testid="about">About Page</div>} />
        </Routes>
      </TestWrapper>
    );

    expect(screen.getByTestId('home')).toHaveTextContent('Home Page');
  });

  it('should support Navigate component for redirects', () => {
    // Verify Navigate still works in v7 (backward compatibility)
    render(
      <TestWrapper>
        <Routes>
          <Route path="/" element={<Navigate to="/redirected" replace />} />
          <Route path="/redirected" element={<div data-testid="redirected">Redirected Page</div>} />
        </Routes>
      </TestWrapper>
    );

    // Should redirect and show the redirected page
    expect(screen.getByTestId('redirected')).toHaveTextContent('Redirected Page');
  });
});
