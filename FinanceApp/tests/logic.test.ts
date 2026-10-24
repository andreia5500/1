// Тесты логики без реальных выписок — запускаются и в GitHub Actions
import { describe, it, expect } from 'vitest';
import { classifyAll } from '../src/core/classify';
import { summarizeMonth } from '../src/core/analytics';
import { simulatePayoff } from '../src/core/debts';
import { parseMoney, ruDate } from '../src/core/util';
import { scrub } from '../src/core/aiSummary';
import { emptyData, type AppData, type RawTx } from '../src/core/types';

const tx = (id: string, accountId: string, date: string, amount: number, description: string, bankCategory?: string, time = '10:00'): RawTx =>
  ({ id, accountId, date, time, amount, description, bankCategory });

function sample(): AppData {
  const d = emptyData();
  d.accounts = [
    { id: 'sber:1', bank: 'sber', kind: 'debit', title: 'Сбер дебет', number: '1', cards: ['1111'] },
    { id: 'sber:2', bank: 'sber', kind: 'credit', title: 'Сбер кредитка', number: '2', cards: ['2222'] },
  ];
  d.txs = [
    tx('a', 'sber:1', '2026-10-09', 50000, 'Заработная плата', 'Прочие операции'),
    tx('b', 'sber:1', '2026-10-10', -5000, 'SBOL', 'Перевод с карты', '12:00'),
    tx('c', 'sber:2', '2026-10-10', 5000, 'С карты 427616******1111', 'Перевод на карту', '12:00'),
    tx('d', 'sber:2', '2026-10-11', -1300, 'MOSCOW YM*OZON', 'Прочие расходы'),
    tx('e', 'sber:2', '2026-10-12', 300, 'MOSCOW OZON Возврат покупки', 'Возврат, отмена операции'),
    tx('f', 'sber:1', '2026-10-13', -10000, 'Озон Банк (Ozon)', 'Перевод СБП'),
    tx('g', 'sber:1', '2026-10-14', -2000, 'ВТБ', 'Перевод СБП'),
    tx('h', 'sber:1', '2026-10-15', -700, 'SBOL', 'Перевод с карты'),
  ];
  return d;
}

describe('логика', () => {
  it('суммы и даты', () => {
    expect(parseMoney('+30 702,57')).toBe(30702.57);
    expect(parseMoney('- 49 358.00')).toBe(-49358);
    expect(parseMoney('1 000,00')).toBe(1000);
    expect(ruDate('09.09.26')).toBe('2026-09-09');
  });

  it('переводы между своими картами не считаются доходом и расходом', () => {
    const txs = classifyAll(sample());
    const k = Object.fromEntries(txs.map(t => [t.id, t]));
    expect(k.b.kind).toBe('transfer');
    expect(k.c.kind).toBe('transfer');
    expect(k.f.kind).toBe('transfer');          // Озон Банк — свой
    expect(k.g.category).toBe('Переводы другим людям'); // ВТБ — не отмечен своим
    expect(k.h.needsReview).toBe(true);         // непарный SBOL
    expect(k.e.kind).toBe('refund');
    const s = summarizeMonth(txs, '2026-10');
    expect(s.income).toBe(50000);
    expect(s.expense).toBe(1300 - 300 + 2000 + 700);
    expect(s.toOwnOtherBanks).toBe(10000);
  });

  it('правило пользователя применяется ко всем похожим', () => {
    const d = sample();
    d.rules = [{ merchant: 'sbol', category: 'Свои переводы', kind: 'transfer' }];
    const h = classifyAll(d).find(t => t.id === 'h')!;
    expect(h.kind).toBe('transfer');
    expect(h.needsReview).toBe(false);
  });

  it('план погашения долгов', () => {
    const debts = [
      { id: '1', title: 'A', debt: 70000, rate: 24, minPayment: 2100, fromStatement: true },
      { id: '2', title: 'B', debt: 48000, rate: 30, minPayment: 900, fromStatement: true },
    ];
    const r = simulatePayoff(debts, 15000);
    expect(r.enough).toBe(true);
    expect(r.order[0]).toBe('B');               // сначала дорогой
    expect(r.months).toBeGreaterThan(7);
    expect(simulatePayoff(debts, 1000).enough).toBe(false);
  });

  it('обезличивание сводки', () => {
    expect(scrub('Внешний перевод по номеру телефона +79001234567')).not.toMatch(/7900/);
    expect(scrub('Перевод от И. Иван Петрович')).toBe('Перевод от [ФИО]');
  });
});

import { advise, occurrences } from '../src/core/advisor';
import { MANUAL_ACCOUNT_ID } from '../src/core/types';

describe('консультант', () => {
  const base = () => {
    const d = emptyData();
    d.accounts = [{ id: 'sber:1', bank: 'sber', kind: 'debit', title: 'Сбер дебет', number: '1', cards: ['1111'], balance: 12000, balanceDate: '2026-10-24' }];
    d.settings.safetyBuffer = 1000;
    d.settings.planned = [
      { id: 'rent', title: 'Кредит', type: 'payment', amount: 15000, day: 5, enabled: true },
      { id: 'net', title: 'Интернет', type: 'payment', amount: 1000, day: 28, enabled: true },
      { id: 'sal', title: 'Зарплата', type: 'income', amount: 50000, day: 9, enabled: true },
    ];
    return d;
  };

  it('даты постоянных платежей', () => {
    expect(occurrences({ id: 'a', title: '', type: 'payment', amount: 1, day: 31, enabled: true }, '2026-10-24', '2026-12-10')).toEqual(['2026-10-31', '2026-11-30']);
    expect(occurrences({ id: 'q', title: '', type: 'payment', amount: 1, day: 10, enabled: true, period: 'quarter', startMonth: 1 }, '2026-01-01', '2026-12-31')).toEqual(['2026-01-10', '2026-04-10', '2026-07-10', '2026-10-10']);
    expect(occurrences({ id: 'y', title: '', type: 'payment', amount: 1, day: 1, enabled: true, period: 'year', startMonth: 3 }, '2026-10-24', '2027-04-01')).toEqual(['2027-03-01']);
  });

  it('предупреждает, что на платёж 5-го не хватит, и советует, как успеть', () => {
    const d = base();
    const a = advise(d, classifyAll(d), '2026-10-24');
    const w = a.warnings.find(w => w.level === 'danger')!;
    expect(w.title).toMatch(/Кредит/);
    expect(w.date).toBe('2026-11-05');
    expect(a.safePerDay).toBeLessThan(0);   // даже без трат не хватает до зарплаты
    expect(a.monthlyPayments).toBe(16000);
  });

  it('хватает — говорит, сколько можно тратить в день', () => {
    const d = base();
    d.accounts[0].balance = 40000;
    const a = advise(d, classifyAll(d), '2026-10-24');
    expect(a.warnings[0].level).toBe('ok');
    // самый узкий день — 8.12, накануне декабрьской зарплаты:
    // 40000 + 50000 − 1000 − 15000 − 1000 − 15000 − подушка 1000 = 57000 на 45 дней ≈ 1266 в день
    expect(a.safePerDay).toBe(1266);
    expect(a.safeUntil).toBe('2026-12-08');
    expect(a.warnings.some(w => w.level === 'info' && /сразу отложите/.test(w.title))).toBe(true);
  });

  it('ручная покупка меняет остаток, а потом сверяется с выпиской', () => {
    const d = base();
    d.txs.push({ id: 'm1', accountId: MANUAL_ACCOUNT_ID, date: '2026-10-25', amount: -2500, description: 'Пятёрочка', manual: true, manualCategory: 'Продукты', createdAt: '2026-10-25T10:00' });
    let txs = classifyAll(d);
    expect(advise(d, txs, '2026-10-25').cash.amount).toBe(12000 - 2500);
    // пришла выписка с этой покупкой и новым остатком
    d.txs.push({ id: 'i1', accountId: 'sber:1', date: '2026-10-26', amount: -2500, description: 'PYATEROCHKA 123', bankCategory: 'Супермаркеты' });
    d.accounts[0].balance = 9500; d.accounts[0].balanceDate = '2026-10-26';
    txs = classifyAll(d);
    expect(txs.find(t => t.id === 'm1')!.kind).toBe('matched');
    expect(summarizeMonth(txs, '2026-10').expense).toBe(2500);   // не задвоилось
    expect(advise(d, txs, '2026-10-26').cash.amount).toBe(9500);
  });

  it('отметка «оплачено» убирает платёж из прогноза', () => {
    const d = base();
    d.txs.push({ id: 'p1', accountId: MANUAL_ACCOUNT_ID, date: '2026-10-28', amount: -1000, description: 'Интернет', manual: true, plannedRef: 'net@2026-10-28', createdAt: '2026-10-28T09:00' });
    const a = advise(d, classifyAll(d), '2026-10-28');
    expect(a.upcoming.some(u => u.occ.key === 'net@2026-10-28')).toBe(false);
  });
});
