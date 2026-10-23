import { test, expect } from '@playwright/test';

// This suite creates/cancels synthetic appointments. Run ONLY against an isolated test stack.
test('receptionist checks availability, books, sees history and cancels', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email', {exact: true}).fill('admin@harbordentaldemo.local');
  await page.getByLabel('Password', {exact: true}).fill(process.env.E2E_PASSWORD ?? 'Phase1Synthetic123!');
  await page.getByRole('button', {name: 'Login', exact: true}).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.getByRole('button', {name: 'Appointments', exact: true}).click();
  await expect(page.getByText('Schedule visit', {exact: true})).toBeVisible();
  const selects = page.locator('select');
  await selects.nth(0).selectOption({index: 1});
  await page.getByLabel('Appointment date', {exact: true}).fill('2026-11-10');
  await page.getByRole('button', {name: 'Check availability', exact: true}).click();
  await expect(page.getByText('Select an available time.', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: '08:00 AM (-05:00)', exact: true}).click();
  const committedBooking = page.waitForResponse((response) => response.url().endsWith('/api/v1/appointments') && response.request().method() === 'POST');
  await page.getByRole('button', {name: 'Book appointment', exact: true}).click();
  const appointmentId = (await (await committedBooking).json()).appointment_id;
  await expect(page.getByText('Appointment scheduled successfully.', {exact: true})).toBeVisible();
  const row = page.getByTestId(`appointment-${appointmentId}`);
  await row.getByRole('button', {name: 'History', exact: true}).click();
  await expect(page.getByText(/appointment.create/)).toBeVisible();
  await row.getByRole('button', {name: 'Reschedule', exact: true}).click();
  await page.getByLabel('Appointment date', {exact: true}).fill('2026-11-11');
  await page.getByRole('button', {name: 'Check availability', exact: true}).click();
  await expect(page.getByText('Select an available time.', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: '08:00 AM (-05:00)', exact: true}).click();
  await page.getByRole('button', {name: 'Save reschedule', exact: true}).click();
  await expect(page.getByText('Appointment rescheduled successfully.', {exact: true})).toBeVisible();
  await row.getByRole('button', {name: 'Cancel', exact: true}).click();
  await expect(page.getByText('Appointment cancelled and removed from the active schedule.', {exact: true})).toBeVisible();
  await page.screenshot({path: 'test-results/phase1-appointments.png', fullPage: true});
  await page.getByRole('button', {name: 'Calls', exact: true}).click();
  await expect(page.getByText('Call center log', {exact: true})).toBeVisible();
  await expect(page.getByText(/AI bookings:/)).toBeVisible();
});

test('dashboard without a token redirects to login', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/login/);
});
