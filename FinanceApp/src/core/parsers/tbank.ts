// Разбор выписок Т-Банка «Выписка по договору №…» (дебетовые и кредитные)
import type { Line } from '../pdf';
import type { Account, ParsedStatement, RawTx } from '../types';
import { isMoney, parseMoney, ruDate, round2, sum } from '../util';
import { makeTxIds } from './ids';

export function isTbank(lines: Line[]): boolean {
  const head = lines.slice(0, 40).map(l => l.text).join('\n');
  return /Выписка по договору №\s*\d+/.test(head) && lines.some(l => /^Операции по карте №/.test(l.text) || /Дата и время/.test(l.text));
}

const ROW_DATE = /^(\d{2}\.\d{2}\.\d{2})(?:\s+(\d{2}:\d{2}))?$/;

function moneyRightOf(l: Line, idx: number, maxX = 300): number | null {
  for (let j = idx + 1; j < l.items.length; j++) {
    if (l.items[j].x > maxX) break;
    if (isMoney(l.items[j].s)) return parseMoney(l.items[j].s);
  }
  return null;
}

export function parseTbank(lines: Line[]): ParsedStatement {
  const all = lines.map(l => l.text).join('\n');
  const contract = all.match(/Выписка по договору №\s*(\d+)/)![1];
  const kind = /Кредитный лимит/.test(all) ? 'credit' : 'debit';

  // Балансы (только левая колонка: справа бывают «Баллы Браво»)
  const balances: { date: string; v: number }[] = [];
  let totalIn = 0, totalOut = 0, creditLimit: number | undefined, minPayment: number | undefined, due: string | undefined;
  for (const l of lines) {
    l.items.forEach((it, i) => {
      if (it.x > 150) return;
      const bm = it.s.match(/^Баланс на (\d{2}\.\d{2}\.\d{2,4})$/);
      if (bm) { const v = moneyRightOf(l, i); if (v !== null) balances.push({ date: ruDate(bm[1])!, v }); }
      else if (it.s === 'Поступления') { const v = moneyRightOf(l, i); if (v !== null) totalIn = Math.abs(v); }
      else if (it.s === 'Расходы') { const v = moneyRightOf(l, i); if (v !== null) totalOut = Math.abs(v); }
      else if (it.s === 'Кредитный лимит') { const v = moneyRightOf(l, i); if (v !== null) creditLimit = Math.abs(v); }
      else if (/^Минимальный плат[её]ж$/.test(it.s)) { const v = moneyRightOf(l, i); if (v !== null) minPayment = Math.abs(v); }
      else if (it.s === 'Оплатить до') { const s = l.items[i + 1]?.s; if (s) due = ruDate(s) ?? undefined; }
    });
  }
  const opening = balances[0];
  const closing = balances[balances.length - 1];
  if (!opening || !closing) throw new Error('Т-Банк: не найдены балансы на начало/конец периода');

  const account: Account = {
    id: `tbank:${contract}`,
    bank: 'tbank',
    kind,
    title: `Т-Банк ${kind === 'credit' ? 'кредитная' : 'дебетовая'} №…${contract.slice(-4)}`,
    number: contract,
    cards: [],
  };
  if (kind === 'credit') {
    account.creditLimit = creditLimit;
    account.debt = closing.v < 0 ? -closing.v : 0;
    account.debtDate = closing.date;
    account.minPayment = minPayment;
    account.minPaymentDue = due;
  } else {
    account.balance = closing.v;
    account.balanceDate = closing.date;
  }

  const txs: Omit<RawTx, 'id'>[] = [];
  let card: string | undefined;
  let cur: (Omit<RawTx, 'id'> & { parts: string[] }) | null = null;
  const flush = () => {
    if (!cur) return;
    const { parts, ...rest } = cur;
    txs.push({ ...rest, description: parts.join(' ').replace(/\s+/g, ' ').trim() });
    cur = null;
  };

  for (const l of lines) {
    const cm = l.text.match(/^Операции по карте №\s*\d{4,6}\*+(\d{4})/);
    if (cm) { flush(); card = cm[1]; if (!account.cards.includes(card)) account.cards.push(card); continue; }
    const it = l.items;
    const rm = it[0]?.x < 100 ? it[0].s.match(ROW_DATE) : null;
    if (rm && it[1] && ruDate(it[1].s)) {
      flush();
      const money = it.filter(x => isMoney(x.s));
      if (!money.length) continue;
      const accAmt = money[money.length - 1].s.replace(/\s/g, ''); // сумма в валюте счёта
      const v = Math.abs(parseMoney(accAmt)!);
      cur = {
        accountId: account.id,
        date: ruDate(rm[1])!,
        time: rm[2],
        amount: accAmt.startsWith('+') ? v : -v,
        description: '',
        card,
        parts: it.filter(x => x.x > 180 && x.x < 400 && !isMoney(x.s) && x.s !== '₽').map(x => x.s),
      };
      continue;
    }
    if (cur && it[0] && it[0].x > 180 && it[0].x < 400 && it.every(x => x.x < 400)) {
      cur.parts.push(...it.map(x => x.s));
      continue;
    }
    flush();
  }
  flush();

  const parsedIn = sum(txs.filter(t => t.amount > 0).map(t => t.amount));
  const parsedOut = sum(txs.filter(t => t.amount < 0).map(t => -t.amount));
  return {
    account,
    meta: {
      accountId: account.id,
      periodFrom: opening.date, periodTo: closing.date,
      opening: opening.v, closing: closing.v,
      totalIn: round2(totalIn), totalOut: round2(totalOut),
      parsedIn, parsedOut,
      verified: Math.abs(parsedIn - totalIn) < 0.01 && Math.abs(parsedOut - totalOut) < 0.01,
      txCount: txs.length,
    },
    txs: makeTxIds(txs),
  };
}
