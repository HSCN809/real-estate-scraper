import { describe, expect, it } from 'vitest';
import { CATEGORIES, TURKISH_CITIES } from './index';

describe('static catalog data', () => {
  it('lists unique Turkish provinces including İstanbul', () => {
    expect(TURKISH_CITIES).toHaveLength(81);
    expect(TURKISH_CITIES).toContain('İstanbul');
    expect(TURKISH_CITIES).toContain('Ardahan');
    expect(new Set(TURKISH_CITIES).size).toBe(81);
  });

  it('exposes both platforms and listing types', () => {
    expect(Object.keys(CATEGORIES).sort()).toEqual(['emlakjet', 'hepsiemlak']);
    expect(Object.keys(CATEGORIES.emlakjet).sort()).toEqual(['kiralik', 'satilik']);
  });
});
