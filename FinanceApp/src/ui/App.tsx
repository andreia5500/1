import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { StoreCtx, useStore, importFiles, loadData, saveData, type Store, type Tab, type TxFilter, type ImportResult } from '../store';
import { classifyAll } from '../core/classify';
import type { AppData } from '../core/types';
import { onAppResume, takeSharedFiles } from '../platform';
import { Icons, Sheet } from './components';
import { Overview } from './Overview';
import { Transactions } from './Transactions';
import { Plan } from './Plan';
import { Debts } from './Debts';
import { Accounts } from './Accounts';
import { fmtDate } from '../core/util';

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Обзор' },
  { id: 'ops', label: 'Операции' },
  { id: 'plan', label: 'План' },
  { id: 'debts', label: 'Долги' },
  { id: 'accounts', label: 'Выписки' },
];

export function App() {
  const [data, setData] = useState<AppData | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [filter, setFilter] = useState<TxFilter>({});
  const [toastMsg, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<ImportResult | null>(null);
  const dataRef = useRef<AppData | null>(null);
  dataRef.current = data;

  useEffect(() => { loadData().then(setData); }, []);

  const update = (fn: (d: AppData) => AppData) => {
    setData(d => { if (!d) return d; const nd = fn(d); saveData(nd); return nd; });
  };

  const importPdfs = async (files: { name: string; bytes: Uint8Array }[]) => {
    if (!files.length || !dataRef.current) return;
    setBusy(true);
    try {
      const { data: nd, result } = await importFiles(dataRef.current, files);
      setData(nd); await saveData(nd);
      setReport(result);
    } finally { setBusy(false); }
  };

  // PDF, присланные через «Поделиться»
  useEffect(() => {
    if (!data) return;
    const check = async () => { const f = await takeSharedFiles(); if (f.length) importPdfs(f); };
    check();
    onAppResume(check);
  }, [!!data]);

  const toast = (m: string) => { setToast(m); setTimeout(() => setToast(null), 2600); };
  const txs = useMemo(() => (data ? classifyAll(data) : []), [data]);

  if (!data) return <div class="app"><p class="muted" style={{ marginTop: 40 }}>Загрузка…</p></div>;

  const store: Store = {
    data, txs, update, importPdfs, toast,
    go: (t, f) => { setFilter(f ?? {}); setTab(t); window.scrollTo(0, 0); },
  };

  return (
    <StoreCtx.Provider value={store}>
      <div class="app">
        {tab === 'overview' && <Overview />}
        {tab === 'ops' && <Transactions filter={filter} setFilter={setFilter} />}
        {tab === 'plan' && <Plan />}
        {tab === 'debts' && <Debts />}
        {tab === 'accounts' && <Accounts />}
      </div>
      <nav class="tabs">
        {TABS.map(t => (
          <button key={t.id} class={tab === t.id ? 'on' : ''} aria-current={tab === t.id ? 'page' : undefined}
            onClick={() => store.go(t.id)}>
            {Icons[t.id]}<span>{t.label}</span>
          </button>
        ))}
      </nav>
      {busy && <div class="toast">Читаю выписку…</div>}
      {toastMsg && !busy && <div class="toast" role="status">{toastMsg}</div>}
      {report && <ImportReportSheet r={report} onClose={() => setReport(null)} />}
    </StoreCtx.Provider>
  );
}

function ImportReportSheet({ r, onClose }: { r: ImportResult; onClose: () => void }) {
  return (
    <Sheet onClose={onClose}>
      <h2 style={{ marginTop: 0 }}>{r.ok.length ? 'Выписка загружена' : 'Не удалось загрузить'}</h2>
      {r.ok.map(x => (
        <div class="note blue" key={x.statement.id}>
          <b>{x.accountTitle}</b>, {fmtDate(x.statement.periodFrom)} — {fmtDate(x.statement.periodTo)}<br />
          Новых операций: {x.added}{x.duplicates ? `, уже были загружены: ${x.duplicates}` : ''}.<br />
          {x.verified
            ? <span class="pos">Суммы сходятся с итогами выписки.</span>
            : <span class="neg">Суммы не сошлись с итогами выписки: поступления {x.statement.parsedIn} из {x.statement.totalIn}, списания {x.statement.parsedOut} из {x.statement.totalOut}. Проверьте операции этого счёта.</span>}
        </div>
      ))}
      {r.failed.map(f => (
        <div class="note red" key={f.name}><b>{f.name}</b><br />{f.error}</div>
      ))}
      <div class="btns"><button class="btn primary" onClick={onClose}>Готово</button></div>
    </Sheet>
  );
}

/** Кнопка выбора PDF из файлов телефона */
export function ImportButton({ primary, label = 'Загрузить выписку' }: { primary?: boolean; label?: string }) {
  const { importPdfs } = useStore();
  const ref = useRef<HTMLInputElement>(null);
  return (
    <>
      <input ref={ref} type="file" accept="application/pdf,.pdf" multiple hidden
        onChange={async e => {
          const input = e.currentTarget;
          const files = [...(input.files ?? [])];
          input.value = '';
          const read = await Promise.all(files.map(async f => ({ name: f.name, bytes: new Uint8Array(await f.arrayBuffer()) })));
          importPdfs(read);
        }} />
      <button class={'btn' + (primary ? ' primary' : '')} onClick={() => ref.current?.click()}>{label}</button>
    </>
  );
}
