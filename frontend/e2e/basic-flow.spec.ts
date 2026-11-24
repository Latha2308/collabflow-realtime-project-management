import { test, expect } from '@playwright/test';

const timestamp = Date.now();
const testUser = {
  email: `test${timestamp}@example.com`,
  username: `testuser${timestamp}`,
  fullName: 'Test User',
  password: 'TestPass123!',
};

test.describe('CollabFlow Basic Flow', () => {
  test('1. Can access homepage', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });

  test('2. Can navigate to register page', async ({ page }) => {
    await page.goto('/login');
    await page.click('text=Sign up');
    await expect(page).toHaveURL(/\/register/);
  });

  test('3. Can register a new user', async ({ page }) => {
    await page.goto('/register');
    
    await page.fill('input[name="email"]', testUser.email);
    await page.fill('input[name="username"]', testUser.username);
    await page.fill('input[name="full_name"]', testUser.fullName);
    await page.fill('input[name="password"]', testUser.password);
    await page.fill('input[name="confirmPassword"]', testUser.password);
    
    await page.click('button[type="submit"]');
    
    // Should redirect to login after successful registration
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('4. Can login with registered user', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[name="username"]', testUser.username);
    await page.fill('input[name="password"]', testUser.password);
    
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard after successful login
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    
    // Check for user name displayed
    await expect(page.locator(`text=${testUser.fullName}`)).toBeVisible({ timeout: 5000 });
  });

  test('5. Dashboard shows create workspace option', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="username"]', testUser.username);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    
    // Check for workspace creation option
    const createButton = page.locator('text=Create Workspace').or(page.locator('text=New Workspace')).or(page.locator('button:has-text("Create")'));
    await expect(createButton.first()).toBeVisible({ timeout: 5000 });
  });
});
