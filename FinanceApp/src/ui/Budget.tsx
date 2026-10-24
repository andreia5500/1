// Бюджет: лимиты по категориям, цели накопления, план погашения долгов
import { useMemo, useState } from 'preact/hooks';
import { useStore } from '../store';
import { goalPlan, limitStates } from '../core/forecast';
import { summarizeMonth } from '../core/analytics';
import { collectDebts, simulatePayoff, type Debt } from '../core/debts';
import { EXPENSE_CATEGORIES } from '../core/categories';
import type { Goal } from '../core/types';
import { addDays, byMonthAfter, fmtDate, monthKey } from '../core/util';
import { Bar, Dot, Money, Sheet, money, num, uid } from './components';

function monthsWord(n: number) {
  const a = n % 10, b = n % 100;
  if (a === 1 && b !== 11) return 'месяц';
  if (a >= 2 && a <= 4 && (b < 12 || b > 14)) return 'месяца';
  return 'месяцев';
}

export function Budget() {
  const { data, txs, today } = useStore();
  const limits = useMemo(() => limitStates(data, txs, today), [data, txs, today]);
  const [limitEdit, setLimitEdit] = useState<string | 'new' | null>(null);
  const [goalEdit, setGoalEdit] = useState<Goal | 'new' | null>(null);

  return (
    <>
      <div class="top"><h1>Бюджет</h1></div>

      <div class="sec-head" style={{ marginTop: 4 }}><h2>Лимиты на месяц</h2><button class="link-btn" onClick={() => setLimitEdit('new')}>Добавить</button></div>
      <section class="card" style={{ padding: '2px 0' }}>
        {!limits.length && <p class="muted" style={{ padding: 16 }}>Поставьте лимит на категорию, где хотите тратить меньше, — например, на маркетплейсы. Приложение предупредит, если в таком темпе вы его превысите.</p>}
        {limits.map(l => (
          <button class="cat" key={l.category} onClick={() => setLimitEdit(l.category)}>
            <div class="head">
              <Dot category={l.category} /><span class="grow">{l.category}</span>
              <span class={'num small ' + (l.status === 'over' ? 'neg' : l.status === 'warn' ? 'warn' : 'muted')}>{money(l.spent)} из {money(l.limit)}</span>
            </div>
            <Bar value={l.spent} max={Math.max(l.limit, l.projected)} marker={l.limit} color={l.status === 'over' ? 'var(--bad)' : l.status === 'warn' ? 'var(--warn)' : 'var(--pos)'} />
            <div class={'tiny ' + (l.status === 'ok' ? 'muted' : l.status === 'over' ? 'neg' : 'warn')} style={{ margin: '7px 0 0 20px' }}>
              {l.status === 'over' ? `Превышен на ${money(l.spent - l.limit)}` : l.status === 'warn' ? `В таком темпе к концу месяца будет ${money(l.projected)} — больше лимита` : `Осталось ${money(l.limit - l.spent)}, в таком темпе к концу месяца ${money(l.projected)}`}
            </div>
          </button>
        ))}
      </section>

      <div class="sec-head"><h2>Цели накопления</h2><button class="link-btn" onClick={() => setGoalEdit('new')}>Добавить</button></div>
      <section class="card" style={{ padding: '2px 0' }}>
        {!data.settings.goals.length && <p class="muted" style={{ padding: 16 }}>Подушка безопасности, отпуск, ремонт — приложение посчитает, сколько откладывать в месяц.</p>}
        {data.settings.goals.map(g => {
          const p = goalPlan(g, today);
          return (
            <button class="cat" key={g.id} onClick={() => setGoalEdit(g)}>
              <div class="head"><span class="grow bold">{g.title}</span><span class="num small muted">{money(g.saved)} из {money(g.target)}</span></div>
              <Bar value={g.saved} max={g.target} color="var(--acc)" flush />
              <div class="tiny muted" style={{ marginTop: 7 }}>
                {p.left <= 0 ? 'Цель достигнута' : g.deadline ? `Осталось ${money(p.left)}: откладывайте ${money(p.perMonth)} в месяц до ${fmtDate(g.deadline)}` : `Осталось ${money(p.left)}. Укажите срок, чтобы посчитать взнос в месяц`}
              </div>
            </button>
          );
        })}
      </section>

      <DebtsSection />

      {limitEdit && <LimitSheet category={limitEdit === 'new' ? null : limitEdit} onClose={() => setLimitEdit(null)} />}
      {goalEdit && <GoalSheet goal={goalEdit === 'new' ? null : goalEdit} onClose={() => setGoalEdit(null)} />}
    </>
  );
}

function DebtsSection() {
  const { data, update, today } = useStore();
  const debts = useMemo(() => collectDebts(data), [data]);
  const total = debts.reduce((s, d) => s + d.debt, 0);
  const minSum = debts.reduce((s, d) => s + d.minPayment, 0);
  const [budgetStr, setBudgetStr] = useState(String(data.settings.debtBudget ?? Math.max(Math.ceil(minSum / 1000) * 1000, 10000)));
  const budget = num(budgetStr);
  const plan = useMemo(() => simulatePayoff(debts, budget), [debts, budget]);
  const faster = useMemo(() => simulatePayoff(debts, budget + 5000), [debts, budget]);
  const [edit, setEdit] = useState<Debt | 'new' | null>(null);
  const account = (id: string) => data.accounts.find(a => a.id === id);
  const saveBudget = (v: string) => { setBudgetStr(v); const n = num(v); if (n > 0) update(d => ({ ...d, settings: { ...d.settings, debtBudget: n } })); };
  const finish = (m: number) => byMonthAfter(today, m);

  return (
    <>
      <div class="sec-head"><h2>Долги</h2><button class="link-btn" onClick={() => setEdit('new')}>Добавить</button></div>
      {!debts.length && <section class="card inner"><p class="muted">Долгов нет — или ещё не загружены выписки по кредитным картам.</p></section>}
      {debts.length > 0 && (
        <section class="card" style={{ padding: '2px 0' }}>
          <div class="row" style={{ alignItems: 'baseline' }}>
            <span class="grow muted small">Общий долг, минимальные платежи ≈ {money(minSum)} в месяц</span>
            <span class="num" style={{ fontSize: 22, fontWeight: 600 }}>{money(total)}</span>
          </div>
          {debts.map(d => {
            const acc = account(d.id);
            const use = d.limit ? d.debt / d.limit : 0;
            return (
              <button class="cat" key={d.id} onClick={() => setEdit(d)}>
                <div class="head"><span class="grow">{d.title}</span><Money v={d.debt} className="bold" /></div>
                {d.limit ? <Bar value={d.debt} max={d.limit} color={use > 0.9 ? 'var(--warn)' : 'var(--ink)'} flush /> : null}
                <div class="tiny muted" style={{ marginTop: 7, lineHeight: 1.5 }}>
                  {d.limit ? `${Math.round(use * 100)}% лимита ${money(d.limit)}; ` : ''}
                  ставка {d.rate ? `${String(d.rate).replace('.', ',')}%` : <span class="warn">не указана — нажмите, чтобы ввести</span>}; мин. платёж {money(d.minPayment)}{acc?.minPaymentDue ? ` до ${fmtDate(acc.minPaymentDue)}` : ''}{acc && !acc.minPayment ? ' (оценка 3%)' : ''}
                  {acc?.debtDate ? `; долг на ${fmtDate(acc.debtDate)}` : ''}{acc?.graceDays ? `; льготный период до ${acc.graceDays} дней` : ''}
                </div>
              </button>
            );
          })}
        </section>
      )}

      {debts.length > 0 && (
        <section class="card inner gap12">
          <h3>План погашения</h3>
          <label class="field"><span>Сколько готовы отдавать на долги в месяц, ₽</span>
            <input class="input num" inputMode="numeric" value={budgetStr} onInput={e => saveBudget(e.currentTarget.value)} />
          </label>
          {budget < minSum && <p class="note bad">Это меньше суммы минимальных платежей ({money(minSum)}) — будут просрочки.</p>}
          {plan.enough && Number.isFinite(plan.months) ? (
            <div class="calc" style={{ marginTop: 10 }}>
              <div class="line"><span>Закроете все долги за</span><b>{plan.months} {monthsWord(plan.months)}</b></div>
              <div class="line"><span>Примерно</span><b>к {finish(plan.months)}</b></div>
              <div class="line"><span>Переплата по процентам, не больше</span><Money v={plan.totalInterest} className="bold" /></div>
              <p class="sub" style={{ marginTop: 4 }}>Порядок: {plan.order.join(', затем ')}. Сначала гасится самый дорогой долг, по остальным — минимальные платежи.</p>
            </div>
          ) : (
            <p class="note bad">При такой сумме долг не уменьшается — увеличьте ежемесячный платёж.</p>
          )}
          {plan.enough && faster.enough && Number.isFinite(faster.months) && faster.months < plan.months && (
            <p class="note">Если платить на 5 000 ₽ больше ({money(budget + 5000)}), закроете на {plan.months - faster.months} {monthsWord(plan.months - faster.months)} раньше и сэкономите {money(plan.totalInterest - faster.totalInterest)} на процентах.</p>
          )}
          <p class="tiny muted" style={{ marginTop: 10 }}>Оценка сверху: проценты считаются на весь остаток каждый месяц. Пока долг гасится в льготный период, процентов может не быть совсем — поэтому вносить больше минимального особенно выгодно.</p>
        </section>
      )}
      {edit && <DebtSheet d={edit === 'new' ? null : edit} onClose={() => setEdit(null)} />}
    </>
  );
}

function LimitSheet({ category, onClose }: { category: string | null; onClose: () => void }) {
  const { data, txs, update, today } = useStore();
  const prevMonth = monthKey(addDays(today.slice(0, 8) + '01', -1));
  const prev = useMemo(() => summarizeMonth(txs, prevMonth), [txs]);
  const cur = useMemo(() => summarizeMonth(txs, monthKey(today)), [txs]);
  const [cat, setCat] = useState(category ?? 'Маркетплейсы');
  const [val, setVal] = useState(String(category ? data.settings.limits[category] ?? '' : ''));
  const ref = prev.byCategory.find(c => c.category === cat)?.amount ?? cur.byCategory.find(c => c.category === cat)?.amount;
  const save = () => {
    const v = num(val);
    update(d => { const limits = { ...d.settings.limits }; if (v > 0) limits[cat] = v; else delete limits[cat]; return { ...d, settings: { ...d.settings, limits } }; });
    onClose();
  };
  const remove = () => { update(d => { const limits = { ...d.settings.limits }; delete limits[cat]; return { ...d, settings: { ...d.settings, limits } }; }); onClose(); };
  return (
    <Sheet onClose={onClose} title={category ? 'Лимит' : 'Новый лимит'}>
      <label class="field"><span>Категория</span>
        <select class="input" value={cat} disabled={!!category} onChange={e => setCat(e.currentTarget.value)}>
          {EXPENSE_CATEGORIES.map(c => <option key={c.name}>{c.name}</option>)}
        </select>
      </label>
      <label class="field"><span>Сколько в месяц, ₽</span>
        <input class="input num" inputMode="numeric" value={val} onInput={e => setVal(e.currentTarget.value)} placeholder={ref ? String(Math.round(ref * 0.8 / 100) * 100) : ''} />
      </label>
      {ref ? <p class="tiny muted" style={{ marginTop: 8 }}>Недавно в этой категории: {money(ref)} за месяц. Для экономии попробуйте на 20% меньше — {money(Math.round(ref * 0.8 / 100) * 100)}.</p> : null}
      <div class="btns">
        <button class="btn primary wide" onClick={save}>Сохранить</button>
        {category && <button class="btn danger wide" onClick={remove}>Удалить лимит</button>}
      </div>
    </Sheet>
  );
}

function GoalSheet({ goal, onClose }: { goal: Goal | null; onClose: () => void }) {
  const { update, today } = useStore();
  const [g, setG] = useState<Goal>(goal ?? { id: uid(), title: '', target: 0, saved: 0 });
  const save = () => {
    if (!g.title.trim() || g.target <= 0) return;
    update(d => ({ ...d, settings: { ...d.settings, goals: [...d.settings.goals.filter(x => x.id !== g.id), g] } }));
    onClose();
  };
  const remove = () => { update(d => ({ ...d, settings: { ...d.settings, goals: d.settings.goals.filter(x => x.id !== g.id) } })); onClose(); };
  const p = goalPlan(g, today);
  return (
    <Sheet onClose={onClose} title={goal ? 'Цель' : 'Новая цель'}>
      <label class="field"><span>Название</span><input class="input" value={g.title} onInput={e => setG({ ...g, title: e.currentTarget.value })} placeholder="Подушка безопасности" /></label>
      <div class="inline">
        <label class="field"><span>Нужно, ₽</span><input class="input num" inputMode="numeric" value={g.target || ''} onInput={e => setG({ ...g, target: num(e.currentTarget.value) })} /></label>
        <label class="field"><span>Уже есть, ₽</span><input class="input num" inputMode="numeric" value={g.saved || ''} onInput={e => setG({ ...g, saved: num(e.currentTarget.value) })} /></label>
      </div>
      <label class="field"><span>К какой дате</span><input class="input" type="date" value={g.deadline ?? ''} onInput={e => setG({ ...g, deadline: e.currentTarget.value || undefined })} /></label>
      {g.deadline && g.target > 0 && <p class="note">Откладывайте {money(p.perMonth)} в месяц ({p.months} мес.).</p>}
      <div class="btns">
        <button class="btn primary wide" onClick={save} disabled={!g.title.trim() || g.target <= 0}>Сохранить</button>
        {goal && <button class="btn danger wide" onClick={remove}>Удалить цель</button>}
      </div>
    </Sheet>
  );
}

function DebtSheet({ d, onClose }: { d: Debt | null; onClose: () => void }) {
  const { data, update } = useStore();
  const fromStatement = d?.fromStatement ?? false;
  const [title, setTitle] = useState(d?.title ?? '');
  const [debt, setDebt] = useState(String(d?.debt ?? ''));
  const [rate, setRate] = useState(d?.rate ? String(d.rate) : '');
  const [minP, setMinP] = useState(String(d?.minPayment ?? ''));
  const save = () => {
    if (fromStatement) {
      update(x => ({ ...x, settings: { ...x.settings, debtOverrides: { ...x.settings.debtOverrides, [d!.id]: { rate: num(rate) || undefined, minPayment: num(minP) || undefined } } } }));
    } else {
      if (!title.trim() || num(debt) <= 0) return;
      const m = { id: d?.id ?? uid(), title, debt: num(debt), rate: num(rate), minPayment: num(minP) };
      update(x => ({ ...x, settings: { ...x.settings, manualDebts: [...x.settings.manualDebts.filter(y => y.id !== m.id), m] } }));
    }
    onClose();
  };
  const remove = () => { update(x => ({ ...x, settings: { ...x.settings, manualDebts: x.settings.manualDebts.filter(y => y.id !== d!.id) } })); onClose(); };
  const acc = d && data.accounts.find(a => a.id === d.id);
  return (
    <Sheet onClose={onClose} title={d ? d.title : 'Новый долг'}>
      {fromStatement
        ? <p class="muted small" style={{ marginTop: 4 }}>Долг {money(d!.debt)} взят из выписки{acc?.debtDate ? ` на ${fmtDate(acc.debtDate)}` : ''}. Обновится, когда загрузите новую выписку.</p>
        : <>
          <label class="field"><span>Название</span><input class="input" value={title} onInput={e => setTitle(e.currentTarget.value)} placeholder="Кредит, рассрочка…" /></label>
          <label class="field"><span>Остаток долга, ₽</span><input class="input num" inputMode="numeric" value={debt} onInput={e => setDebt(e.currentTarget.value)} /></label>
        </>}
      <div class="inline">
        <label class="field"><span>Ставка, % годовых</span><input class="input num" inputMode="decimal" value={rate} onInput={e => setRate(e.currentTarget.value)} placeholder="например, 29,9" /></label>
        <label class="field"><span>Мин. платёж, ₽</span><input class="input num" inputMode="numeric" value={minP} onInput={e => setMinP(e.currentTarget.value)} /></label>
      </div>
      <p class="tiny muted" style={{ marginTop: 8 }}>Ставка указана в договоре или в условиях карты в приложении банка (тарифный план).</p>
      <div class="btns">
        <button class="btn primary wide" onClick={save}>Сохранить</button>
        {d && !fromStatement && <button class="btn danger wide" onClick={remove}>Удалить</button>}
      </div>
    </Sheet>
  );
}
