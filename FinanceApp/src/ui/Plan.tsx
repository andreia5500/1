import { useMemo, useState } from 'preact/hooks';
import { useStore } from '../store';
import { forecastMonth, goalPlan, limitStates } from '../core/forecast';
import { summarizeMonth } from '../core/analytics';
import { EXPENSE_CATEGORIES } from '../core/categories';
import type { Goal, Planned } from '../core/types';
import { addDays, fmtDate, monthKey, todayIso } from '../core/util';
import { Bar, Dot, Money, Sheet, money } from './components';

const uid = () => Math.random().toString(36).slice(2, 10);

export function Plan() {
  const { data, txs } = useStore();
  const today = todayIso();
  const f = useMemo(() => forecastMonth(data, txs, today), [data, txs]);
  const limits = useMemo(() => limitStates(data, txs, today), [data, txs]);
  const [limitEdit, setLimitEdit] = useState<string | null | 'new'>(null);
  const [goalEdit, setGoalEdit] = useState<Goal | 'new' | null>(null);
  const [plEdit, setPlEdit] = useState<Planned | 'new' | null>(null);

  return (
    <>
      <div class="top"><h1>План</h1></div>

      <h2 style={{ marginTop: 8 }}>Сколько останется к концу месяца</h2>
      <div class="rows calc" style={{ padding: '6px 10px' }}>
        <div class="line"><span>Деньги на дебетовых картах</span><Money v={f.cashNow} /></div>
        {f.cashNowNote.map(n => <div class="sub" key={n}>{n}</div>)}
        {f.plannedIncome.map(x => <div class="line" key={x.p.id}><span>+ {x.p.title}, {fmtDate(x.date).slice(0, 5)}</span><Money v={x.p.amount} className="pos" /></div>)}
        {f.plannedPayments.map(x => <div class="line" key={x.p.id}><span>− {x.p.title}, {fmtDate(x.date).slice(0, 5)}</span><Money v={-x.p.amount} /></div>)}
        <div class="line"><span>− Повседневные траты: {money(f.dailyEveryday)} × {f.daysLeft} дн.</span><Money v={-f.everydayRest} /></div>
        <div class="line total"><span>Останется</span><Money v={f.endBalance} className={f.endBalance < 0 ? 'neg' : ''} /></div>
        {f.goalMonthly > 0 && <>
          <div class="line"><span>− Отложить на цели</span><Money v={-f.goalMonthly} /></div>
          <div class="line total"><span>Свободно после целей</span><Money v={f.freeAfterGoals} className={f.freeAfterGoals < 0 ? 'neg' : 'pos'} /></div>
        </>}
      </div>
      <p class="faint" style={{ marginTop: 6 }}>Повседневные — продукты, маркетплейсы, транспорт, аптеки, кафе, наличные и прочее; среднее за последние 45 дней. Остатки берутся из последних загруженных выписок.</p>

      <h2>Лимиты на месяц</h2>
      <div class="rows" style={{ paddingInline: 8 }}>
        {!limits.length && <p class="muted" style={{ padding: '10px 2px' }}>Поставьте лимит на категорию, где хотите тратить меньше, — например, маркетплейсы.</p>}
        {limits.map(l => (
          <button class="cat" key={l.category} onClick={() => setLimitEdit(l.category)}>
            <div class="head"><Dot category={l.category} /><span class="grow">{l.category}</span>
              <span class={'num ' + (l.status === 'over' ? 'neg' : l.status === 'warn' ? 'warn' : '')}>{money(l.spent)} из {money(l.limit)}</span></div>
            <Bar value={l.spent} max={Math.max(l.limit, l.projected)} marker={l.limit} color={l.status === 'over' ? 'var(--red)' : l.status === 'warn' ? 'var(--amber)' : 'var(--green)'} />
            <div class="faint" style={{ marginTop: 3 }}>
              {l.status === 'over' ? `Превышен на ${money(l.spent - l.limit)}` : l.status === 'warn' ? `В таком темпе к концу месяца будет ${money(l.projected)} — больше лимита` : `В таком темпе к концу месяца ${money(l.projected)}`}
            </div>
          </button>
        ))}
      </div>
      <div class="btns"><button class="btn small" onClick={() => setLimitEdit('new')}>Добавить лимит</button></div>

      <h2>Цели накопления</h2>
      <div class="rows" style={{ paddingInline: 8 }}>
        {!data.settings.goals.length && <p class="muted" style={{ padding: '10px 2px' }}>Например: подушка безопасности, отпуск, ремонт.</p>}
        {data.settings.goals.map(g => {
          const p = goalPlan(g, today);
          return (
            <button class="cat" key={g.id} onClick={() => setGoalEdit(g)}>
              <div class="head"><span class="grow"><b>{g.title}</b></span><span class="num">{money(g.saved)} из {money(g.target)}</span></div>
              <Bar value={g.saved} max={g.target} color="var(--blue)" />
              <div class="faint" style={{ marginTop: 3 }}>
                {p.left <= 0 ? 'Цель достигнута' : g.deadline ? `Осталось ${money(p.left)}: откладывайте ${money(p.perMonth)} в месяц до ${fmtDate(g.deadline)}` : `Осталось ${money(p.left)}. Укажите срок, чтобы посчитать взнос в месяц`}
              </div>
            </button>
          );
        })}
      </div>
      <div class="btns"><button class="btn small" onClick={() => setGoalEdit('new')}>Добавить цель</button></div>

      <h2>Регулярные поступления и платежи</h2>
      <p class="faint">Найдены автоматически по выпискам. Используются в прогнозе — проверьте суммы и дни.</p>
      <div class="rows" style={{ paddingInline: 8 }}>
        {data.settings.planned.map(p => (
          <button class="row" key={p.id} onClick={() => setPlEdit(p)} style={{ opacity: p.enabled ? 1 : 0.5 }}>
            <div class="grow"><div class="title">{p.title}</div><div class="meta">{p.type === 'income' ? 'поступление' : 'платёж'}, {p.day}-го числа{p.enabled ? '' : ', не учитывается'}</div></div>
            <Money v={p.type === 'income' ? p.amount : -p.amount} className={p.type === 'income' ? 'pos' : ''} />
          </button>
        ))}
      </div>
      <div class="btns"><button class="btn small" onClick={() => setPlEdit('new')}>Добавить</button></div>

      {limitEdit && <LimitSheet category={limitEdit === 'new' ? null : limitEdit} onClose={() => setLimitEdit(null)} />}
      {goalEdit && <GoalSheet goal={goalEdit === 'new' ? null : goalEdit} onClose={() => setGoalEdit(null)} />}
      {plEdit && <PlannedSheet p={plEdit === 'new' ? null : plEdit} onClose={() => setPlEdit(null)} />}
    </>
  );
}

function LimitSheet({ category, onClose }: { category: string | null; onClose: () => void }) {
  const { data, txs, update } = useStore();
  const today = todayIso();
  // подсказка: сколько было потрачено в прошлом полном месяце
  const prevMonth = monthKey(addDays(today.slice(0, 8) + '01', -1));
  const prev = useMemo(() => summarizeMonth(txs, prevMonth), [txs]);
  const cur = useMemo(() => summarizeMonth(txs, monthKey(today)), [txs]);
  const [cat, setCat] = useState(category ?? EXPENSE_CATEGORIES[1].name);
  const [val, setVal] = useState(String(category ? data.settings.limits[category] ?? '' : ''));
  const ref = prev.byCategory.find(c => c.category === cat)?.amount ?? cur.byCategory.find(c => c.category === cat)?.amount;
  const save = () => {
    const v = Number(val.replace(/\s/g, '').replace(',', '.'));
    update(d => { const limits = { ...d.settings.limits }; if (category && category !== cat) delete limits[category]; if (v > 0) limits[cat] = v; else delete limits[cat]; return { ...d, settings: { ...d.settings, limits } }; });
    onClose();
  };
  const remove = () => { update(d => { const limits = { ...d.settings.limits }; delete limits[cat]; return { ...d, settings: { ...d.settings, limits } }; }); onClose(); };
  return (
    <Sheet onClose={onClose}>
      <h2 style={{ marginTop: 0 }}>{category ? 'Лимит' : 'Новый лимит'}</h2>
      <label class="field"><span>Категория</span>
        <select class="input" value={cat} disabled={!!category} onChange={e => setCat(e.currentTarget.value)}>
          {EXPENSE_CATEGORIES.map(c => <option key={c.name}>{c.name}</option>)}
        </select>
      </label>
      <label class="field"><span>Сколько в месяц, ₽</span>
        <input class="input" inputMode="numeric" value={val} onInput={e => setVal(e.currentTarget.value)} placeholder={ref ? String(Math.round(ref * 0.8 / 100) * 100) : ''} />
      </label>
      {ref ? <p class="faint" style={{ marginTop: 6 }}>Недавно в этой категории: {money(ref)} за месяц. Для экономии попробуйте на 20% меньше — {money(Math.round(ref * 0.8 / 100) * 100)}.</p> : null}
      <div class="btns">
        <button class="btn primary" onClick={save}>Сохранить</button>
        {category && <button class="btn danger" onClick={remove}>Удалить лимит</button>}
      </div>
    </Sheet>
  );
}

function GoalSheet({ goal, onClose }: { goal: Goal | null; onClose: () => void }) {
  const { update } = useStore();
  const [g, setG] = useState<Goal>(goal ?? { id: uid(), title: '', target: 0, saved: 0 });
  const num = (s: string) => Number(s.replace(/\s/g, '').replace(',', '.')) || 0;
  const save = () => {
    if (!g.title.trim() || g.target <= 0) return;
    update(d => ({ ...d, settings: { ...d.settings, goals: [...d.settings.goals.filter(x => x.id !== g.id), g] } }));
    onClose();
  };
  const remove = () => { update(d => ({ ...d, settings: { ...d.settings, goals: d.settings.goals.filter(x => x.id !== g.id) } })); onClose(); };
  const p = goalPlan(g, todayIso());
  return (
    <Sheet onClose={onClose}>
      <h2 style={{ marginTop: 0 }}>{goal ? 'Цель' : 'Новая цель'}</h2>
      <label class="field"><span>Название</span><input class="input" value={g.title} onInput={e => setG({ ...g, title: e.currentTarget.value })} placeholder="Подушка безопасности" /></label>
      <div class="inline">
        <label class="field"><span>Нужно, ₽</span><input class="input" inputMode="numeric" value={g.target || ''} onInput={e => setG({ ...g, target: num(e.currentTarget.value) })} /></label>
        <label class="field"><span>Уже есть, ₽</span><input class="input" inputMode="numeric" value={g.saved || ''} onInput={e => setG({ ...g, saved: num(e.currentTarget.value) })} /></label>
      </div>
      <label class="field"><span>К какой дате</span><input class="input" type="date" value={g.deadline ?? ''} onInput={e => setG({ ...g, deadline: e.currentTarget.value || undefined })} /></label>
      {g.deadline && g.target > 0 && <p class="note blue">Откладывайте {money(p.perMonth)} в месяц ({p.months} мес.).</p>}
      <div class="btns">
        <button class="btn primary" onClick={save} disabled={!g.title.trim() || g.target <= 0}>Сохранить</button>
        {goal && <button class="btn danger" onClick={remove}>Удалить цель</button>}
      </div>
    </Sheet>
  );
}

function PlannedSheet({ p, onClose }: { p: Planned | null; onClose: () => void }) {
  const { update } = useStore();
  const [x, setX] = useState<Planned>(p ?? { id: uid(), title: '', type: 'payment', amount: 0, day: 1, enabled: true });
  const num = (s: string) => Number(s.replace(/\s/g, '').replace(',', '.')) || 0;
  const save = () => {
    if (!x.title.trim() || x.amount <= 0) return;
    update(d => ({ ...d, settings: { ...d.settings, planned: [...d.settings.planned.filter(y => y.id !== x.id), { ...x, day: Math.min(31, Math.max(1, x.day)) }] } }));
    onClose();
  };
  const remove = () => {
    update(d => ({ ...d, settings: { ...d.settings, planned: d.settings.planned.filter(y => y.id !== x.id), plannedDismissed: x.key ? [...d.settings.plannedDismissed, x.key] : d.settings.plannedDismissed } }));
    onClose();
  };
  return (
    <Sheet onClose={onClose}>
      <h2 style={{ marginTop: 0 }}>{p ? 'Регулярная операция' : 'Новая регулярная операция'}</h2>
      <div class="field"><span>Тип</span>
        <div class="seg" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <button class={x.type === 'income' ? 'on' : ''} onClick={() => setX({ ...x, type: 'income' })}>Поступление</button>
          <button class={x.type === 'payment' ? 'on' : ''} onClick={() => setX({ ...x, type: 'payment' })}>Платёж</button>
        </div>
      </div>
      <label class="field"><span>Название</span><input class="input" value={x.title} onInput={e => setX({ ...x, title: e.currentTarget.value })} placeholder="Ипотека, садик, кружок…" /></label>
      <div class="inline">
        <label class="field"><span>Сумма, ₽</span><input class="input" inputMode="numeric" value={x.amount || ''} onInput={e => setX({ ...x, amount: num(e.currentTarget.value) })} /></label>
        <label class="field"><span>Число месяца</span><input class="input" inputMode="numeric" value={x.day} onInput={e => setX({ ...x, day: num(e.currentTarget.value) })} /></label>
      </div>
      <label class="check"><input type="checkbox" checked={x.enabled} onChange={e => setX({ ...x, enabled: e.currentTarget.checked })} /><span>Учитывать в прогнозе</span></label>
      <div class="btns">
        <button class="btn primary" onClick={save} disabled={!x.title.trim() || x.amount <= 0}>Сохранить</button>
        {p && <button class="btn danger" onClick={remove}>Удалить</button>}
      </div>
    </Sheet>
  );
}
