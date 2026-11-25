/**
 * Screenshot Capture Script for CollabFlow
 * 
 * Captures professional application screenshots for README documentation.
 * Creates realistic sample data and navigates through key features.
 * 
 * Note: This is a development script, not production code.
 * ESLint warnings suppressed for script-specific patterns.
 */

/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */

import { chromium, Browser, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const BASE_URL = process.env.API_BASE_URL || 'http://backend:8000';
const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://frontend:5173';
const SCREENSHOTS_DIR = path.join(__dirname, '../../docs/screenshots');

// Demo user credentials (timestamp-based to avoid conflicts)
const timestamp = Date.now();
const demoUser = {
  email: `demo${timestamp}@collabflow.example`,
  username: `demo_user_${timestamp}`,
  fullName: 'Demo User',
  password: 'DemoPass123!',
};

// Sample data
const sampleWorkspace = {
  name: 'Product Development Team',
  description: 'Cross-functional team building the next generation platform',
};

const sampleProject = {
  name: 'Mobile App Redesign Q1 2024',
  description: 'Complete redesign of mobile application with focus on UX improvements and performance optimization',
  status: 'in_progress',
};

const sampleTasks = [
  {
    title: 'Design user authentication flow',
    description: 'Create wireframes and high-fidelity mockups for the new authentication experience',
    status: 'in_progress',
    priority: 'high',
    estimated_hours: 16,
  },
  {
    title: 'Implement dark mode toggle',
    description: 'Add system-wide dark mode support with user preference persistence',
    status: 'todo',
    priority: 'medium',
    estimated_hours: 12,
  },
  {
    title: 'Set up CI/CD pipeline',
    description: 'Configure automated testing and deployment workflow with GitHub Actions',
    status: 'done',
    priority: 'high',
    estimated_hours: 20,
  },
  {
    title: 'Review accessibility standards',
    description: 'Audit current implementation against WCAG 2.1 AA guidelines',
    status: 'in_review',
    priority: 'medium',
    estimated_hours: 8,
  },
  {
    title: 'Conduct user testing sessions',
    description: 'Schedule and run usability tests with 10-15 target users',
    status: 'backlog',
    priority: 'low',
    estimated_hours: 24,
  },
  {
    title: 'Optimize image loading performance',
    description: 'Implement lazy loading and WebP format for faster page loads',
    status: 'in_progress',
    priority: 'urgent',
    estimated_hours: 10,
  },
  {
    title: 'Write API documentation',
    description: 'Complete OpenAPI specification and usage examples',
    status: 'in_review',
    priority: 'medium',
    estimated_hours: 16,
  },
  {
    title: 'Refactor state management',
    description: 'Migrate from Redux to Zustand for simpler state handling',
    status: 'done',
    priority: 'high',
    estimated_hours: 32,
  },
  {
    title: 'Add push notifications',
    description: 'Implement real-time push notifications for task updates',
    status: 'todo',
    priority: 'medium',
    estimated_hours: 20,
  },
  {
    title: 'Database query optimization',
    description: 'Add indexes and optimize N+1 query issues',
    status: 'done',
    priority: 'high',
    estimated_hours: 14,
  },
  {
    title: 'Create onboarding tutorial',
    description: 'Build interactive first-time user experience walkthrough',
    status: 'backlog',
    priority: 'low',
    estimated_hours: 18,
  },
  {
    title: 'Security audit and penetration testing',
    description: 'Engage third-party security firm for comprehensive assessment',
    status: 'todo',
    priority: 'urgent',
    estimated_hours: 40,
  },
];

async function makeApiCall(endpoint: string, method: string, body?: any, cookie?: string) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (cookie) {
    headers['Cookie'] = cookie;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API call failed: ${response.status} ${text}`);
  }

  return response.json();
}

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function setupSampleData(): Promise<{ workspaceId: string; projectId: string; cookie: string }> {
  console.log('Creating demo user...');
  
  // Register user
  await makeApiCall('/api/v1/auth/register', 'POST', {
    email: demoUser.email,
    username: demoUser.username,
    full_name: demoUser.fullName,
    password: demoUser.password,
  });

  console.log('Logging in...');
  
  // Login and get cookie
  const loginResponse = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: demoUser.username,
      password: demoUser.password,
    }),
  });

  const setCookieHeader = loginResponse.headers.get('set-cookie');
  if (!setCookieHeader) {
    throw new Error('No auth cookie received');
  }

  const cookie = setCookieHeader.split(';')[0];
  console.log('Authenticated successfully');

  // Create workspace
  console.log('Creating workspace...');
  const workspace = await makeApiCall('/api/v1/workspaces', 'POST', sampleWorkspace, cookie);
  const workspaceId = workspace.id;

  // Create project
  console.log('Creating project...');
  const project = await makeApiCall('/api/v1/projects', 'POST', {
    ...sampleProject,
    workspace_id: workspaceId,
  }, cookie);
  const projectId = project.id;

  // Create tasks
  console.log('Creating sample tasks...');
  const createdTasks = [];
  for (const task of sampleTasks) {
    const created = await makeApiCall('/api/v1/tasks', 'POST', {
      ...task,
      project_id: projectId,
    }, cookie);
    createdTasks.push(created);
    await sleep(100); // Small delay to avoid overwhelming the backend
  }

  // Add some task dependencies to demonstrate graph algorithms
  console.log('Creating task dependencies...');
  const authTask = createdTasks.find(t => t.title.includes('authentication'));
  const cicdTask = createdTasks.find(t => t.title.includes('CI/CD'));
  const securityTask = createdTasks.find(t => t.title.includes('Security audit'));

  if (authTask && cicdTask) {
    // CI/CD depends on auth being designed
    await makeApiCall(`/api/v1/tasks/dependencies`, 'POST', {
      task_id: cicdTask.id,
      depends_on_id: authTask.id,
    }, cookie);
  }

  if (securityTask && authTask) {
    // Security audit depends on auth implementation
    await makeApiCall(`/api/v1/tasks/dependencies`, 'POST', {
      task_id: securityTask.id,
      depends_on_id: authTask.id,
    }, cookie);
  }

  console.log('Sample data created successfully!');

  return { workspaceId, projectId, cookie };
}

async function captureScreenshots(browser: Browser, projectId: string) {
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });

  const page = await context.newPage();

  // Ensure screenshots directory exists
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  }

  try {
    // 1. Login Page
    console.log('Capturing login page...');
    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForLoadState('networkidle');
    await sleep(1000); // Extra time for fonts and styling
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '01-login.png'),
      fullPage: false,
    });
    console.log('✓ Login page captured');

    // Login to access protected pages
    await page.fill('input[type="text"]', demoUser.username);
    await page.fill('input[type="password"]', demoUser.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/$/, { timeout: 10000 });
    await sleep(2000);

    // 2. Kanban Board
    console.log('Capturing Kanban board...');
    await page.goto(`${FRONTEND_URL}/projects/${projectId}/board`);
    await page.waitForLoadState('networkidle');
    
    // Wait for tasks to load
    await page.waitForSelector('[data-testid="task-card"], .task-card, text="Design user authentication"', { 
      timeout: 15000 
    }).catch(() => {
      console.log('Waiting for tasks to appear...');
    });
    
    await sleep(3000); // Extra time for all cards to render
    
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '02-board-overview.png'),
      fullPage: true, // Capture full board
    });
    console.log('✓ Board overview captured');

    // 3. Task Details Drawer
    console.log('Capturing task details...');
    
    // Click on the first visible task card to open drawer
    const taskCard = page.locator('text="Design user authentication flow"').or(
      page.locator('text="Review accessibility standards"')
    ).first();
    
    await taskCard.click();
    await sleep(2000); // Wait for drawer animation and data load
    
    // Wait for drawer to be visible
    await page.waitForSelector('[role="dialog"], .drawer, .modal', { timeout: 5000 }).catch(() => {
      console.log('Drawer might have different selector, proceeding...');
    });
    
    await sleep(1000);
    
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '03-task-details.png'),
      fullPage: false,
    });
    console.log('✓ Task details captured');

    // Close drawer
    await page.keyboard.press('Escape');
    await sleep(500);

    // 4. Analytics Dashboard
    console.log('Capturing analytics dashboard...');
    await page.goto(`${FRONTEND_URL}/projects/${projectId}/analytics`);
    await page.waitForLoadState('networkidle');
    
    // Wait for charts to render
    await sleep(4000); // Charts need extra time to animate and render
    
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '04-analytics.png'),
      fullPage: true, // Capture all charts
    });
    console.log('✓ Analytics dashboard captured');

  } catch (error) {
    console.error('Error during screenshot capture:', error);
    throw error;
  } finally {
    await context.close();
  }
}

async function main() {
  console.log('=== CollabFlow Screenshot Capture ===\n');
  
  let browser: Browser | null = null;
  
  try {
    // Setup sample data
    const { projectId } = await setupSampleData();
    
    console.log('\nLaunching browser...');
    browser = await chromium.launch({
      headless: true,
    });

    // Capture screenshots
    console.log('\nCapturing screenshots...');
    await captureScreenshots(browser, projectId);

    console.log('\n=== Screenshot capture completed successfully! ===');
    console.log(`\nScreenshots saved to: ${SCREENSHOTS_DIR}`);
    console.log('\nFiles created:');
    console.log('  - 01-login.png');
    console.log('  - 02-board-overview.png');
    console.log('  - 03-task-details.png');
    console.log('  - 04-analytics.png');
    
  } catch (error) {
    console.error('\n❌ Screenshot capture failed:', error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

main();
