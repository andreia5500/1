import { useMemo, useState } from 'preact/hooks';
import { useStore, type TxFilter } from '../store';
import type { ClassifiedTx, TxKind } from '../core/types';
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES, TRANSFER_CATEGORY } from '../core/categories';
import { prettyName } from '../core/classify';
import { dayTitle, fmtDate, monthKey, monthTitle } from '../core/util';
import { Dot, Icons, Money, Sheet } from './components';

const KINDS: { id: TxFilter['kind'] | undefined; label: string }[] = [
  { id: undefined, label: 'Все' },
  { id: 'expense', label: 'Расходы' },
  { id: 'income', label: 'Доходы' },
  { id: 'transfer', label: 'Свои переводы' },
  { id: 'review', label: 'Проверить' },
];

export function Transactions({ filter, setFilter }: { filter: TxFilter; setFilter: (f: TxFilter) => void }) {
  const { txs, data } = useStore();
  const [q, setQ] = useState('');
  const [edit, setEdit] = useState<ClassifiedTx | null>(null);
  const accTitle = useMemo(() => new Map(data.accounts.map(a => [a.id, a.title])), [data.accounts]);

  const list = useMemo(() => txs.filter(t => {
    if (filter.month && monthKey(t.date) !== filter.month) return false;
    if (filter.category && t.category !== filter.category) return false;
    if (filter.kind === 'review' && !t.needsReview) return false;
    if (filter.kind === 'expense' && t.kind !== 'expense' && t.kind !== 'refund') return false;
    if (filter.kind === 'income' && t.kind !== 'income') return false;
    if (filter.kind === 'transfer' && t.kind !== 'transfer') return false;
    if (q && !(t.description + ' ' + t.category).toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  }), [txs, filter, q]);

  const groups = useMemo(() => {
    const g = new Map<string, ClassifiedTx[]>();
    for (const t of list.slice(0, 600)) g.set(t.date, [...(g.get(t.date) ?? []), t]);
    return [...g.entries()];
  }, [list]);

  return (
    <>
      <div class="top"><h1>Операции</h1></div>
      <div class="chips" role="tablist">
        {KINDS.map(k => (
          <button key={k.label} class={'chip' + (filter.kind === k.id ? ' on' : '')} onClick={() => setFilter({ ...filter, kind: k.id })}>{k.label}</button>
        ))}
      </div>
      {(filter.category || filter.month) && (
        <div class="chips">
          {filter.month && <button class="chip on" onClick={() => setFilter({ ...filter, month: undefined })}>{monthTitle(filter.month)} ✕</button>}
          {filter.category && <button class="chip on" onClick={() => setFilter({ ...filter, category: undefined })}>{filter.category} ✕</button>}
        </div>
      )}
      <input class="input" type="search" placeholder="Поиск по описанию" value={q} onInput={e => setQ(e.currentTarget.value)} />
      {filter.kind === 'review' && list.length > 0 && (
        <p class="note">По этим операциям из выписки не понять, что это: трата, перевод себе или за что платёж. Нажмите на операцию и уточните.</p>
      )}
      {!list.length && <p class="muted" style={{ marginTop: 16 }}>Ничего не найдено.</p>}
      {groups.map(([date, items]) => (
        <div key={date}>
          <div class="day-head"><span>{dayTitle(date)}</span></div>
          <div class="rows" style={{ paddingInline: 8 }}>
            {items.map(t => (
              <button class="row" key={t.id} onClick={() => setEdit(t)}>
                <Dot category={t.category} />
                <div class="grow">
                  <div class="title">{prettyName(t.description)}</div>
                  <div class="meta">
                    {t.needsReview && <span class="warn">уточнить · </span>}
                    {t.kind === 'transfer' ? (t.transferNote ?? TRANSFER_CATEGORY) : t.category}{t.kind === 'refund' ? ', возврат' : ''} · {accTitle.get(t.accountId)}
                  </div>
                </div>
                <Money v={t.amount} sign className={t.kind === 'transfer' ? 'muted' : t.amount > 0 ? 'pos' : ''} />
              </button>
            ))}
          </div>
        </div>
      ))}
      {edit && <EditTx t={edit} onClose={() => setEdit(null)} accountTitle={accTitle.get(edit.accountId) ?? ''} />}
    </>
  );
}

const KIND_LABEL: [TxKind, string][] = [['expense', 'Расход'], ['income', 'Доход'], ['transfer', 'Перевод себе'], ['refund', 'Возврат']];

function EditTx({ t, onClose, accountTitle }: { t: ClassifiedTx; onClose: () => void; accountTitle: string }) {
  const { txs, update, toast } = useStore();
  const [kind, setKind] = useState<TxKind>(t.kind);
  const [category, setCategory] = useState(t.category);
  const similar = txs.filter(x => x.merchant === t.merchant && x.id !== t.id).length;
  const [all, setAll] = useState(false);
  const cats = kind === 'income' ? INCOME_CATEGORIES : kind === 'transfer' ? [] : EXPENSE_CATEGORIES;

  const save = () => {
    const cat = kind === 'transfer' ? TRANSFER_CATEGORY : (cats.some(c => c.name === category) ? category : cats[0].name);
    update(d => {
      if (all) {
        const rules = d.rules.filter(r => r.merchant !== t.merchant);
        rules.push({ merchant: t.merchant, category: cat, kind });
        const overrides = { ...d.overrides }; delete overrides[t.id];
        return { ...d, rules, overrides };
      }
      return { ...d, overrides: { ...d.overrides, [t.id]: { kind, category: cat } } };
    });
    toast(all ? `Сохранено для ${similar + 1} похожих операций` : 'Сохранено');
    onClose();
  };
  const reset = () => {
    update(d => {
      const overrides = { ...d.overrides }; delete overrides[t.id];
      return { ...d, overrides, rules: d.rules.filter(r => r.merchant !== t.merchant) };
    });
    toast('Вернул автоматическую категорию');
    onClose();
  };

  return (
    <Sheet onClose={onClose}>
      <div class="top" style={{ minHeight: 0 }}>
        <h2 style={{ margin: 0, flex: 1 }}><Money v={t.amount} sign className={t.amount > 0 ? 'pos' : ''} /></h2>
        <button class="icon-btn" aria-label="Закрыть" onClick={onClose}>{Icons.close}</button>
      </div>
      <p style={{ marginTop: 6 }}>{t.description}</p>
      <p class="faint">{fmtDate(t.date)}{t.time ? ' ' + t.time : ''} · {accountTitle}{t.bankCategory ? ` · в выписке: «${t.bankCategory}»` : ''}</p>
      {t.transferNote && <p class="note blue">{t.transferNote}</p>}
      {t.needsReview && (t.category === 'Платежи в СберОнлайн'
        ? <p class="note">В выписке не сказано, за что этот платёж из СберБанк Онлайн. Посмотрите его в истории операций банка и выберите категорию — с галочкой ниже похожие платежи разнесутся сами.</p>
        : <p class="note">По выписке не понять, кому ушли или откуда пришли эти деньги. Если это ваш собственный счёт — выберите «Перевод себе», тогда сумма не попадёт в доходы и расходы.</p>)}

      <div class="field"><span>Что это</span>
        <div class="seg">
          {KIND_LABEL.map(([k, l]) => <button key={k} class={kind === k ? 'on' : ''} onClick={() => setKind(k)}>{l}</button>)}
        </div>
      </div>
      {kind !== 'transfer' && (
        <label class="field"><span>Категория</span>
          <select class="input" value={category} onChange={e => setCategory(e.currentTarget.value)}>
            {!cats.some(c => c.name === category) && <option value={category}>{category}</option>}
            {cats.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
        </label>
      )}
      {similar > 0 && (
        <label class="check">
          <input type="checkbox" checked={all} onChange={e => setAll(e.currentTarget.checked)} />
          <span>Применить ко всем похожим операциям ({similar} шт.) и к будущим выпискам</span>
        </label>
      )}
      <div class="btns">
        <button class="btn primary" onClick={save}>Сохранить</button>
        {t.overridden && <button class="btn" onClick={reset}>Сбросить</button>}
      </div>
    </Sheet>
  );
}
