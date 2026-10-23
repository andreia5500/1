// Хранилище: все данные лежат только на телефоне (IndexedDB внутри приложения)
import { get, set, del } from 'idb-keyval';
import { createContext } from 'preact';
import { useContext } from 'preact/hooks';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';
import { emptyData, type AppData, type ClassifiedTx } from './core/types';
import { parseStatementPdf } from './core/parsers';
import { mergeStatement, type ImportReport } from './core/merge';
import { classifyAll } from './core/classify';
import { suggestPlanned } from './core/analytics';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

const KEY = 'finance-data-v1';

export async function loadData(): Promise<AppData> {
  const d = (await get(KEY)) as AppData | undefined;
  if (!d) return emptyData();
  const e = emptyData();
  return { ...e, ...d, settings: { ...e.settings, ...d.settings } };
}

export async function saveData(d: AppData) { await set(KEY, d); }
export async function wipeData() { await del(KEY); }

export interface ImportResult { ok: ImportReport[]; failed: { name: string; error: string }[] }

export async function importFiles(data: AppData, files: { name: string; bytes: Uint8Array }[]): Promise<{ data: AppData; result: ImportResult }> {
  let d = data;
  const result: ImportResult = { ok: [], failed: [] };
  for (const f of files) {
    try {
      const parsed = await parseStatementPdf(pdfjs as any, f.bytes);
      const r = mergeStatement(d, parsed, f.name);
      d = r.data;
      result.ok.push(r.report);
    } catch (e: any) {
      result.failed.push({ name: f.name, error: e?.message ?? String(e) });
    }
  }
  if (result.ok.length) {
    // автоматически добавляем найденные регулярные доходы и платежи в план
    const sugg = suggestPlanned(d, classifyAll(d));
    if (sugg.length) d = { ...d, settings: { ...d.settings, planned: [...d.settings.planned, ...sugg] } };
  }
  return { data: d, result };
}

export function isAppData(x: any): x is AppData {
  return x && x.version === 1 && Array.isArray(x.accounts) && Array.isArray(x.txs) && x.settings;
}

export interface Store {
  data: AppData;
  txs: ClassifiedTx[];
  update: (fn: (d: AppData) => AppData) => void;
  importPdfs: (files: { name: string; bytes: Uint8Array }[]) => Promise<void>;
  go: (tab: Tab, filter?: TxFilter) => void;
  toast: (msg: string) => void;
}

export type Tab = 'overview' | 'ops' | 'plan' | 'debts' | 'accounts';
export interface TxFilter { kind?: 'expense' | 'income' | 'transfer' | 'review'; category?: string; month?: string }

export const StoreCtx = createContext<Store>(null as any);
export const useStore = () => useContext(StoreCtx);
