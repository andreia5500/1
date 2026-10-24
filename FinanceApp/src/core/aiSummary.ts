// Обезличенная сводка для ИИ: без ФИО, номеров карт, счетов и телефонов
import type { AppData, ClassifiedTx } from './types';
import { summarizeMonth } from './analytics';
import { collectDebts } from './debts';
import { goalPlan } from './forecast';
import { advise } from './advisor';
import { monthTitle } from './util';

export function scrub(s: string): string {
  return s.replace(/\+?\d[\d\s*-]{5,}\d/g, '[номер]').replace(/[А-ЯЁ]\.\s?[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+(вич|вна)/g, '[ФИО]');
}

export function buildAiSummary(data: AppData, txs: ClassifiedTx[], months: string[], today: string): string {
  const r = (v: number) => Math.round(v).toLocaleString('ru-RU');
  const lines: string[] = [];
  lines.push('Проанализируй мои личные финансы и предложи конкретные шаги, как сократить расходы и быстрее закрыть долги. Данные обезличены.');
  for (const m of months.slice(0, 3)) {
    const s = summarizeMonth(txs, m);
    lines.push('', `## ${monthTitle(m)} (данные по выпискам, месяц может быть неполным)`);
    lines.push(`Доходы: ${r(s.income)} ₽; расходы: ${r(s.expense)} ₽; итог: ${r(s.net)} ₽.`);
    lines.push('Расходы по категориям: ' + s.byCategory.map(c => `${c.category} ${r(c.amount)} ₽ (${c.count} опер.)`).join('; '));
    lines.push('Доходы: ' + s.incomeByCategory.map(c => `${c.category} ${r(c.amount)} ₽`).join('; '));
    lines.push('Крупнейшие получатели: ' + s.topMerchants.slice(0, 6).map(x => `${scrub(x.label).slice(0, 40)} ${r(x.amount)} ₽ (${x.count})`).join('; '));
  }
  const debts = collectDebts(data);
  if (debts.length) {
    lines.push('', '## Долги');
    for (const d of debts) lines.push(`${d.fromStatement ? 'Кредитная карта' : d.title}: долг ${r(d.debt)} ₽, ставка ${d.rate || '?'}% годовых, мин. платёж ${r(d.minPayment)} ₽${d.limit ? `, лимит ${r(d.limit)} ₽` : ''}`);
  }
  if (data.settings.goals.length) {
    lines.push('', '## Цели');
    for (const g of data.settings.goals) { const p = goalPlan(g, today); lines.push(`${scrub(g.title)}: нужно ${r(g.target)} ₽, накоплено ${r(g.saved)} ₽${g.deadline ? `, к ${g.deadline}, нужно ~${r(p.perMonth)} ₽/мес` : ''}`); }
  }
  const a = advise(data, txs, today);
  const pays = data.settings.planned.filter(p => p.enabled && p.type === 'payment');
  if (pays.length) {
    lines.push('', '## Постоянные платежи');
    for (const p of pays) lines.push(`${scrub(p.title)}: ${r(p.amount)} ₽, ${p.day}-го числа${p.period === 'quarter' ? ', раз в квартал' : p.period === 'year' ? ', раз в год' : ''}`);
  }
  lines.push('', `## Прогноз: свободные деньги сейчас ≈ ${r(a.cash.amount)} ₽, повседневные траты ≈ ${r(a.rate)} ₽/день, безопасно тратить ≈ ${r(a.safePerDay)} ₽/день.`);
  for (const w of a.warnings.filter(w => w.level === 'danger' || w.level === 'warn')) lines.push(`Риск: ${scrub(w.title)}`);
  return lines.join('\n');
}
