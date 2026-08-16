import { expect, test } from '@playwright/test';

test('login page renders and rejects invalid credentials', async ({ page }) => {
  await page.goto('/login', { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await expect(page.getByText('Hoş Geldiniz')).toBeVisible({ timeout: 30_000 });
  await page.getByPlaceholder('kullanıcı_adı').fill('olmayan_kullanici');
  await page.getByPlaceholder('********').fill('Yanlis1A');
  await page.getByRole('button', { name: 'Giriş Yap' }).click();
  await expect(page.getByText(/başarısız|alınamadı|Hatalı|Giriş/i).first()).toBeVisible({
    timeout: 15_000,
  });
});
