# E2E Testing

This project uses [Playwright](https://playwright.dev/) for end-to-end tests. Tests live in `frontend/e2e/`.

## Setup

From the `frontend/` directory:
```bash
npm install
npx playwright install
```

## Running tests
```bash
# Run all tests headlessly (fast, good for CI)
npm run test:e2e

# Run with a visible browser window
npx playwright test --headed

# Run with the interactive UI (great for debugging individual tests)
npm run test:e2e:ui

# View the HTML report from the last run
npx playwright show-report
```

## Test accounts

The tests automatically create a `test@domain.com` account with password `password` on first run. If the account already exists (e.g. on subsequent runs), the tests will log in with those credentials instead. No setup required.

## Test coverage

| File | What it tests |
|---|---|
| `e2e/resume-date-validation.spec.js` | Date validation on the Resume tab for Education and Awards entries |

### Resume date validation (`resume-date-validation.spec.js`)

Tests the client-side validation rules added to the Resume tab:

**Education – Start Year**
- Error shown when year is before 1900
- Error shown when year is in the future
- Error clears when a valid year is entered

**Education – End Year**
- Error shown when end year is before start year
- Error shown when end year is more than 10 years in the future
- Error clears when end year is corrected
- End year input is disabled when "Currently enrolled" is checked

**Awards – Year**
- Error shown when year is before 1900
- Error shown when year is after the current year
- Error clears when a valid year is entered

In all invalid cases the Save button is also verified to be disabled.

## CI

A GitHub Actions workflow lives at `.github/workflows/playwright.yml` and runs all tests automatically on every push and pull request. The backend must be reachable for tests to pass in CI — make sure your CI environment has the backend running before the test step.