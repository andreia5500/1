// Аналитика: сводка за месяц, покрытие месяца выписками, регулярные платежи, подсказки по экономии
import type { Account, AppData, ClassifiedTx, Planned, StatementMeta } from './types';
import { EXPENSE_CATEGORIES, TRANSFER_CATEGORY, catInfo } from './categories';
import { daysInMonth, diffDays, monthKey, round2, sum } from './util';
import { prettyName } from './classify';

export interface CatSum { category: string; amount: number; count: number; share: number }

export interface MonthSummary {
  month: string;
  income: number;
  expense: number;           // расходы за вычетом возвратов
  net: number;
  refunds: number;
  byCategory: CatSum[];      // расходы
  incomeByCategory: CatSum[];
  toOwnOtherBanks: number;   // ушло на свои счета/вклады (чистое перемещение)
  topMerchants: { merchant: string; label: string; amount: number; count: number }[];
  daily: { date: string; amount: number }[];
  needsReview: number;
}

export function monthsAvailable(txs: ClassifiedTx[]): string[] {
  return [...new Set(txs.map(t => monthKey(t.date)))].sort().reverse();
}

export function summarizeMonth(txs: ClassifiedTx[], month: string): MonthSummary {
  const m = txs.filter(t => monthKey(t.date) === month);
  const exp = new Map<string, { amount: number; count: number }>();
  const inc = new Map<string, { amount: number; count: number }>();
  const merch = new Map<string, { label: string; amount: number; count: number }>();
  const daily = new Map<string, number>();
  let refunds = 0, toOwn = 0;
  for (const t of m) {
    if (t.kind === 'expense' || t.kind === 'refund') {
      const v = -t.amount; // расход положительный, возврат отрицательный
      if (t.kind === 'refund') refunds += t.amount;
      const e = exp.get(t.category) ?? { amount: 0, count: 0 };
      e.amount += v; if (t.kind === 'expense') e.count++;
      exp.set(t.category, e);
      const mm = merch.get(t.merchant) ?? { label: prettyName(t.description), amount: 0, count: 0 };
      mm.amount += v; if (t.kind === 'expense') mm.count++;
      merch.set(t.merchant, mm);
      if (t.kind === 'expense') daily.set(t.date, (daily.get(t.date) ?? 0) + v);
    } else if (t.kind === 'income') {
      const e = inc.get(t.category) ?? { amount: 0, count: 0 };
      e.amount += t.amount; e.count++;
      inc.set(t.category, e);
    } else if (t.kind === 'transfer' && !t.pairId) {
      // перевод без пары внутри импортированных счетов = деньги ушли/пришли на свой счёт, которого здесь нет
      toOwn -= t.amount;
    }
  }
  const expense = round2([...exp.values()].reduce((a, b) => a + b.amount, 0));
  const income = round2([...inc.values()].reduce((a, b) => a + b.amount, 0));
  const toList = (mp: Map<string, { amount: number; count: number }>, total: number): CatSum[] =>
    [...mp.entries()].map(([category, v]) => ({ category, amount: round2(v.amount), count: v.count, share: total > 0 ? v.amount / total : 0 }))
      .filter(c => Math.abs(c.amount) >= 0.01)
      .sort((a, b) => b.amount - a.amount);
  return {
    month,
    income, expense, net: round2(income - expense), refunds: round2(refunds),
    byCategory: toList(exp, expense),
    incomeByCategory: toList(inc, income),
    toOwnOtherBanks: round2(toOwn),
    topMerchants: [...merch.entries()].map(([merchant, v]) => ({ merchant, ...v, amount: round2(v.amount) }))
      .filter(x => x.amount > 0).sort((a, b) => b.amount - a.amount).slice(0, 8),
    daily: [...daily.entries()].map(([date, amount]) => ({ date, amount: round2(amount) })).sort((a, b) => a.date.localeCompare(b.date)),
    needsReview: m.filter(t => t.needsReview).length,
  };
}

export interface Coverage { account: Account; from?: string; to?: string; days: number; total: number }

/** Какие дни месяца покрыты выписками по каждому счёту */
export function monthCoverage(accounts: Account[], statements: StatementMeta[], month: string): Coverage[] {
  const first = month + '-01';
  const last = month + '-' + String(daysInMonth(month)).padStart(2, '0');
  return accounts.map(account => {
    const covered = new Set<string>();
    for (const s of statements.filter(s => s.accountId === account.id)) {
      const from = s.periodFrom > first ? s.periodFrom : first;
      const to = s.periodTo < last ? s.periodTo : last;
      if (from > to) continue;
      for (let i = 0; i <= diffDays(from, to); i++) {
        const d = new Date(from + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + i);
        covered.add(d.toISOString().slice(0, 10));
      }
    }
    const days = [...covered].sort();
    return { account, from: days[0], to: days[days.length - 1], days: days.length, total: daysInMonth(month) };
  });
}

/** Автопредложения для плана: зарплата/аванс и регулярные платежи из истории */
export function suggestPlanned(data: AppData, txs: ClassifiedTx[]): Planned[] {
  const out: Planned[] = [];
  const add = (p: Planned) => {
    if (data.settings.plannedDismissed.includes(p.key!)) return;
    if (data.settings.planned.some(x => x.key === p.key)) return;
    if (out.some(x => x.key === p.key)) return;
    out.push(p);
  };
  const latest = (pred: (t: ClassifiedTx) => boolean) => txs.filter(pred).sort((a, b) => b.date.localeCompare(a.date))[0];

  const sal = latest(t => t.kind === 'income' && /заработная плата|зарплата/i.test(t.description) && !/аванс/i.test(t.description));
  if (sal) add({ id: 'auto-salary', key: 'salary', title: 'Зарплата', type: 'income', amount: sal.amount, day: Number(sal.date.slice(8)), enabled: true, auto: true, category: 'Зарплата' });
  const adv = latest(t => t.kind === 'income' && /аванс/i.test(t.description));
  if (adv) add({ id: 'auto-advance', key: 'advance', title: 'Аванс', type: 'income', amount: adv.amount, day: Number(adv.date.slice(8)), enabled: true, auto: true, category: 'Зарплата' });

  // Регулярные категории: берём последний платёж по каждому продавцу
  const regularCats = new Set(EXPENSE_CATEGORIES.filter(c => c.regular).map(c => c.name));
  const byMerchant = new Map<string, ClassifiedTx[]>();
  for (const t of txs) if (t.kind === 'expense' && regularCats.has(t.category)) {
    byMerchant.set(t.merchant, [...(byMerchant.get(t.merchant) ?? []), t]);
  }
  for (const [merchant, list] of byMerchant) {
    list.sort((a, b) => b.date.localeCompare(a.date));
    const lastMonth = monthKey(list[0].date);
    const monthSum = sum(list.filter(t => monthKey(t.date) === lastMonth).map(t => -t.amount));
    add({ id: 'auto-' + merchant, key: 'pay:' + merchant, title: prettyName(list[0].description).slice(0, 45), type: 'payment', amount: monthSum, day: Number(list[0].date.slice(8)), enabled: true, auto: true, category: list[0].category });
  }
  // Минимальные платежи по кредиткам
  for (const a of data.accounts) {
    if (a.kind === 'credit' && a.minPayment && a.minPaymentDue) {
      add({ id: 'auto-min-' + a.id, key: 'min:' + a.id, title: `Мин. платёж: ${a.title}`, type: 'payment', amount: a.minPayment, day: Number(a.minPaymentDue.slice(8)), enabled: true, auto: true, category: 'Проценты по кредитам' });
    }
  }
  return out;
}

export interface Tip { title: string; text: string; amount?: number; category?: string; suggestLimit?: number }

/** Подсказки, где можно сэкономить — только по фактам из выписок */
export function savingTips(txs: ClassifiedTx[], month: string, _accounts?: Account[]): Tip[] {
  const tips: Tip[] = [];
  const m = txs.filter(t => monthKey(t.date) === month && t.kind === 'expense');
  const fees = m.filter(t => t.category === 'Комиссии банка');
  if (fees.length) {
    const v = sum(fees.map(t => -t.amount));
    tips.push({ title: 'Комиссии банка', amount: v, category: 'Комиссии банка', text: `${plural(fees.length, 'комиссия', 'комиссии', 'комиссий')} на ${fmt(v)}. Например: «${fees[0].description.slice(0, 50)}». Снимайте наличные в банкоматах своего банка или в пределах бесплатного лимита.` });
  }
  const mp = m.filter(t => t.category === 'Маркетплейсы');
  if (mp.length >= 5) {
    const gross = sum(mp.map(t => -t.amount));
    const ref = sum(txs.filter(t => monthKey(t.date) === month && t.kind === 'refund' && t.category === 'Маркетплейсы').map(t => t.amount));
    const small = mp.filter(t => -t.amount < 500).length;
    const net = round2(gross - ref);
    tips.push({
      title: `Маркетплейсы: ${plural(mp.length, 'покупка', 'покупки', 'покупок')} за месяц`, amount: net, category: 'Маркетплейсы',
      suggestLimit: Math.max(500, Math.round(net * 0.8 / 100) * 100),
      text: `${fmt(gross)}${ref > 0 ? `, после возвратов ${fmt(net)}` : ''}. Средний чек ${fmt(gross / mp.length)}, ${small} из них дешевле 500 ₽ — мелкие заказы складываются незаметно.`,
    });
  }
  const subs = m.filter(t => t.category === 'Подписки и развлечения');
  if (subs.length) {
    const v = sum(subs.map(t => -t.amount));
    tips.push({ title: 'Подписки', amount: v, category: 'Подписки и развлечения', text: `${plural(subs.length, 'списание', 'списания', 'списаний')} на ${fmt(v)}: ${[...new Set(subs.map(t => t.description.slice(0, 25)))].slice(0, 4).join(', ')}. Проверьте, всеми ли пользуетесь.` });
  }
  const cash = m.filter(t => t.category === 'Наличные');
  if (cash.length) {
    const v = sum(cash.map(t => -t.amount));
    tips.push({ title: 'Наличные', amount: v, text: `Снято ${fmt(v)} — в выписке не видно, на что они ушли. Записывайте траты наличными кнопкой «+», тогда они попадут в анализ.` });
  }
  return tips;
}

export function plural(n: number, one: string, few: string, many: string): string {
  const a = n % 10, b = n % 100;
  const w = a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 12 || b > 14) ? few : many;
  return `${n} ${w}`;
}

export function fmt(v: number, digits = 0): string {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v) + ' ₽';
}

export { TRANSFER_CATEGORY, catInfo };
