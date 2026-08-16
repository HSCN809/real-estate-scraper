export const TR_TIMEZONE = 'Europe/Istanbul';

function pad(value: string | number): string {
  return String(value).padStart(2, '0');
}

function istanbulParts(date: Date) {
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: TR_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    weekday: 'short',
    hourCycle: 'h23',
  });
  return Object.fromEntries(
    fmt.formatToParts(date)
      .filter((part) => part.type !== 'literal')
      .map((part) => [part.type, part.value])
  ) as Record<string, string>;
}

export function parseAppDate(dateStr?: string | null): Date | null {
  if (!dateStr) return null;

  const raw = String(dateStr).trim();
  if (!raw) return null;

  const trDateMatch = raw.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?$/);
  if (trDateMatch) {
    const [, day, month, year, hour = '0', minute = '0'] = trDateMatch;
    const parsed = new Date(
      `${year}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}:00+03:00`
    );
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  const hasTimezone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw);
  const isNaiveIso = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(raw);
  const parsed = new Date(hasTimezone || !isNaiveIso ? raw : `${raw}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatIstanbulDateTime(date: Date): string {
  const parts = istanbulParts(date);
  return `${parts.day}.${parts.month}.${parts.year} ${parts.hour}:${parts.minute}`;
}

export function formatIstanbulTime(date: Date): string {
  const parts = istanbulParts(date);
  return `${parts.hour}:${parts.minute}:${parts.second}`;
}

export function formatIstanbulDate(date: Date): string {
  const parts = istanbulParts(date);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function formatAppDateTime(dateStr?: string | null): string {
  const date = parseAppDate(dateStr);
  return date ? formatIstanbulDateTime(date) : '-';
}

export function getIstanbulHour(date = new Date()): number {
  return Number(istanbulParts(date).hour);
}

export function istanbulDayStart(date: Date): Date {
  const parts = istanbulParts(date);
  return new Date(`${parts.year}-${parts.month}-${parts.day}T00:00:00+03:00`);
}

export function formatTimeAgo(dateStr?: string | null, now = new Date()): string {
  const date = parseAppDate(dateStr);
  if (!date) return '-';

  const diffMs = now.getTime() - date.getTime();
  if (diffMs < 0) return 'Az önce';

  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Az önce';
  if (diffMins < 60) return `${diffMins} dk önce`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} saat önce`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'Dün';
  return `${diffDays} gün önce`;
}
