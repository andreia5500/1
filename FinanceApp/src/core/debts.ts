// План погашения долгов: метод «лавина» (сначала самый дорогой долг)
import type { AppData } from './types';
import { round2 } from './util';

export interface Debt { id: string; title: string; debt: number; rate: number; minPayment: number; fromStatement: boolean; limit?: number }

export function collectDebts(data: AppData): Debt[] {
  const out: Debt[] = [];
  for (const a of data.accounts.filter(a => a.kind === 'credit' && (a.debt ?? 0) > 0)) {
    const o = data.settings.debtOverrides[a.id] ?? {};
    const debt = a.debt!;
    out.push({
      id: a.id, title: a.title, debt, fromStatement: true, limit: a.creditLimit,
      rate: o.rate ?? a.rate ?? 0,
      // если банк не указал минимальный платёж — берём типичные 3% от долга
      minPayment: o.minPayment ?? a.minPayment ?? Math.ceil(debt * 0.03),
    });
  }
  for (const m of data.settings.manualDebts) out.push({ ...m, fromStatement: false });
  return out;
}

export interface PayoffResult {
  months: number;              // за сколько месяцев закроются все долги (Infinity если бюджета не хватает)
  totalInterest: number;
  order: string[];             // в каком порядке закрываются
  schedule: { month: number; remaining: number }[];
  enough: boolean;
}

/** Упрощённая модель: проценты начисляются ежемесячно на остаток (льготный период не учитывается — оценка «сверху») */
export function simulatePayoff(debts: Debt[], monthlyBudget: number, maxMonths = 360): PayoffResult {
  const ds = debts.map(d => ({ ...d, left: d.debt }));
  const minSum = ds.reduce((s, d) => s + d.minPayment, 0);
  if (!ds.length) return { months: 0, totalInterest: 0, order: [], schedule: [], enough: true };
  const budget = Math.max(monthlyBudget, 0);
  let totalInterest = 0;
  const order: string[] = [];
  const schedule: { month: number; remaining: number }[] = [];
  let month = 0;
  while (ds.some(d => d.left > 0.01) && month < maxMonths) {
    month++;
    for (const d of ds) if (d.left > 0) { const i = d.left * d.rate / 100 / 12; d.left += i; totalInterest += i; }
    let money = budget;
    for (const d of ds) if (d.left > 0) { const p = Math.min(d.minPayment, d.left, money); d.left -= p; money -= p; }
    const byRate = ds.filter(d => d.left > 0).sort((a, b) => b.rate - a.rate || a.left - b.left);
    for (const d of byRate) { if (money <= 0) break; const p = Math.min(money, d.left); d.left -= p; money -= p; }
    for (const d of ds) if (d.left <= 0.01 && !order.includes(d.title)) { d.left = 0; order.push(d.title); }
    schedule.push({ month, remaining: round2(ds.reduce((s, d) => s + d.left, 0)) });
    if (month > 2 && schedule[month - 1].remaining >= schedule[month - 2].remaining) {
      return { months: Infinity, totalInterest: round2(totalInterest), order, schedule, enough: false };
    }
  }
  const done = !ds.some(d => d.left > 0.01);
  return { months: done ? month : Infinity, totalInterest: round2(totalInterest), order, schedule, enough: done && budget >= minSum };
}
