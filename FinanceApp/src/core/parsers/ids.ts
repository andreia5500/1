import type { RawTx } from '../types';
import { hash } from '../util';

/** Стабильные id операций: одинаковая операция из пересекающихся выписок получает тот же id */
export function makeTxIds(txs: Omit<RawTx, 'id'>[]): RawTx[] {
  const seen = new Map<string, number>();
  return txs.map(t => {
    const base = [t.accountId, t.date, t.time ?? '', t.amount.toFixed(2), t.description.toLowerCase().replace(/\s+/g, '')].join('|');
    const n = seen.get(base) ?? 0;
    seen.set(base, n + 1);
    return { ...t, id: hash(base) + '-' + n };
  });
}
