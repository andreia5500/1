import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { StoreCtx, useStore, importFiles, loadData, saveData, type AddPreset, type Store, type Tab, type TxFilter, type ImportResult } from '../store';
import { classifyAll } from '../core/classify';
import type { AppData } from '../core/types';
import { onAppResume, takeSharedFiles } from '../platform';
import { syncNotifications } from '../notify';
import { Icons, Sheet } from './components';
import { Overview } from './Overview';
import { Transactions } from './Transactions';
import { Payments } from './Payments';
import { Budget } from './Budget';
import { Accounts } from './Accounts';
import { QuickAdd } from './QuickAdd';
import { fmtDate, todayIso } from '../core/util';

const TABS: { id: Tab; label: string; icon: keyof typeof Icons }[] = [
  { id: 'overview', label: 'Обзор', icon: 'overview' },
  { id: 'ops', label: 'Операции', icon: 'ops' },
  { id: 'payments', label: 'Платежи', icon: 'payments' },
  { id: 'budget', label: 'Бюджет', icon: 'budget' },
  { id: 'accounts', label: 'Выписки', icon: 'accounts' },
];

export function App() {
  const [data, setData] = useState<AppData | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [filter, setFilter] = useState<TxFilter>({});
  const [toastMsg, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<ImportResult | null>(null);
  const [add, setAdd] = useState<AddPreset | null>(null);
  const [today, setToday] = useState(todayIso());
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

  // PDF, присланные через «Поделиться»; при возврате в приложение — обновить «сегодня»
  useEffect(() => {
    if (!data) return;
    const check = async () => { setToday(todayIso()); const f = await takeSharedFiles(); if (f.length) importPdfs(f); };
    check();
    onAppResume(check);
  }, [!!data]);

  const toast = (m: string) => { setToast(m); setTimeout(() => setToast(null), 2800); };
  const txs = useMemo(() => (data ? classifyAll(data) : []), [data]);

  // Напоминания о платежах пересчитываются при каждом изменении данных
  useEffect(() => {
    if (!data) return;
    const t = setTimeout(() => { syncNotifications(data, txs, today).catch(() => {}); }, 1500);
    return () => clearTimeout(t);
  }, [data, txs, today]);

  if (!data) return <div class="app"><p class="muted pad" style={{ marginTop: 40 }}>Загрузка…</p></div>;

  const store: Store = {
    data, txs, update, importPdfs, toast, today,
    go: (t, f) => { setFilter(f ?? {}); setTab(t); window.scrollTo(0, 0); },
    openAdd: p => setAdd(p ?? {}),
  };
  const showFab = tab === 'overview' || tab === 'ops' || tab === 'payments';

  return (
    <StoreCtx.Provider value={store}>
      <div class="app">
        {tab === 'overview' && <Overview />}
        {tab === 'ops' && <Transactions filter={filter} setFilter={setFilter} />}
        {tab === 'payments' && <Payments />}
        {tab === 'budget' && <Budget />}
        {tab === 'accounts' && <Accounts />}
      </div>
      {showFab && (
        <button class="fab" aria-label="Добавить расход или доход" onClick={() => setAdd({})}>{Icons.plus}</button>
      )}
      <nav class="tabs" aria-label="Разделы">
        <div class="in">
          {TABS.map(t => (
            <button key={t.id} class={tab === t.id ? 'on' : ''} aria-current={tab === t.id ? 'page' : undefined} onClick={() => store.go(t.id)}>
              <span class="pill">{Icons[t.icon]}</span><span>{t.label}</span>
            </button>
          ))}
        </div>
      </nav>
      {busy && <div class="toast">Читаю выписку…</div>}
      {toastMsg && !busy && <div class="toast" role="status">{toastMsg}</div>}
      {report && <ImportReportSheet r={report} onClose={() => setReport(null)} />}
      {add && <QuickAdd preset={add} onClose={() => setAdd(null)} />}
    </StoreCtx.Provider>
  );
}

function ImportReportSheet({ r, onClose }: { r: ImportResult; onClose: () => void }) {
  return (
    <Sheet onClose={onClose} title={r.ok.length ? 'Выписка загружена' : 'Не удалось загрузить'}>
      {r.ok.map(x => (
        <div class={'note ' + (x.verified ? 'ok' : 'bad')} key={x.statement.id}>
          <b>{x.accountTitle}</b>, {fmtDate(x.statement.periodFrom)} — {fmtDate(x.statement.periodTo)}<br />
          Новых операций: {x.added}{x.duplicates ? `, уже были загружены: ${x.duplicates}` : ''}.<br />
          {x.verified
            ? 'Суммы сходятся с итогами выписки.'
            : `Суммы не сошлись с итогами выписки: поступления ${x.statement.parsedIn} из ${x.statement.totalIn}, списания ${x.statement.parsedOut} из ${x.statement.totalOut}. Проверьте операции этого счёта.`}
        </div>
      ))}
      {r.failed.map(f => (
        <div class="note bad" key={f.name}><b>{f.name}</b><br />{f.error}</div>
      ))}
      <div class="btns"><button class="btn primary" onClick={onClose}>Готово</button></div>
    </Sheet>
  );
}

/** Кнопка выбора PDF из файлов телефона */
export function ImportButton({ primary, label = 'Загрузить выписку', round }: { primary?: boolean; label?: string; round?: boolean }) {
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
      {round
        ? <button class="icon-btn round" aria-label={label} onClick={() => ref.current?.click()}>{Icons.upload}</button>
        : <button class={'btn' + (primary ? ' primary' : '')} onClick={() => ref.current?.click()}>{label}</button>}
    </>
  );
}
