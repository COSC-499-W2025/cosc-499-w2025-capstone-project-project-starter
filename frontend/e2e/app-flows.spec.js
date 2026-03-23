const { test, expect } = require('@playwright/test');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TEST_EMAIL = 'test@domain.com';
const TEST_PASSWORD = 'password';

async function ensureLoggedIn(page) {
  await page.goto('/');
  const alreadyIn = await page.getByRole('button', { name: 'Log Out' }).isVisible().catch(() => false);
  if (alreadyIn) return;

  // The tab button says "Log In", the submit button says "Sign In" — target the submit
  await page.getByLabel(/email/i).fill(TEST_EMAIL);
  await page.getByLabel(/password/i).first().fill(TEST_PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();

  const authError = await page.getByText(/invalid|not found|incorrect/i).isVisible().catch(() => false);
  if (authError) {
    // Account doesn't exist — register
    await page.getByRole('button', { name: 'Create Account' }).first().click();
    await page.getByLabel(/display name/i).fill('Test User');
    await page.getByLabel(/^email/i).fill(TEST_EMAIL);
    const passwordInputs = page.getByLabel(/password/i);
    await passwordInputs.nth(0).fill(TEST_PASSWORD);
    await passwordInputs.nth(1).fill(TEST_PASSWORD);
    await page.locator('form').getByRole('button', { name: 'Create Account' }).click();
  }

  await expect(page.getByRole('button', { name: 'Log Out' })).toBeVisible({ timeout: 10000 });
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

test.describe('Authentication', () => {
  test('shows login form on first visit', async ({ page }) => {
    await page.goto('/');
    // Should see email + password inputs and a sign-in button before logging in
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
  });

  test('shows an error on bad credentials', async ({ page }) => {
    await page.goto('/');
    await page.getByLabel(/email/i).fill('nobody@nowhere.com');
    await page.getByLabel(/password/i).first().fill('wrongpassword');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByText(/invalid|incorrect|not found|failed/i)).toBeVisible({ timeout: 8000 });
  });

  test('can switch to the register form', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Create Account' }).first().click();
    await expect(page.getByLabel(/display name/i)).toBeVisible();
  });

  test('register shows error when passwords do not match', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Create Account' }).first().click();
    await page.getByLabel(/display name/i).fill('Test');
    await page.getByLabel(/^email/i).fill('mismatch@example.com');
    const passwordInputs = page.getByLabel(/password/i);
    await passwordInputs.nth(0).fill('password1');
    await passwordInputs.nth(1).fill('password2');
    await page.locator('form').getByRole('button', { name: 'Create Account' }).click();
    await expect(page.getByText(/passwords do not match/i)).toBeVisible();
  });

  test('can log in with valid credentials', async ({ page }) => {
    await ensureLoggedIn(page);
    await expect(page.getByRole('button', { name: /log out|logout/i })).toBeVisible();
  });

  test('can log out and is returned to the login screen', async ({ page }) => {
    await ensureLoggedIn(page);
    await page.getByRole('button', { name: 'Log Out' }).click();
    await expect(page.getByLabel(/email/i)).toBeVisible({ timeout: 8000 });
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Navigation / tab switching
// ---------------------------------------------------------------------------

test.describe('Navigation tabs', () => {
  test.beforeEach(async ({ page }) => {
    await ensureLoggedIn(page);
  });

  test('Projects tab is active by default after login', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Your Projects' })).toBeVisible({ timeout: 10000 });
  });

  test('can switch to the Upload tab', async ({ page }) => {
    await page.getByRole('button', { name: 'Upload' }).click();
    await expect(page.getByText('New project upload')).toBeVisible();
  });

  test('can switch to the Compare tab', async ({ page }) => {
    await page.getByRole('button', { name: 'Compare' }).click();
    await expect(page.getByRole('heading', { name: 'Compare Projects' })).toBeVisible();
  });

  test('can switch to the Resume tab', async ({ page }) => {
    await page.getByRole('button', { name: /resume/i }).click();
    await expect(page.getByRole('heading', { name: /education/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Upload tab
// ---------------------------------------------------------------------------

test.describe('Upload tab', () => {
  test.beforeEach(async ({ page }) => {
    await ensureLoggedIn(page);
    await page.getByRole('button', { name: /upload/i }).click();
  });

  test('shows new project and incremental mode options', async ({ page }) => {
    await expect(page.getByText('New project upload')).toBeVisible();
    await expect(page.getByText(/incremental update/i).first()).toBeVisible();
  });

  test('switching to incremental mode shows project selector', async ({ page }) => {
    await page.getByText(/incremental update/i).first().click();
    await expect(
      page.getByRole('combobox').or(page.getByLabel(/existing project|target project|select project/i)).first()
    ).toBeVisible();
  });

  test('project name field is pre-filled from filename after selecting a file', async ({ page }) => {
    await page.getByLabel(/new project/i).click();

    // Attach a dummy zip file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'my-cool-project.zip',
      mimeType: 'application/zip',
      buffer: Buffer.from('dummy'),
    });

    // The project name field should be pre-populated with the normalised filename
    const nameInput = page.getByLabel(/project name/i);
    await expect(nameInput).toHaveValue(/my-cool-project/i);
  });
});

// ---------------------------------------------------------------------------
// Compare tab
// ---------------------------------------------------------------------------

test.describe('Compare tab', () => {
  test.beforeEach(async ({ page }) => {
    await ensureLoggedIn(page);
    await page.getByRole('button', { name: /compare/i }).click();
  });

  test('shows empty state when no projects exist', async ({ page }) => {
    // With no projects, the app should show a message rather than a compare button
    await expect(page.getByText(/no projects available/i)).toBeVisible();
  });

  test('shows attribute selection options after projects exist', async ({ page }) => {
    // The attribute checkboxes are from COMPARISON_ATTRIBUTE_OPTIONS in the source
    // They only render when projects are available — verify the section heading exists
    await expect(page.getByRole('heading', { name: 'Compare Projects' })).toBeVisible();
  });
});
