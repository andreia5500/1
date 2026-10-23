// Мелкие утилиты: суммы, даты, округление

/** «1 000,00», «+30 702,57», «+ 50 000.00», «- 49 358.00» → число */
export function parseMoney(s: string): number | null {
  const t = s.replace(/[\s  ]/g, '').replace('₽', '');
  const m = t.match(/^([+\-−]?)(\d+)(?:[.,](\d{1,2}))?$/);
  if (!m) return null;
  const v = Number(m[2]) + (m[3] ? Number(m[3].padEnd(2, '0')) / 100 : 0);
  return m[1] === '-' || m[1] === '−' ? -v : v;
}

/** Похоже ли на денежную сумму в колонке выписки */
export const MONEY_RE = /^[+\-−]?\s?\d{1,3}(?:[   ]\d{3})*[.,]\d{2}$/;

export function isMoney(s: string): boolean { return MONEY_RE.test(s.trim()); }

/** '21.10.2026' или '21.10.26' → '2026-10-21' */
export function ruDate(s: string): string | null {
  const m = s.trim().match(/^(\d{2})\.(\d{2})\.(\d{2}|\d{4})$/);
  if (!m) return null;
  const y = m[3].length === 2 ? '20' + m[3] : m[3];
  return `${y}-${m[2]}-${m[1]}`;
}

export const round2 = (v: number) => Math.round(v * 100) / 100;

export function sum(xs: number[]): number { return round2(xs.reduce((a, b) => a + b, 0)); }

export function monthKey(date: string): string { return date.slice(0, 7); }

export function daysInMonth(month: string): number {
  const [y, m] = month.split('-').map(Number);
  return new Date(y, m, 0).getDate();
}

export function addDays(date: string, n: number): string {
  const d = new Date(date + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function diffDays(a: string, b: string): number {
  return Math.round((Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / 86400000);
}

export function todayIso(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

const MONTHS = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'];
const MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

export function monthTitle(month: string): string {
  const [y, m] = month.split('-').map(Number);
  const t = MONTHS[m - 1];
  return t[0].toUpperCase() + t.slice(1) + ' ' + y;
}

export function dayTitle(date: string): string {
  const [, m, d] = date.split('-').map(Number);
  return `${d} ${MONTHS_GEN[m - 1]}`;
}

export function fmtDate(date: string): string {
  const [y, m, d] = date.split('-');
  return `${d}.${m}.${y}`;
}

export function hash(s: string): string {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(36);
}
