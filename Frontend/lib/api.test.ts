import { afterEach, describe, expect, it, vi } from 'vitest';
import { exportToExcel, getListings, healthCheck, startScrape } from './api';

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('healthCheck returns true when the response is ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    await expect(healthCheck()).resolves.toBe(true);
  });

  it('healthCheck returns false when fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    await expect(healthCheck()).resolves.toBe(false);
  });

  it('startScrape posts to the platform endpoint', async () => {
    const payload = { task_id: 't-1', status: 'queued', message: 'ok' };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      startScrape('hepsiemlak', { category: 'konut', listing_type: 'satilik' }),
    ).resolves.toEqual(payload);
    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8000/api/v1/scrape/hepsiemlak',
    );
  });

  it('getListings serializes query params', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total: 0, page: 1, limit: 10, pages: 0, items: [] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await getListings({ platform: 'emlakjet', city: 'İstanbul', page: 2 });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain('/listings?');
    expect(url).toContain('platform=emlakjet');
    expect(url).toContain('page=2');
  });

  it('exportToExcel skips all-valued filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['xlsx']),
    });
    vi.stubGlobal('fetch', fetchMock);

    await exportToExcel({ platform: 'all', kategori: 'konut', city: 'Ankara' });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).not.toContain('platform=');
    expect(url).toContain('kategori=konut');
    expect(url).toContain('city=Ankara');
  });
});
