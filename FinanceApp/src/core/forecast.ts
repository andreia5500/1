// Средние траты, лимиты, цели
import type { AppData, ClassifiedTx, Goal } from './types';
import { catInfo } from './categories';
import { addDays, daysInMonth, diffDays, monthKey, round2, sum } from './util';

/** Средние повседневные траты в день за последние N дней, где есть данные */
export function everydayDailyRate(txs: ClassifiedTx[], today: string, windowDays = 45): number {
  const from = addDays(today, -windowDays);
  const list = txs.filter(t => t.date > from && t.date <= today && (t.kind === 'expense' || t.kind === 'refund') && catInfo(t.category).everyday);
  if (!list.length) return 0;
  const first = list.reduce((m, t) => (t.date < m ? t.date : m), today);
  const span = Math.max(14, diffDays(first, today) + 1); // не меньше двух недель, чтобы не завышать по одному дню
  return round2(sum(list.map(t => -t.amount)) / span);
}

export interface LimitState { category: string; limit: number; spent: number; projected: number; status: 'ok' | 'warn' | 'over' }

export function limitStates(data: AppData, txs: ClassifiedTx[], today: string): LimitState[] {
  const month = monthKey(today);
  const dim = daysInMonth(month);
  const day = Number(today.slice(8));
  return Object.entries(data.settings.limits).filter(([, v]) => v > 0).map(([category, limit]) => {
    const spent = round2(sum(txs.filter(t => monthKey(t.date) === month && t.category === category && (t.kind === 'expense' || t.kind === 'refund')).map(t => -t.amount)));
    const projected = round2(day > 0 ? spent / day * dim : spent);
    const status = spent > limit ? 'over' : projected > limit ? 'warn' : 'ok';
    return { category, limit, spent, projected, status };
  });
}

export function goalPlan(g: Goal, today: string): { left: number; months: number; perMonth: number } {
  const left = Math.max(0, round2(g.target - g.saved));
  if (!g.deadline) return { left, months: 0, perMonth: 0 };
  const months = Math.max(1, Math.ceil(diffDays(today, g.deadline) / 30.4));
  return { left, months, perMonth: round2(left / months) };
}
