// Разбор выписок СберБанк Онлайн: «Выписка по счёту дебетовой карты» и «… кредитной карты»
import type { Line } from '../pdf';
import type { Account, ParsedStatement, RawTx } from '../types';
import { isMoney, parseMoney, ruDate, round2, sum } from '../util';
import { makeTxIds } from './ids';

export function isSber(lines: Line[]): boolean {
  const head = lines.slice(0, 40).map(l => l.text).join('\n');
  return /sberbank\.ru|СберБанк Онлайн/i.test(head) && /Выписка по сч[её]ту/i.test(head);
}

/** значение справа от метки в той же строке */
function valueAfter(lines: Line[], label: RegExp, maxX = 9999): string | null {
  for (const l of lines) {
    const i = l.items.findIndex(it => label.test(it.s) && it.x < maxX);
    if (i >= 0 && l.items[i + 1]) return l.items[i + 1].s;
  }
  return null;
}

const FOOTER_RE = /^(Продолжение на следующей|Для проверки подлинности|Дата формирования|ПАО Сбербанк|Выписка по сч[её]ту|ДАТА ОПЕРАЦИИ|Дата обработки|и код авторизации|Страница \d)/i;

export function parseSber(lines: Line[]): ParsedStatement {
  const all = lines.map(l => l.text).join('\n');
  const kind = /Выписка по сч[её]ту кредитной карты/i.test(all) ? 'credit' : 'debit';

  const period = all.match(/За период\s+(\d{2}\.\d{2}\.\d{4})\s*[—–-]\s*(\d{2}\.\d{2}\.\d{4})/);
  if (!period) throw new Error('Сбер: не найден период выписки');
  const periodFrom = ruDate(period[1])!;
  const periodTo = ruDate(period[2])!;

  const number = (valueAfter(lines, /^Номер сч[её]та$/) ?? '').replace(/\s/g, '');
  const cardStr = valueAfter(lines, /^Карта$/) ?? '';
  const card = cardStr.match(/(\d{4})\s*$/)?.[1];

  // Итоги из правой колонки шапки
  let opening: number | undefined, closing: number | undefined;
  let totalIn = 0, totalOut = 0;
  for (const l of lines.slice(0, 60)) {
    for (let i = 0; i < l.items.length; i++) {
      const it = l.items[i];
      const next = l.items[i + 1]?.s ?? '';
      if (/^Остаток на \d{2}\.\d{2}\.\d{4}/.test(it.s) && isMoney(next)) {
        if (opening === undefined) opening = parseMoney(next)!; else closing = parseMoney(next)!;
      } else if (it.s === 'Пополнение' && isMoney(next)) totalIn = parseMoney(next)!;
      else if (it.s === 'Списание' && isMoney(next)) totalOut = Math.abs(parseMoney(next)!);
    }
  }

  const account: Account = {
    id: `sber:${number || card || 'unknown'}`,
    bank: 'sber',
    kind,
    title: `Сбер ${kind === 'credit' ? 'кредитная' : 'дебетовая'}${card ? ' •' + card : ''}`,
    number,
    cards: card ? [card] : [],
  };

  if (kind === 'credit') {
    const lim = valueAfter(lines, /^Кредитный лимит$/);
    if (lim) account.creditLimit = Math.abs(parseMoney(lim.replace('₽', '')) ?? 0) || undefined;
    const rate = valueAfter(lines, /^Процентная ставка$/);
    if (rate) account.rate = Number(rate.replace(',', '.').match(/[\d.]+/)?.[0]);
    const grace = valueAfter(lines, /^Льготный период$/);
    if (grace) account.graceDays = Number(grace.match(/\d+/)?.[0]) || undefined;
    const debt = valueAfter(lines, /^Общая задолженность на$/);
    if (debt) { account.debt = Math.abs(parseMoney(debt.replace('₽', '')) ?? 0); account.debtDate = periodTo; }
  } else if (closing !== undefined) {
    account.balance = closing;
    account.balanceDate = periodTo;
  }

  // Операции: строка 1 — дата, время, категория, сумма, остаток; строка 2 — дата обработки, код, описание; далее — продолжение описания
  const txs: Omit<RawTx, 'id'>[] = [];
  let cur: (Omit<RawTx, 'id'> & { descParts: string[]; stage: number }) | null = null;
  const flush = () => {
    if (!cur) return;
    let d = cur.descParts.join(' ').replace(/\s+/g, ' ').trim();
    const cm = d.match(/\.?\s*Операция по\s+карте\s+\*+(\d{4})\s*$/i);
    if (cm) { cur.card = cm[1]; d = d.slice(0, cm.index).trim(); }
    d = d.replace(/\s*Покупка по СБП в ТСТ другого\s+банка\.*/i, ' (СБП)').replace(/\s+/g, ' ').trim();
    const { descParts: _a, stage: _b, ...rest } = cur;
    txs.push({ ...rest, description: d });
    cur = null;
  };

  for (const l of lines) {
    const it = l.items;
    const d0 = it[0] && ruDate(it[0].s);
    if (d0 && it[1] && /^\d{2}:\d{2}$/.test(it[1].s) && it[0].x < 80) {
      flush();
      const money = it.filter(x => isMoney(x.s));
      const text = it.slice(2).filter(x => !isMoney(x.s)).map(x => x.s).join(' ');
      if (money.length < 1) continue;
      const amtItem = money.length >= 2 ? money[money.length - 2] : money[0];
      const raw = amtItem.s.replace(/\s/g, '');
      const v = Math.abs(parseMoney(raw)!);
      cur = {
        accountId: account.id,
        date: d0,
        time: it[1].s,
        amount: raw.startsWith('+') ? v : -v,
        bankCategory: text,
        description: '',
        descParts: [],
        stage: 1,
      };
      continue;
    }
    if (!cur) continue;
    if (FOOTER_RE.test(l.text)) { flush(); continue; }
    if (cur.stage === 1 && d0 && it[1]) {
      // строка с датой обработки и кодом авторизации
      if (/^\d{4,8}$/.test(it[1].s)) cur.authCode = it[1].s;
      const desc = it.slice(2).filter(x => x.x < 380).map(x => x.s);
      cur.descParts.push(...desc);
      cur.stage = 2;
      continue;
    }
    if (cur.stage === 2 && it[0].x > 120 && it[0].x < 200) {
      cur.descParts.push(...it.filter(x => x.x < 380).map(x => x.s));
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
      periodFrom, periodTo, opening, closing,
      totalIn: round2(totalIn), totalOut: round2(totalOut),
      parsedIn, parsedOut,
      verified: Math.abs(parsedIn - totalIn) < 0.01 && Math.abs(parsedOut - totalOut) < 0.01,
      txCount: txs.length,
    },
    txs: makeTxIds(txs),
  };
}
