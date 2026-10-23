import { useMemo, useState } from 'preact/hooks';
import { useStore } from '../store';
import { collectDebts, simulatePayoff, type Debt } from '../core/debts';
import { fmtDate, todayIso } from '../core/util';
import { Bar, Money, Sheet, money } from './components';

const uid = () => Math.random().toString(36).slice(2, 10);

function monthsWord(n: number) {
  const a = n % 10, b = n % 100;
  if (a === 1 && b !== 11) return 'месяц';
  if (a >= 2 && a <= 4 && (b < 12 || b > 14)) return 'месяца';
  return 'месяцев';
}

export function Debts() {
  const { data, update } = useStore();
  const debts = useMemo(() => collectDebts(data), [data]);
  const total = debts.reduce((s, d) => s + d.debt, 0);
  const minSum = debts.reduce((s, d) => s + d.minPayment, 0);
  const [budgetStr, setBudgetStr] = useState(String(data.settings.debtBudget ?? Math.max(Math.ceil(minSum / 1000) * 1000, 10000)));
  const budget = Number(budgetStr.replace(/\s/g, '')) || 0;
  const plan = useMemo(() => simulatePayoff(debts, budget), [debts, budget]);
  const faster = useMemo(() => simulatePayoff(debts, budget + 5000), [debts, budget]);
  const [edit, setEdit] = useState<Debt | 'new' | null>(null);
  const account = (id: string) => data.accounts.find(a => a.id === id);

  const saveBudget = (v: string) => { setBudgetStr(v); const n = Number(v.replace(/\s/g, '')); if (n > 0) update(d => ({ ...d, settings: { ...d.settings, debtBudget: n } })); };
  const finish = (m: number) => { const d = new Date(todayIso()); d.setMonth(d.getMonth() + m); return d.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' }); };

  return (
    <>
      <div class="top"><h1>Долги</h1></div>
      {!debts.length && <p class="muted">Долгов нет — либо ещё не загружены выписки по кредитным картам.</p>}
      {debts.length > 0 && (
        <div class="stamp">
          <div class="main"><div class="lbl">Общий долг</div><div class="val neg">{money(total)}</div>
            <div class="sub">минимальные платежи ≈ {money(minSum)} в месяц</div></div>
        </div>
      )}

      {debts.map(d => {
        const acc = account(d.id);
        return (
          <button class="cat rows" style={{ marginTop: 10, padding: '10px 10px 12px' }} key={d.id} onClick={() => setEdit(d)}>
            <div class="head"><span class="grow"><b>{d.title}</b></span><Money v={d.debt} className="neg" /></div>
            {d.limit ? <><Bar value={d.debt} max={d.limit} color="var(--red)" /><div class="faint" style={{ marginTop: 3 }}>использовано {Math.round(d.debt / d.limit * 100)}% лимита {money(d.limit)}</div></> : null}
            <div class="faint" style={{ marginTop: 4 }}>
              ставка {d.rate ? `${d.rate}%` : <span class="warn">не указана — нажмите, чтобы ввести из договора</span>}, мин. платёж {money(d.minPayment)}
              {acc?.minPaymentDue ? ` до ${fmtDate(acc.minPaymentDue)}` : ''}
              {acc && !acc.minPayment ? ' (оценка 3%)' : ''}
              {acc?.debtDate ? `; долг на ${fmtDate(acc.debtDate)}` : ''}
              {acc?.graceDays ? `; льготный период до ${acc.graceDays} дней` : ''}
            </div>
          </button>
        );
      })}
      <div class="btns"><button class="btn small" onClick={() => setEdit('new')}>Добавить другой долг</button></div>

      {debts.length > 0 && (
        <>
          <h2>План погашения</h2>
          <label class="field"><span>Сколько готовы отдавать на долги в месяц, ₽</span>
            <input class="input" inputMode="numeric" value={budgetStr} onInput={e => saveBudget(e.currentTarget.value)} />
          </label>
          {budget < minSum && <p class="note red">Это меньше суммы минимальных платежей ({money(minSum)}) — будут просрочки.</p>}
          {plan.enough && Number.isFinite(plan.months) ? (
            <div class="rows calc" style={{ padding: '8px 10px', marginTop: 10 }}>
              <div class="line total" style={{ borderTop: 0, marginTop: 0 }}><span>Закроете все долги за</span><span>{plan.months} {monthsWord(plan.months)}</span></div>
              <div class="line"><span>примерно к</span><span>{finish(plan.months)}</span></div>
              <div class="line"><span>Переплата по процентам, не больше</span><Money v={plan.totalInterest} /></div>
              <div class="sub" style={{ paddingTop: 4 }}>Порядок: {plan.order.join(', затем ')}. Сначала гасится самый дорогой долг, по остальным — минимальные платежи.</div>
            </div>
          ) : (
            <p class="note red">При такой сумме долг не уменьшается — увеличьте ежемесячный платёж.</p>
          )}
          {plan.enough && faster.enough && Number.isFinite(faster.months) && faster.months < plan.months && (
            <p class="note blue">Если платить на 5 000 ₽ больше ({money(budget + 5000)}), закроете на {plan.months - faster.months} {monthsWord(plan.months - faster.months)} раньше и сэкономите {money(plan.totalInterest - faster.totalInterest)} на процентах.</p>
          )}
          <p class="faint">Оценка сверху: проценты считаются на весь остаток каждый месяц. Пока долг гасится в льготный период, процентов может не быть совсем — поэтому вносить больше минимального особенно выгодно.</p>
        </>
      )}
      {edit && <DebtSheet d={edit === 'new' ? null : edit} onClose={() => setEdit(null)} />}
    </>
  );
}

function DebtSheet({ d, onClose }: { d: Debt | null; onClose: () => void }) {
  const { data, update } = useStore();
  const fromStatement = d?.fromStatement ?? false;
  const [title, setTitle] = useState(d?.title ?? '');
  const [debt, setDebt] = useState(String(d?.debt ?? ''));
  const [rate, setRate] = useState(d?.rate ? String(d.rate) : '');
  const [minP, setMinP] = useState(String(d?.minPayment ?? ''));
  const num = (s: string) => Number(s.replace(/\s/g, '').replace(',', '.')) || 0;
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
    <Sheet onClose={onClose}>
      <h2 style={{ marginTop: 0 }}>{d ? d.title : 'Новый долг'}</h2>
      {fromStatement
        ? <p class="muted">Долг {money(d!.debt)} взят из выписки{acc?.debtDate ? ` на ${fmtDate(acc.debtDate)}` : ''}. Обновится, когда загрузите новую выписку.</p>
        : <>
          <label class="field"><span>Название</span><input class="input" value={title} onInput={e => setTitle(e.currentTarget.value)} placeholder="Кредит, рассрочка…" /></label>
          <label class="field"><span>Остаток долга, ₽</span><input class="input" inputMode="numeric" value={debt} onInput={e => setDebt(e.currentTarget.value)} /></label>
        </>}
      <div class="inline">
        <label class="field"><span>Ставка, % годовых</span><input class="input" inputMode="decimal" value={rate} onInput={e => setRate(e.currentTarget.value)} placeholder="например, 29,9" /></label>
        <label class="field"><span>Мин. платёж, ₽</span><input class="input" inputMode="numeric" value={minP} onInput={e => setMinP(e.currentTarget.value)} /></label>
      </div>
      <p class="faint" style={{ marginTop: 6 }}>Ставка указана в договоре или в условиях карты в приложении банка (тарифный план).</p>
      <div class="btns">
        <button class="btn primary" onClick={save}>Сохранить</button>
        {d && !fromStatement && <button class="btn danger" onClick={remove}>Удалить</button>}
      </div>
    </Sheet>
  );
}
