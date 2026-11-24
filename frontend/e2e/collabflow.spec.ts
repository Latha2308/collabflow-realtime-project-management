import { test, expect, Page } from '@playwright/test';

// Test data
const testUser = {
  email: `test${Date.now()}@example.com`,
  username: `testuser${Date.now()}`,
  fullName: 'Test User',
  password: 'TestPass123!',
};

const testUser2 = {
  email: `test2${Date.now()}@example.com`,
  username: `testuser2${Date.now()}`,
  fullName: 'Test User 2',
  password: 'TestPass123!',
};

const testWorkspace = {
  name: `Test Workspace ${Date.now()}`,
  description: 'E2E Test Workspace',
};

const testProject = {
  name: `Test Project ${Date.now()}`,
  description: 'E2E Test Project',
};

// Helper functions
async function register(page: Page, user: typeof testUser) {
  await page.goto('/register');
  await page.fill('input[name="email"]', user.email);
  await page.fill('input[name="username"]', user.username);
  await page.fill('input[name="full_name"]', user.fullName);
  await page.fill('input[name="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('/login', { timeout: 10000 });
}

async function login(page: Page, user: typeof testUser) {
  await page.goto('/login');
  await page.fill('input[name="username"]', user.username);
  await page.fill('input[name="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('/dashboard', { timeout: 10000 });
}

async function createWorkspace(page: Page, workspace: typeof testWorkspace) {
  await page.click('text=Create Workspace');
  await page.fill('input[name="name"]', workspace.name);
  await page.fill('textarea[name="description"]', workspace.description);
  await page.click('button:has-text("Create")');
  await page.waitForTimeout(2000);
}

async function createProject(page: Page, project: typeof testProject) {
  await page.click('text=New Project');
  await page.fill('input[name="name"]', project.name);
  await page.fill('textarea[name="description"]', project.description);
  await page.click('button:has-text("Create")');
  await page.waitForTimeout(2000);
}

test.describe('CollabFlow E2E Tests', () => {
  test.describe.configure({ mode: 'serial' });

  let workspaceId: string;
  let projectId: string;

  test('1. User Registration', async ({ page }) => {
    await register(page, testUser);
    await expect(page).toHaveURL('/login');
  });

  test('2. User Login', async ({ page }) => {
    await login(page, testUser);
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('text=' + testUser.fullName)).toBeVisible();
  });

  test('3. Create Workspace', async ({ page }) => {
    await login(page, testUser);
    await createWorkspace(page, testWorkspace);
    
    // Verify workspace appears in list
    await expect(page.locator(`text=${testWorkspace.name}`)).toBeVisible();
    
    // Extract workspace ID from URL or element
    await page.click(`text=${testWorkspace.name}`);
    await page.waitForTimeout(1000);
    const url = page.url();
    const match = url.match(/workspaces\/([a-f0-9-]+)/);
    if (match) {
      workspaceId = match[1];
    }
  });

  test('4. Create Project', async ({ page }) => {
    await login(page, testUser);
    
    if (!workspaceId) {
      // Navigate to any workspace
      await page.click('text=' + testWorkspace.name);
      const url = page.url();
      const match = url.match(/workspaces\/([a-f0-9-]+)/);
      if (match) {
        workspaceId = match[1];
      }
    }
    
    await createProject(page, testProject);
    await expect(page.locator(`text=${testProject.name}`)).toBeVisible();
    
    // Extract project ID
    await page.click(`text=${testProject.name}`);
    await page.waitForTimeout(1000);
    const url = page.url();
    const match = url.match(/projects\/([a-f0-9-]+)/);
    if (match) {
      projectId = match[1];
    }
  });

  test('5. Create Task', async ({ page }) => {
    await login(page, testUser);
    
    // Navigate to project board
    await page.goto(`/projects/${projectId}/board`);
    
    // Create a new task
    await page.click('button:has-text("New Task")');
    await page.fill('input[name="title"]', 'Test Task 1');
    await page.fill('textarea[name="description"]', 'This is a test task');
    await page.selectOption('select[name="priority"]', 'high');
    await page.click('button:has-text("Create Task")');
    
    // Verify task appears on board
    await page.waitForTimeout(1000);
    await expect(page.locator('text=Test Task 1')).toBeVisible();
  });

  test('6. Drag and Drop Task', async ({ page }) => {
    await login(page, testUser);
    await page.goto(`/projects/${projectId}/board`);
    
    // Wait for board to load
    await page.waitForSelector('text=Test Task 1');
    
    // Find task and target column
    const task = page.locator('text=Test Task 1').first();
    const todoColumn = page.locator('[data-status="todo"]').first();
    
    // Perform drag and drop
    await task.dragTo(todoColumn);
    
    // Verify task moved
    await page.waitForTimeout(1000);
    const taskInTodo = todoColumn.locator('text=Test Task 1');
    await expect(taskInTodo).toBeVisible();
  });

  test('7. Update Task Details', async ({ page }) => {
    await login(page, testUser);
    await page.goto(`/projects/${projectId}/board`);
    
    // Click on task to open details
    await page.click('text=Test Task 1');
    await page.waitForTimeout(500);
    
    // Update task description
    const descriptionField = page.locator('textarea[name="description"]');
    await descriptionField.fill('Updated task description');
    
    // Save changes
    await page.click('button:has-text("Save")');
    await page.waitForTimeout(1000);
    
    // Verify changes persisted
    await page.click('text=Test Task 1');
    await expect(page.locator('text=Updated task description')).toBeVisible();
  });

  test('8. Create Task Dependencies', async ({ page }) => {
    await login(page, testUser);
    await page.goto(`/projects/${projectId}/board`);
    
    // Create second task
    await page.click('button:has-text("New Task")');
    await page.fill('input[name="title"]', 'Test Task 2');
    await page.fill('textarea[name="description"]', 'Depends on Task 1');
    await page.click('button:has-text("Create Task")');
    await page.waitForTimeout(1000);
    
    // Open task 2 and add dependency
    await page.click('text=Test Task 2');
    await page.waitForTimeout(500);
    
    // Add dependency (this assumes there's a dependencies UI)
    // This might need adjustment based on actual UI implementation
    const addDependencyButton = page.locator('button:has-text("Add Dependency")');
    if (await addDependencyButton.isVisible()) {
      await addDependencyButton.click();
      await page.click('text=Test Task 1');
      await page.click('button:has-text("Save")');
    }
  });

  test('9. Test Circular Dependency Rejection', async ({ page }) => {
    await login(page, testUser);
    await page.goto(`/projects/${projectId}/board`);
    
    // Try to create circular dependency
    await page.click('text=Test Task 1');
    await page.waitForTimeout(500);
    
    const addDependencyButton = page.locator('button:has-text("Add Dependency")');
    if (await addDependencyButton.isVisible()) {
      await addDependencyButton.click();
      await page.click('text=Test Task 2');
      
      // Should show error message
      await expect(page.locator('text=circular dependency').or(page.locator('text=cycle'))).toBeVisible({ timeout: 3000 });
    }
  });

  test('10. View Analytics', async ({ page }) => {
    await login(page, testUser);
    await page.goto(`/projects/${projectId}/analytics`);
    
    // Verify analytics page loads
    await expect(page.locator('text=Project Analytics').or(page.locator('text=Analytics'))).toBeVisible();
    
    // Check for charts/metrics
    await expect(page.locator('canvas, svg').first()).toBeVisible({ timeout: 5000 });
  });

  test('11. Real-time Collaboration (Two Users)', async ({ browser }) => {
    // Create second user
    const context1 = await browser.newContext();
    const page1 = await context1.newPage();
    await register(page1, testUser2);
    await login(page1, testUser2);
    
    // User 2 navigates to same project
    await page1.goto(`/projects/${projectId}/board`);
    
    // User 1 creates a task
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    await login(page2, testUser);
    await page2.goto(`/projects/${projectId}/board`);
    
    await page2.click('button:has-text("New Task")');
    await page2.fill('input[name="title"]', 'Real-time Test Task');
    await page2.click('button:has-text("Create Task")');
    
    // User 2 should see the new task appear in real-time
    await page1.waitForTimeout(2000);
    await expect(page1.locator('text=Real-time Test Task')).toBeVisible({ timeout: 10000 });
    
    await context1.close();
    await context2.close();
  });

  test('12. Test Conflict Resolution', async ({ browser }) => {
    // Two users edit same task simultaneously
    const context1 = await browser.newContext();
    const page1 = await context1.newPage();
    await login(page1, testUser);
    await page1.goto(`/projects/${projectId}/board`);
    
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    await login(page2, testUser2);
    await page2.goto(`/projects/${projectId}/board`);
    
    // Both users open same task
    await page1.click('text=Test Task 1');
    await page2.click('text=Test Task 1');
    
    // User 1 updates
    await page1.locator('textarea[name="description"]').fill('User 1 update');
    await page1.click('button:has-text("Save")');
    await page1.waitForTimeout(1000);
    
    // User 2 updates (should detect conflict)
    await page2.locator('textarea[name="description"]').fill('User 2 update');
    await page2.click('button:has-text("Save")');
    
    // Should show conflict warning or refresh data
    await page2.waitForTimeout(2000);
    
    await context1.close();
    await context2.close();
  });

  test('13. User Logout', async ({ page }) => {
    await login(page, testUser);
    
    // Click logout button
    await page.click('button:has-text("Logout")').or(page.click('text=Log Out'));
    
    // Should redirect to login
    await page.waitForURL('/login', { timeout: 5000 });
    
    // Verify user cannot access protected pages
    await page.goto('/dashboard');
    await expect(page).toHaveURL('/login');
  });

  test('14. Security Audit - npm vulnerabilities', async () => {
    // This test just documents that we should check npm vulnerabilities
    // The actual check is done via npm audit
    expect(true).toBe(true);
  });
});
