import { expect, test } from '@playwright/test';

const username = 'silinecek_mvfgk826';
const password = 'Silinecek1a';

test('disposable user can open the app and queue one HepsiEmlak page', async ({ page }) => {
  test.setTimeout(300_000);

  await page.goto('/login');
  await page.getByRole('textbox', { name: 'Kullanıcı Adı veya E-posta' }).fill(username);
  await page.getByRole('textbox', { name: 'Şifre', exact: true }).fill(password);
  await page.getByRole('button', { name: 'Giriş Yap' }).click();
  await expect(page.getByText(username).first()).toBeVisible({ timeout: 20_000 });

  await page.goto('/scraper/hepsiemlak');
  await expect(page.getByRole('heading', { name: 'HepsiEmlak' })).toBeVisible();
  await page.getByRole('spinbutton', { name: 'Maksimum Sayfa' }).fill('1');
  await page.getByRole('button', { name: 'Haritadan Şehir Seç' }).click();
  const bayburt = page.locator('#bayburt path');
  await expect(bayburt).toBeVisible({ timeout: 15_000 });
  await bayburt.click();
  await page.getByRole('button', { name: 'Seçimi Onayla' }).click();
  await expect(page.getByRole('main').getByText('Bayburt')).toBeVisible();

  const started = page.waitForResponse(
    (response) =>
      response.url().includes('/scrape/hepsiemlak') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Taramayı Başlat' }).click();
  const response = await started;
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.status).toBe('queued');
  expect(body.task_id).toBeTruthy();

  const deadline = Date.now() + 240_000;
  let last = body;
  while (Date.now() < deadline) {
    const status = await page.request.get(`http://localhost:8000/api/v1/tasks/${body.task_id}`);
    expect(status.ok()).toBeTruthy();
    last = await status.json();
    if (['completed', 'failed', 'cancelled'].includes(last.status)) break;
    await page.waitForTimeout(5_000);
  }

  console.log(`USER ${username}`);
  console.log(`TASK ${last.task_id} ${last.status} ${last.message}`);
  expect(['completed', 'failed', 'queued', 'running']).toContain(last.status);
});
