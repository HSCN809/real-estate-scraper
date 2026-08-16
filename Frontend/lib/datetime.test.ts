import { describe, expect, it } from 'vitest';
import {
  formatAppDateTime,
  formatIstanbulDateTime,
  formatTimeAgo,
  parseAppDate,
} from './datetime';

describe('parseAppDate', () => {
  it('treats naive ISO timestamps as UTC', () => {
    const date = parseAppDate('2026-08-16T13:00:00');
    expect(date?.toISOString()).toBe('2026-08-16T13:00:00.000Z');
  });

  it('parses Turkish display times as Istanbul', () => {
    const date = parseAppDate('16.08.2026 16:00');
    expect(date?.toISOString()).toBe('2026-08-16T13:00:00.000Z');
  });
});

describe('formatIstanbulDateTime', () => {
  it('converts UTC instants to Turkey time', () => {
    const date = new Date('2026-08-16T13:00:00.000Z');
    expect(formatIstanbulDateTime(date)).toBe('16.08.2026 16:00');
    expect(formatAppDateTime('2026-08-16T13:00:00')).toBe('16.08.2026 16:00');
  });
});

describe('formatTimeAgo', () => {
  it('uses the parsed instant for relative time', () => {
    const now = new Date('2026-08-16T14:00:00.000Z');
    expect(formatTimeAgo('2026-08-16T13:00:00', now)).toBe('1 saat önce');
  });
});
