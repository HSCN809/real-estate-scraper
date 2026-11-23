import { expect, test } from '@playwright/test';

test('filtered charts reuse filter options and refresh without the unfiltered overview', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const overview = { cities: [], platforms: {}, categories: {}, listing_types: {}, history: [] };
  const facetRequests: URL[] = [];

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());
    const headers = {
      'access-control-allow-origin': new URL(page.url()).origin,
      'access-control-allow-credentials': 'true',
    };
    switch (url.pathname) {
      case '/api/v1/auth/me':
        await route.fulfill({ headers, json: { id: 1, username: 'fixture', email: 'fixture@example.com', is_active: true, is_admin: false } });
        break;
      case '/api/v1/tasks/active':
        await route.fulfill({ headers, json: { active_tasks: [], count: 0 } });
        break;
      case '/api/v1/results/filters':
        facetRequests.push(url);
        await route.fulfill({
          headers,
          json: {
            platforms: ['Emlakjet'], categories: [], listing_types: [], subtypes: [],
            locations: {}, total_groups: 0, total_listings: 0, last_scrape: 'Test tarama tarihi',
            ...(url.searchParams.has('include_overview') ? { overview } : {}),
          },
        });
        break;
      case '/api/v1/results/overview':
        await route.fulfill({ headers, json: overview });
        break;
      default:
        await route.abort();
    }
  });

  await page.goto('/results?view=charts');
  await expect(page.getByText('Test tarama tarihi')).toBeVisible();
  expect(facetRequests.map(url => url.search)).toEqual(['?include_overview=true']);

  await page.getByLabel('Platform', { exact: true }).click();
  const filteredOverview = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.pathname === '/api/v1/results/overview' && url.searchParams.get('platform') === 'Emlakjet';
  });
  await page.getByRole('button', { name: 'Emlakjet', exact: true }).click();
  expect((await filteredOverview).ok()).toBe(true);
  expect(facetRequests).toHaveLength(1);

  const refreshedFacets = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/results/filters');
  await page.getByRole('button', { name: 'Verileri yenile', exact: true }).click();
  expect(new URL((await refreshedFacets).url()).search).toBe('');
});
