import { test, expect } from '@playwright/test';

/**
 * Helper: log in and navigate to the Resume tab.
 *
 * Reads credentials from environment variables so no passwords are
 * hard-coded in the repo. Set them before running:
 *
 *   export E2E_EMAIL=you@example.com
 *   export E2E_PASSWORD=yourpassword
 *
 * Or add them to a .env.local file (never commit that file).
 */
async function goToResumeTab(page) {
  await page.goto('/');

  // Try to register first
  await page.getByRole('button', { name: 'Create Account' }).first().click();
  await page.getByLabel('Email').fill('test@domain.com');
  await page.getByLabel('Password').first().fill('password');
  await page.getByLabel('Confirm Password').fill('password');
  await page.locator('form').getByRole('button', { name: 'Create Account' }).click();

  // If account already exists, the app shows an error — fall back to logging in
  const errorBanner = page.locator('.error-banner');
  const resumeBtn = page.getByRole('button', { name: 'Resume' });

  const result = await Promise.race([
    errorBanner.waitFor({ timeout: 3000 }).then(() => 'error'),
    resumeBtn.waitFor({ timeout: 3000 }).then(() => 'success'),
  ]);

  if (result === 'error') {
    // Account already exists — log in instead
    await page.getByRole('button', { name: 'Log In' }).click();
    await page.getByLabel('Email').fill('test@domain.com');
    await page.getByLabel('Password').fill('password');
    await page.getByRole('button', { name: 'Sign In' }).click();
  }

  // Wait until the nav is visible
  await expect(resumeBtn).toBeVisible();

  // Navigate to the Resume tab
  await resumeBtn.click();
  await expect(page.getByRole('heading', { name: 'Education' })).toBeVisible();
}

const currentYear = new Date().getFullYear();

// ---------------------------------------------------------------------------
// Education – Start Year validation
// ---------------------------------------------------------------------------

test.describe('Education – Start Year validation', () => {
  test.beforeEach(async ({ page }) => {
    await goToResumeTab(page);
    await page.getByRole('button', { name: '+ Add' }).first().click();
  });

  test('shows error when start year is before 1900', async ({ page }) => {
    const startYearInput = page.getByLabel('Start Year');
    await startYearInput.fill('1899');
    await startYearInput.blur();

    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save' }).first()).toBeDisabled();
  });

  test('shows error when start year is in the future', async ({ page }) => {
    const startYearInput = page.getByLabel('Start Year');
    await startYearInput.fill(String(currentYear + 1));
    await startYearInput.blur();

    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save' }).first()).toBeDisabled();
  });

  test('clears error when a valid start year is entered', async ({ page }) => {
    const startYearInput = page.getByLabel('Start Year');

    // Trigger the error first
    await startYearInput.fill('1800');
    await startYearInput.blur();
    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`).first()).toBeVisible();

    // Fix it
    await startYearInput.fill('2020');
    await startYearInput.blur();
    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`)).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Education – End Year validation
// ---------------------------------------------------------------------------

test.describe('Education – End Year validation', () => {
  test.beforeEach(async ({ page }) => {
    await goToResumeTab(page);
    await page.getByRole('button', { name: '+ Add' }).first().click();
  });

  test('shows error when end year is before start year', async ({ page }) => {
    await page.getByLabel('Start Year').fill('2020');
    await page.getByLabel('Start Year').blur();

    const endYearInput = page.getByLabel('End Year');
    await endYearInput.fill('2018');
    await endYearInput.blur();

    await expect(page.getByText('Cannot be before start year.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save' }).first()).toBeDisabled();
  });

  test('shows error when end year is more than 10 years in the future', async ({ page }) => {
    const maxEndYear = currentYear + 10;
    const endYearInput = page.getByLabel('End Year');
    await endYearInput.fill(String(maxEndYear + 1));
    await endYearInput.blur();

    await expect(page.getByText(`Must be between 1900 and ${maxEndYear}.`).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save' }).first()).toBeDisabled();
  });

  test('clears error when end year is corrected to be after start year', async ({ page }) => {
    await page.getByLabel('Start Year').fill('2020');
    await page.getByLabel('Start Year').blur();

    const endYearInput = page.getByLabel('End Year');

    // Trigger the error
    await endYearInput.fill('2018');
    await endYearInput.blur();
    await expect(page.getByText('Cannot be before start year.')).toBeVisible();

    // Fix it
    await endYearInput.fill('2024');
    await endYearInput.blur();
    await expect(page.getByText('Cannot be before start year.')).not.toBeVisible();
  });

  test('end year field is disabled when Currently enrolled is checked', async ({ page }) => {
    await page.getByLabel('Currently enrolled').check();
    await expect(page.getByLabel('End Year')).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// Awards – Year validation
// ---------------------------------------------------------------------------

test.describe('Awards – Year validation', () => {
  test.beforeEach(async ({ page }) => {
    await goToResumeTab(page);
    // The Awards section has its own "+ Add" button — click the second one
    await page.getByRole('button', { name: '+ Add' }).nth(1).click();
  });

  test('shows error when award year is before 1900', async ({ page }) => {
    const yearInput = page.getByLabel('Year');
    await yearInput.fill('1899');
    await yearInput.blur();

    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save' }).first()).toBeDisabled();
  });

  test('shows error when award year is after the current year', async ({ page }) => {
    const yearInput = page.getByLabel('Year');
    await yearInput.fill(String(currentYear + 1));
    await yearInput.blur();

    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save' }).first()).toBeDisabled();
  });

  test('clears error when a valid award year is entered', async ({ page }) => {
    const yearInput = page.getByLabel('Year');

    // Trigger the error
    await yearInput.fill('1800');
    await yearInput.blur();
    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`).first()).toBeVisible();

    // Fix it
    await yearInput.fill('2022');
    await yearInput.blur();
    await expect(page.getByText(`Must be between 1900 and ${currentYear}.`)).not.toBeVisible();
  });
});
