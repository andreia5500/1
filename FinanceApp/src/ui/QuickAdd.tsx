// Быстрый ручной ввод расхода или дохода
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { useStore, type AddPreset } from '../store';
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES } from '../core/categories';
import { MANUAL_ACCOUNT_ID, type RawTx } from '../core/types';
import { addDays } from '../core/util';
import { Dot, Sheet, num, uid } from './components';

const pad = (n: number) => String(n).padStart(2, '0');

export function QuickAdd({ preset, onClose }: { preset: AddPreset; onClose: () => void }) {
  const { data, txs, update, toast, today } = useStore();
  const editing = preset.editId ? data.txs.find(t => t.id === preset.editId) : undefined;
  const [kind, setKind] = useState<'expense' | 'income'>(editing ? (editing.amount > 0 ? 'income' : 'expense') : preset.kind ?? 'expense');
  const [amount, setAmount] = useState(editing ? String(Math.abs(editing.amount)) : preset.amount ? String(preset.amount) : '');
  const [category, setCategory] = useState(editing?.manualCategory ?? preset.category ?? '');
  const [date, setDate] = useState(editing?.date ?? preset.date ?? today);
  const [note, setNote] = useState(editing ? (editing.description === editing.manualCategory ? '' : editing.description) : preset.note ?? '');
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { setTimeout(() => ref.current?.focus(), 250); }, []);

  // Частые категории наверху: по тому, как вы тратите
  const cats = useMemo(() => {
    const list = kind === 'expense' ? EXPENSE_CATEGORIES : INCOME_CATEGORIES;
    const freq = new Map<string, number>();
    for (const t of txs) if (t.kind === kind) freq.set(t.category, (freq.get(t.category) ?? 0) + 1);
    const hidden = new Set(['Платежи в СберОнлайн', 'Взыскания и долги', 'Пополнения (источник неизвестен)']);
    return list.map(c => c.name).filter(n => !hidden.has(n)).sort((a, b) => (freq.get(b) ?? 0) - (freq.get(a) ?? 0));
  }, [kind, txs]);
  const cat = cats.includes(category) ? category : cats[0];

  const v = num(amount);
  const save = () => {
    if (v <= 0) return;
    const now = new Date();
    const tx: RawTx = {
      id: editing?.id ?? 'm-' + uid(),
      accountId: MANUAL_ACCOUNT_ID,
      date,
      time: editing?.time ?? (date === today ? `${pad(now.getHours())}:${pad(now.getMinutes())}` : undefined),
      amount: kind === 'expense' ? -v : v,
      description: note.trim() || cat,
      manual: true,
      manualCategory: cat,
      plannedRef: editing?.plannedRef ?? preset.plannedRef,
      createdAt: editing?.createdAt ?? now.toISOString(),
    };
    update(d => ({ ...d, txs: editing ? d.txs.map(t => (t.id === tx.id ? tx : t)) : [...d.txs, tx] }));
    toast(editing ? 'Изменено' : kind === 'expense' ? `Расход ${v.toLocaleString('ru-RU')} ₽ записан` : `Доход ${v.toLocaleString('ru-RU')} ₽ записан`);
    onClose();
  };
  const remove = () => {
    update(d => ({ ...d, txs: d.txs.filter(t => t.id !== editing!.id) }));
    toast('Удалено');
    onClose();
  };

  const yest = addDays(today, -1);
  return (
    <Sheet onClose={onClose} title={editing ? 'Ручная операция' : preset.plannedRef ? 'Отметить платёж' : 'Новая запись'}>
      <div class="seg" style={{ marginTop: 6 }}>
        <button class={kind === 'expense' ? 'on' : ''} onClick={() => setKind('expense')}>Расход</button>
        <button class={kind === 'income' ? 'on' : ''} onClick={() => setKind('income')}>Доход</button>
      </div>
      <label class="amount-wrap">
        <input ref={ref} class="amount-in num" inputMode="decimal" placeholder="0" aria-label="Сумма, рублей" value={amount}
          onInput={e => setAmount(e.currentTarget.value.replace(/[^\d.,\s]/g, ''))}
          onKeyDown={e => e.key === 'Enter' && save()} />
        <span>₽</span>
      </label>

      <div class="field"><span>Категория</span>
        <div class="chips wrap">
          {cats.slice(0, 9).map(c => (
            <button key={c} class={'chip' + (c === cat ? ' on' : '')} onClick={() => setCategory(c)}>
              {c !== cat && <Dot category={c} />}{c}
            </button>
          ))}
        </div>
        {cats.length > 9 && (
          <select class="input" style={{ marginTop: 8 }} value={cats.slice(0, 9).includes(cat) ? '' : cat} onChange={e => e.currentTarget.value && setCategory(e.currentTarget.value)} aria-label="Другая категория">
            <option value="">Другая категория…</option>
            {cats.slice(9).map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
      </div>

      <div class="field"><span>Когда</span>
        <div class="chips wrap">
          <button class={'chip' + (date === today ? ' on' : '')} onClick={() => setDate(today)}>Сегодня</button>
          <button class={'chip' + (date === yest ? ' on' : '')} onClick={() => setDate(yest)}>Вчера</button>
          <input class="input" type="date" value={date} max={addDays(today, 60)} onInput={e => e.currentTarget.value && setDate(e.currentTarget.value)} style={{ width: 170, minHeight: 36, padding: '6px 10px' }} aria-label="Дата" />
        </div>
      </div>

      <label class="field"><span>Комментарий, если нужно</span>
        <input class="input" value={note} onInput={e => setNote(e.currentTarget.value)} placeholder={kind === 'expense' ? 'Например: рынок, бензин' : 'Например: подработка'} />
      </label>

      <div class="btns">
        <button class="btn primary wide" disabled={v <= 0} onClick={save}>{editing ? 'Сохранить' : kind === 'expense' ? 'Записать расход' : 'Записать доход'}</button>
        {editing && <button class="btn danger wide" onClick={remove}>Удалить запись</button>}
      </div>
      {!editing && <p class="tiny muted" style={{ marginTop: 10 }}>Если эта покупка потом придёт в выписке банка, приложение узнает её и не посчитает дважды.</p>}
    </Sheet>
  );
}
