// Прогноз на конец месяца, лимиты, цели
import type { AppData, ClassifiedTx, Goal, Planned } from './types';
import { catInfo } from './categories';
import { addDays, daysInMonth, diffDays, monthKey, round2, sum } from './util';

export interface Forecast {
  month: string;
  today: string;
  daysLeft: number;
  cashNow: number;              // свои деньги на дебетовых счетах (последние известные остатки)
  cashNowNote: string[];
  plannedIncome: { p: Planned; date: string }[];
  plannedPayments: { p: Planned; date: string }[];
  dailyEveryday: number;        // средние повседневные траты в день
  everydayRest: number;         // прогноз повседневных трат до конца месяца
  endBalance: number;           // прогноз свободных денег на конец месяца
  goalMonthly: number;          // сколько нужно отложить в этом месяце на цели
  freeAfterGoals: number;
}

/** Средние повседневные траты в день за последние N дней, где есть данные */
export function everydayDailyRate(txs: ClassifiedTx[], today: string, windowDays = 45): number {
  const from = addDays(today, -windowDays);
  const list = txs.filter(t => t.date > from && t.date <= today && (t.kind === 'expense' || t.kind === 'refund') && catInfo(t.category).everyday);
  if (!list.length) return 0;
  const first = list.reduce((m, t) => (t.date < m ? t.date : m), today);
  const span = Math.max(14, diffDays(first, today) + 1); // не меньше двух недель, чтобы не завышать по одному дню
  return round2(sum(list.map(t => -t.amount)) / span);
}

export function forecastMonth(data: AppData, txs: ClassifiedTx[], today: string): Forecast {
  const month = monthKey(today);
  const dim = daysInMonth(month);
  const day = Number(today.slice(8));
  const daysLeft = dim - day;

  // Деньги сейчас: последние известные остатки дебетовых счетов + операции после даты остатка
  let cashNow = 0;
  const cashNowNote: string[] = [];
  for (const a of data.accounts.filter(a => a.kind === 'debit' && a.balance !== undefined)) {
    cashNow += a.balance!;
    cashNowNote.push(`${a.title}: ${a.balance!.toLocaleString('ru-RU')} ₽ на ${a.balanceDate?.split('-').reverse().join('.')}`);
  }
  cashNow = round2(cashNow);

  const dateOf = (p: Planned) => `${month}-${String(Math.min(p.day, dim)).padStart(2, '0')}`;
  const already = (p: Planned) => {
    // уже случилось в этом месяце?
    const thisMonth = txs.filter(t => monthKey(t.date) === month);
    if (p.key?.startsWith('pay:')) { const m = p.key.slice(4); return thisMonth.some(t => t.kind === 'expense' && t.merchant === m); }
    if (p.key?.startsWith('min:')) return dateOf(p) < today;
    if (p.type === 'income') {
      const d = dateOf(p);
      return thisMonth.some(t => t.kind === 'income' && Math.abs(diffDays(t.date, d)) <= 5 && Math.abs(t.amount - p.amount) / p.amount < 0.35);
    }
    return dateOf(p) < today;
  };
  const upcoming = data.settings.planned.filter(p => p.enabled && p.day >= day && !already(p));
  const plannedIncome = upcoming.filter(p => p.type === 'income').map(p => ({ p, date: dateOf(p) }));
  const plannedPayments = upcoming.filter(p => p.type === 'payment').map(p => ({ p, date: dateOf(p) }));

  const dailyEveryday = everydayDailyRate(txs, today);
  const everydayRest = round2(dailyEveryday * daysLeft);
  const endBalance = round2(cashNow + sum(plannedIncome.map(x => x.p.amount)) - sum(plannedPayments.map(x => x.p.amount)) - everydayRest);
  const goalMonthly = round2(sum(data.settings.goals.map(g => goalPlan(g, today).perMonth)));
  return { month, today, daysLeft, cashNow, cashNowNote, plannedIncome, plannedPayments, dailyEveryday, everydayRest, endBalance, goalMonthly, freeAfterGoals: round2(endBalance - goalMonthly) };
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
