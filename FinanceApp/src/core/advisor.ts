// Личный консультант: прокручивает деньги по дням вперёд и предупреждает,
// если на постоянный платёж может не хватить.
import type { AppData, ClassifiedTx, Planned } from './types';
import { addDays, daysInMonth, diffDays, fmtDate, monthKey, round2 } from './util';
import { everydayDailyRate } from './forecast';

export interface Occurrence {
  p: Planned;
  date: string;
  key: string;        // '<id>@<дата>' — им же помечается «оплачено»
  done: boolean;
}

export interface CashNow {
  amount: number;
  asOf: string;               // на какую дату известен остаток
  source: 'statements' | 'manual' | 'none';
  parts: string[];            // откуда взялось число
  manualDelta: number;        // ручные операции после этой даты
  stale: boolean;             // остаток старше 3 дней
}

export interface DayPoint {
  date: string;
  everyday: number;
  events: { occ: Occurrence; after: number }[];
  end: number;
}

export interface Warning {
  level: 'danger' | 'warn' | 'ok' | 'info';
  title: string;
  text: string;
  date?: string;
}

export interface Advice {
  today: string;
  cash: CashNow;
  rate: number;                 // повседневные траты в день
  safePerDay: number;           // сколько можно тратить в день, чтобы хватило на все платежи
  safeUntil: string;            // самый «узкий» день, по которому посчитан лимит
  buffer: number;
  timeline: DayPoint[];
  upcoming: { occ: Occurrence; after: number; status: 'ok' | 'tight' | 'short' }[];
  warnings: Warning[];
  nextIncome?: Occurrence;
  monthEnd?: number;            // остаток на конец текущего месяца
  minPoint?: { date: string; value: number };
  monthlyPayments: number;      // сумма постоянных платежей в месяц (в среднем)
  monthlyIncome: number;
}

const periodMonths = (p: Planned) => (p.period === 'quarter' ? 3 : p.period === 'year' ? 12 : 1);

/** Все даты постоянного платежа в интервале [from, to] */
export function occurrences(p: Planned, from: string, to: string): string[] {
  const out: string[] = [];
  let [y, m] = from.split('-').map(Number);
  const step = periodMonths(p);
  const start = p.startMonth ?? m;
  for (let i = 0; i < 40; i++) {
    const mk = `${y}-${String(m).padStart(2, '0')}`;
    if (step === 1 || ((m - start) % step + step) % step === 0) {
      const d = `${mk}-${String(Math.min(p.day, daysInMonth(mk))).padStart(2, '0')}`;
      if (d > to) break;
      if (d >= from) out.push(d);
    }
    if (`${mk}-01` > to) break;
    m++; if (m > 12) { m = 1; y++; }
  }
  return out;
}

/** Случился ли уже этот платёж / поступление */
export function isDone(p: Planned, date: string, txs: ClassifiedTx[]): boolean {
  const key = `${p.id}@${date}`;
  if (txs.some(t => t.plannedRef === key)) return true;
  const near = (t: ClassifiedTx, days: number) => Math.abs(diffDays(t.date, date)) <= days;
  if (p.key?.startsWith('pay:')) {
    const m = p.key.slice(4);
    return txs.some(t => t.kind === 'expense' && t.merchant === m && near(t, 5));
  }
  if (p.key?.startsWith('min:')) return false;
  if (p.type === 'income') {
    return txs.some(t => t.kind === 'income' && near(t, 5) && Math.abs(t.amount - p.amount) / Math.max(p.amount, 1) < 0.35);
  }
  return txs.some(t => (t.kind === 'expense' || t.kind === 'transfer') && t.amount < 0 && near(t, 3)
    && Math.abs(-t.amount - p.amount) / Math.max(p.amount, 1) < 0.03);
}

export function cashNow(data: AppData, txs: ClassifiedTx[], today: string): CashNow {
  const debit = data.accounts.filter(a => a.kind === 'debit' && a.balance !== undefined);
  let amount = 0, asOf = '', source: CashNow['source'] = 'none';
  const parts: string[] = [];
  for (const a of debit) {
    amount += a.balance!;
    if ((a.balanceDate ?? '') > asOf) asOf = a.balanceDate ?? '';
    parts.push(`${a.title}: ${Math.round(a.balance!).toLocaleString('ru-RU')} ₽ на ${fmtDate(a.balanceDate ?? today)}`);
  }
  if (debit.length) source = 'statements';
  const ov = data.settings.balanceOverride;
  let manualFilter = (t: ClassifiedTx) => t.date > asOf;
  if (ov && (source === 'none' || ov.at.slice(0, 10) >= asOf)) {
    amount = ov.amount; asOf = ov.at.slice(0, 10); source = 'manual';
    parts.length = 0;
    parts.push(`Вы указали ${Math.round(ov.amount).toLocaleString('ru-RU')} ₽ на ${fmtDate(asOf)}`);
    manualFilter = (t) => (t.createdAt ?? `${t.date}T23:59`) > ov.at;
  }
  const manual = txs.filter(t => t.manual && t.kind !== 'matched' && t.date <= today && manualFilter(t));
  const manualDelta = round2(manual.reduce((s, t) => s + t.amount, 0));
  if (manual.length) parts.push(`Внесено вручную после этого: ${manualDelta > 0 ? '+' : ''}${Math.round(manualDelta).toLocaleString('ru-RU')} ₽`);
  return { amount: round2(amount + manualDelta), asOf: asOf || today, source, parts, manualDelta, stale: !!asOf && diffDays(asOf, today) > 3 };
}

export function advise(data: AppData, txs: ClassifiedTx[], today: string, horizon = 45): Advice {
  const buffer = data.settings.safetyBuffer ?? 2000;
  const cash = cashNow(data, txs, today);
  const rate = everydayDailyRate(txs, today);
  const end = addDays(today, horizon);

  const occs: Occurrence[] = [];
  for (const p of data.settings.planned.filter(p => p.enabled && p.amount > 0)) {
    for (const date of occurrences(p, today, end)) {
      const done = isDone(p, date, txs);
      occs.push({ p, date, key: `${p.id}@${date}`, done });
    }
  }
  const pending = occs.filter(o => !o.done).sort((a, b) => a.date.localeCompare(b.date) || (a.p.type === 'income' ? -1 : 1));

  // День за днём
  const timeline: DayPoint[] = [];
  let bal = cash.amount;
  for (let i = 0; i <= horizon; i++) {
    const date = addDays(today, i);
    const everyday = i === 0 ? 0 : rate; // сегодняшние траты вы вносите сами или они уже в выписке
    bal -= everyday;
    const events: DayPoint['events'] = [];
    for (const o of pending.filter(o => o.date === date)) {
      bal += o.p.type === 'income' ? o.p.amount : -o.p.amount;
      events.push({ occ: o, after: round2(bal) });
    }
    timeline.push({ date, everyday, events, end: round2(bal) });
  }

  // Сколько можно тратить в день: остаток минус все будущие платежи (плюс поступления) не ниже подушки в любой день
  // Смотрим полный цикл: до дня перед второй зарплатой (если она попадает в горизонт)
  const incDates = [...new Set(pending.filter(o => o.p.type === 'income' && o.date > today).map(o => o.date))];
  const lastDay = incDates[1] ? diffDays(today, incDates[1]) - 1 : horizon;
  let safe = Infinity, safeUntil = addDays(today, lastDay);
  let fixed = cash.amount;
  for (let i = 1; i <= lastDay; i++) {
    const date = addDays(today, i);
    for (const o of pending.filter(o => o.date === date)) fixed += o.p.type === 'income' ? o.p.amount : -o.p.amount;
    const v = (fixed - buffer) / i;
    if (v < safe) { safe = v; safeUntil = date; }
  }
  // платежи сегодня
  for (const o of pending.filter(o => o.date === today)) if (o.p.type === 'payment') safe = Math.min(safe, (cash.amount - o.p.amount - buffer));
  const safePerDay = Number.isFinite(safe) ? Math.floor(safe) : 0;

  const upcoming = timeline.flatMap(d => d.events.map(e => ({ ...e, status: (e.after < 0 ? 'short' : e.after < buffer ? 'tight' : 'ok') as 'ok' | 'tight' | 'short' })));

  const warnings: Warning[] = [];
  const incomes = (before: string) => pending.filter(o => o.p.type === 'income' && o.date >= today && o.date <= before);
  for (const e of upcoming.filter(e => e.occ.p.type === 'payment' && e.status !== 'ok').slice(0, 4)) {
    const days = Math.max(1, diffDays(today, e.occ.date));
    const inc = incomes(e.occ.date);
    let how: string;
    if (inc.length) {
      how = `Отложите ${rub(Math.ceil((buffer - e.after) / 100) * 100)} из «${inc[0].p.title}» ${fmtDate(inc[0].date).slice(0, 5)} и не тратьте их до платежа.`;
    } else if (rate * days > buffer - e.after) {
      const cut = Math.max(0, Math.floor(rate - (buffer - e.after) / days));
      how = `Чтобы хватило, тратьте не больше ${rub(cut)} в день до ${fmtDate(e.occ.date).slice(0, 5)} (сейчас в среднем ${rub(rate)}).`;
    } else {
      how = `Даже без повседневных трат не хватит ${rub(-e.after)} — заранее найдите деньги или договоритесь о переносе.`;
    }
    warnings.push({
      level: e.status === 'short' ? 'danger' : 'warn',
      date: e.occ.date,
      title: e.status === 'short'
        ? `Не хватит ≈ ${rub(-e.after)} на «${e.occ.p.title}» ${fmtDate(e.occ.date).slice(0, 5)}`
        : `Впритык: «${e.occ.p.title}» ${fmtDate(e.occ.date).slice(0, 5)}`,
      text: (e.status === 'short'
        ? `К ${fmtDate(e.occ.date).slice(0, 5)} при нынешних тратах на картах будет меньше, чем ${rub(e.occ.p.amount)}. `
        : `После платежа останется около ${rub(e.after)} — меньше вашей подушки ${rub(buffer)}. `) + how,
    });
  }

  // Совет на день зарплаты: сколько отложить на платежи до следующей
  const incList = pending.filter(o => o.p.type === 'income');
  for (let i = 0; i < Math.min(incList.length, 2); i++) {
    const inc = incList[i];
    const next = incList[i + 1]?.date ?? end;
    const pays = pending.filter(o => o.p.type === 'payment' && o.date >= inc.date && o.date < next);
    const total = pays.reduce((s, o) => s + o.p.amount, 0);
    if (total > 0) warnings.push({
      level: 'info', date: inc.date,
      title: `${fmtDate(inc.date).slice(0, 5)} «${inc.p.title}»: сразу отложите ${rub(total)}`,
      text: `Это платежи до ${fmtDate(next).slice(0, 5)}: ${pays.map(o => `${o.p.title} ${rub(o.p.amount)} (${fmtDate(o.date).slice(0, 5)})`).join(', ')}.`,
    });
  }

  const min = timeline.reduce((m, d) => (d.end < m.value ? { date: d.date, value: d.end } : m), { date: today, value: cash.amount });
  if (!warnings.some(w => w.level === 'danger' || w.level === 'warn')) {
    warnings.unshift({ level: 'ok', title: 'На все постоянные платежи хватает', text: `До ${fmtDate(end)} при нынешних тратах остаток не опустится ниже ${rub(Math.max(min.value, 0))}.` });
  }

  const monthEndDate = `${monthKey(today)}-${String(daysInMonth(monthKey(today))).padStart(2, '0')}`;
  const me = timeline.find(d => d.date === monthEndDate);
  const perMonth = (type: 'income' | 'payment') => round2(data.settings.planned.filter(p => p.enabled && p.type === type).reduce((s, p) => s + p.amount / periodMonths(p), 0));
  return {
    today, cash, rate, safePerDay, safeUntil, buffer, timeline, upcoming, warnings,
    nextIncome: incList[0], monthEnd: me?.end, minPoint: min,
    monthlyPayments: perMonth('payment'), monthlyIncome: perMonth('income'),
  };
}

export function rub(v: number): string {
  return Math.round(v).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ₽';
}
