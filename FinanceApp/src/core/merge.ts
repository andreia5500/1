// Добавление разобранной выписки в данные приложения (без дублей)
import type { AppData, ParsedStatement, StatementMeta } from './types';
import { hash } from './util';

export interface ImportReport {
  accountTitle: string;
  period: string;
  added: number;
  duplicates: number;
  verified: boolean;
  replaced: boolean;
  statement: StatementMeta;
}

export function mergeStatement(data: AppData, parsed: ParsedStatement, fileName: string, now = new Date().toISOString()): { data: AppData; report: ImportReport } {
  const accounts = [...data.accounts];
  const idx = accounts.findIndex(a => a.id === parsed.account.id);
  const prevStatements = data.statements.filter(s => s.accountId === parsed.account.id);
  const isNewest = prevStatements.every(s => s.periodTo <= parsed.meta.periodTo);
  if (idx < 0) accounts.push(parsed.account);
  else {
    const old = accounts[idx];
    const cards = [...new Set([...old.cards, ...parsed.account.cards])];
    // свежие остатки/долги берём из самой поздней выписки
    accounts[idx] = isNewest ? { ...old, ...stripUndef(parsed.account), cards } : { ...stripUndef(parsed.account), ...old, cards };
  }

  const existing = new Set(data.txs.map(t => t.id));
  const fresh = parsed.txs.filter(t => !existing.has(t.id));
  const statementId = hash(parsed.account.id + parsed.meta.periodFrom + parsed.meta.periodTo);
  const replaced = data.statements.some(s => s.id === statementId);
  const statement: StatementMeta = { ...parsed.meta, id: statementId, fileName, importedAt: now };
  return {
    data: {
      ...data,
      accounts,
      statements: [...data.statements.filter(s => s.id !== statementId), statement].sort((a, b) => b.periodTo.localeCompare(a.periodTo)),
      txs: [...data.txs, ...fresh],
    },
    report: {
      accountTitle: parsed.account.title,
      period: `${parsed.meta.periodFrom} — ${parsed.meta.periodTo}`,
      added: fresh.length,
      duplicates: parsed.txs.length - fresh.length,
      verified: parsed.meta.verified,
      replaced,
      statement,
    },
  };
}

function stripUndef<T extends object>(o: T): Partial<T> {
  return Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
}

/** Удалить счёт со всеми операциями и выписками */
export function removeAccount(data: AppData, accountId: string): AppData {
  const txIds = new Set(data.txs.filter(t => t.accountId === accountId).map(t => t.id));
  return {
    ...data,
    accounts: data.accounts.filter(a => a.id !== accountId),
    statements: data.statements.filter(s => s.accountId !== accountId),
    txs: data.txs.filter(t => t.accountId !== accountId),
    overrides: Object.fromEntries(Object.entries(data.overrides).filter(([id]) => !txIds.has(id))),
  };
}
