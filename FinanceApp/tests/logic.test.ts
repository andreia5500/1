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
