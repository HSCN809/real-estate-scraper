import { afterEach, describe, expect, it, vi } from 'vitest';
import { extractErrorMessage, login } from './auth-api';

describe('extractErrorMessage', () => {
  it('returns string detail', () => {
    expect(extractErrorMessage({ detail: 'Giriş başarısız' }, 'fallback')).toBe(
      'Giriş başarısız',
    );
  });

  it('returns first 422 message from detail array', () => {
    expect(
      extractErrorMessage(
        { detail: [{ msg: 'value is not a valid email' }] },
        'fallback',
      ),
    ).toBe('value is not a valid email');
  });

  it('falls back for empty or unknown payloads', () => {
    expect(extractErrorMessage(null, 'Giriş başarısız')).toBe('Giriş başarısız');
    expect(extractErrorMessage({}, 'Giriş başarısız')).toBe('Giriş başarısız');
  });
});

describe('login', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('posts credentials and returns the user', async () => {
    const user = {
      id: 1,
      username: 'ali',
      email: 'ali@example.com',
      is_active: true,
      is_admin: false,
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => user,
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      login({ username: 'ali', password: 'Secret1' }),
    ).resolves.toEqual(user);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/auth/login',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      }),
    );
  });

  it('throws the API detail when login fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Hatalı şifre' }),
      }),
    );

    await expect(login({ username: 'ali', password: 'wrong' })).rejects.toMatchObject({
      message: 'Hatalı şifre',
      status: 401,
    });
  });
});
