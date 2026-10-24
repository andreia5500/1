// Постоянные платежи и личный консультант: хватит ли денег на всё
import { useMemo, useState } from 'preact/hooks';
import { useStore } from '../store';
import { advise, type Advice } from '../core/advisor';
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES } from '../core/categories';
import type { Period, Planned } from '../core/types';
import { dayTitle, fmtDate } from '../core/util';
import { enableNotifications } from '../notify';
import { isNative } from '../platform';
import { Dot, Money, Sheet, money, num, uid } from './components';

const PERIOD: Record<Period, string> = { month: 'каждый месяц', quarter: 'раз в квартал', year: 'раз в год' };
const MONTHS = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'];

export function Payments() {
  const { data, txs, update, toast, openAdd, today } = useStore();
  const a = useMemo(() => advise(data, txs, today), [data, txs, today]);
  const [edit, setEdit] = useState<Planned | 'payment' | 'income' | null>(null);
  const [cashEdit, setCashEdit] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const pays = data.settings.planned.filter(p => p.type === 'payment').sort((x, y) => x.day - y.day);
  const incs = data.settings.planned.filter(p => p.type === 'income').sort((x, y) => x.day - y.day);
  const events = a.upcoming;
  const shown = showAll ? events : events.slice(0, 10);
  const grouped = groupBy(shown, e => e.occ.date);
  const free = a.monthlyIncome - a.monthlyPayments;

  return (
    <>
      <div class="top"><h1>Платежи</h1></div>

      <section class="card big hero">
        <div class="label">Можно тратить в день</div>
        <div class={'big num' + (a.safePerDay < 0 ? ' neg' : '')}>{a.safePerDay < 0 ? 'Не хватает' : money(a.safePerDay)}</div>
        <div class="sub">
          {a.safePerDay < 0
            ? `Даже без повседневных трат к ${dayTitle(a.safeUntil)} не хватит на все платежи. Смотрите советы ниже.`
            : `Чтобы до ${dayTitle(a.safeUntil)} хватило на все платежи и на картах осталось не меньше ${money(a.buffer)}. Сейчас в среднем уходит ${money(a.rate)} в день.`}
        </div>
        <BalanceChart a={a} />
      </section>

      <section class="card inner gap12">
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
          <span class="muted small">Деньги сейчас</span>
          <Money v={a.cash.amount} className="bold" />
        </div>
        {a.cash.parts.map(p => <p class="tiny muted" key={p} style={{ marginTop: 4 }}>{p}</p>)}
        {a.cash.stale && a.cash.source === 'statements' && (
          <p class="tiny warn" style={{ marginTop: 8 }}>Остаток из выписки устарел. Укажите, сколько сейчас на картах, — прогноз станет точнее.</p>
        )}
        <div class="btns" style={{ marginTop: 10 }}>
          <button class="btn small" onClick={() => setCashEdit(true)}>Уточнить остаток</button>
          {a.cash.source === 'manual' && <button class="btn small ghost" onClick={() => { update(d => ({ ...d, settings: { ...d.settings, balanceOverride: undefined } })); toast('Остаток снова берётся из выписок'); }}>Брать из выписок</button>}
        </div>
      </section>

      {a.warnings.length > 0 && <div class="sec-head"><h2>Советы</h2></div>}
      {a.warnings.map((w, i) => (
        <div key={i} class={'note ' + (w.level === 'danger' ? 'bad' : w.level === 'warn' ? 'warnbg' : w.level === 'ok' ? 'ok' : '')} style={{ margin: (i ? '10px' : '0') + ' 16px 0' }}>
          <b>{w.title}</b>
          <p class="muted" style={{ marginTop: 3, fontSize: 14 }}>{w.text}</p>
        </div>
      ))}

      <div class="sec-head"><h2>Ближайшие платежи</h2>{events.length > 10 && <button class="link-btn" onClick={() => setShowAll(!showAll)}>{showAll ? 'Свернуть' : 'Все 45 дней'}</button>}</div>
      <section class="card" style={{ padding: '2px 0' }}>
        {!events.length && <p class="muted" style={{ padding: 16 }}>Добавьте постоянные платежи и зарплату ниже — здесь появится календарь на полтора месяца вперёд.</p>}
        {grouped.map(([date, list]) => (
          <div class="day" key={date}>
            <div class="dh"><span class="bold" style={{ color: 'var(--ink)' }}>{date === today ? 'Сегодня' : dayTitle(date)}</span><span class="num">остаток ≈ {money(list[list.length - 1].after)}</span></div>
            {list.map(e => (
              <div class="ev" key={e.occ.key}>
                <Dot category={e.occ.p.category ?? (e.occ.p.type === 'income' ? 'Зарплата' : 'Прочее')} />
                <div class="grow">
                  <div class="title">{e.occ.p.title}</div>
                  {e.occ.p.type === 'payment' && (
                    <span class={'tag ' + e.status}>{e.status === 'ok' ? 'хватает' : e.status === 'tight' ? 'впритык' : `не хватит ${money(-e.after)}`}</span>
                  )}
                </div>
                <Money v={e.occ.p.type === 'income' ? e.occ.p.amount : -e.occ.p.amount} sign className={e.occ.p.type === 'income' ? 'pos bold' : 'bold'} />
                {date <= addOne(today) && (
                  <button class="btn small" onClick={() => openAdd({
                    kind: e.occ.p.type === 'income' ? 'income' : 'expense', amount: e.occ.p.amount, category: e.occ.p.category,
                    note: e.occ.p.title, date: today, plannedRef: e.occ.key,
                  })}>{e.occ.p.type === 'income' ? 'Пришло' : 'Оплачено'}</button>
                )}
              </div>
            ))}
          </div>
        ))}
      </section>

      <div class="sec-head"><h2>Постоянные платежи</h2><button class="link-btn" onClick={() => setEdit('payment')}>Добавить</button></div>
      <section class="card" style={{ padding: '2px 0' }}>
        {!pays.length && <p class="muted" style={{ padding: 16 }}>Кредиты, ЖКХ, связь, садик, кружки — всё, что платите регулярно.</p>}
        {pays.map(p => <PlannedRow key={p.id} p={p} onClick={() => setEdit(p)} />)}
      </section>

      <div class="sec-head"><h2>Поступления</h2><button class="link-btn" onClick={() => setEdit('income')}>Добавить</button></div>
      <section class="card" style={{ padding: '2px 0' }}>
        {!incs.length && <p class="muted" style={{ padding: 16 }}>Зарплата, аванс, пенсия, пособия — когда и сколько приходит.</p>}
        {incs.map(p => <PlannedRow key={p.id} p={p} onClick={() => setEdit(p)} />)}
      </section>

      {(pays.length > 0 || incs.length > 0) && (
        <section class="card inner gap12 calc">
          <div class="line"><span>Поступления в месяц</span><Money v={a.monthlyIncome} className="pos" /></div>
          <div class="line"><span>Постоянные платежи в месяц</span><Money v={-a.monthlyPayments} /></div>
          <div class="line total"><span>Остаётся на жизнь</span><Money v={free} className={free < 0 ? 'neg' : ''} /></div>
          {a.monthlyIncome > 0 && <p class="sub" style={{ marginTop: 4 }}>Обязательные платежи забирают {Math.round(a.monthlyPayments / a.monthlyIncome * 100)}% дохода. Это около {money(free / 30)} в день на всё остальное.</p>}
        </section>
      )}

      <div class="sec-head"><h2>Настройки консультанта</h2></div>
      <section class="card inner">
        <label class="field" style={{ marginTop: 0 }}><span>Неснижаемый остаток на картах, ₽ — подушка на непредвиденное</span>
          <input class="input" inputMode="numeric" value={String(data.settings.safetyBuffer)} onChange={e => update(d => ({ ...d, settings: { ...d.settings, safetyBuffer: num(e.currentTarget.value) } }))} />
        </label>
        <label class="check">
          <input type="checkbox" checked={data.settings.notifications} onChange={async e => {
            const on = e.currentTarget.checked;
            if (on && isNative()) {
              const ok = await enableNotifications();
              if (!ok) { toast('Разрешите уведомления для приложения в настройках телефона'); return; }
            }
            update(d => ({ ...d, settings: { ...d.settings, notifications: on } }));
            if (on && !isNative()) toast('Уведомления работают в приложении на телефоне');
          }} />
          <span>Напоминать на телефоне: за день до платежа, в день зарплаты — сколько отложить, и заранее — если может не хватить</span>
        </label>
      </section>

      {edit && <PlannedSheet p={typeof edit === 'string' ? null : edit} type={typeof edit === 'string' ? edit : edit.type} onClose={() => setEdit(null)} />}
      {cashEdit && <CashSheet current={a.cash.amount} onClose={() => setCashEdit(false)} />}
    </>
  );
}

const addOne = (d: string) => { const x = new Date(d + 'T00:00:00Z'); x.setUTCDate(x.getUTCDate() + 1); return x.toISOString().slice(0, 10); };

function groupBy<T>(xs: T[], key: (x: T) => string): [string, T[]][] {
  const m = new Map<string, T[]>();
  for (const x of xs) m.set(key(x), [...(m.get(key(x)) ?? []), x]);
  return [...m.entries()];
}

function PlannedRow({ p, onClick }: { p: Planned; onClick: () => void }) {
  const per = p.period ?? 'month';
  return (
    <button class="row" onClick={onClick} style={{ opacity: p.enabled ? 1 : 0.5 }}>
      <Dot category={p.category ?? (p.type === 'income' ? 'Зарплата' : 'Прочее')} />
      <div class="grow">
        <div class="title">{p.title}</div>
        <div class="meta">{per === 'month' ? `${p.day}-го числа каждый месяц` : `${p.day}-го, ${PERIOD[per]}${p.startMonth ? ` (с ${MONTHS[p.startMonth - 1].slice(0, 3)}.)` : ''}`}{p.category ? `, ${p.category.toLowerCase()}` : ''}{p.enabled ? '' : ', выключен'}</div>
      </div>
      <Money v={p.type === 'income' ? p.amount : -p.amount} className={(p.type === 'income' ? 'pos ' : '') + 'bold'} />
    </button>
  );
}

function PlannedSheet({ p, type, onClose }: { p: Planned | null; type: 'payment' | 'income'; onClose: () => void }) {
  const { update, today } = useStore();
  const [x, setX] = useState<Planned>(p ?? { id: uid(), title: '', type, amount: 0, day: Number(today.slice(8)), enabled: true, period: 'month', category: type === 'income' ? 'Зарплата' : 'ЖКХ' });
  const [amountStr, setAmountStr] = useState(x.amount ? String(x.amount) : '');
  const cats = (x.type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES).map(c => c.name);
  const per = x.period ?? 'month';
  const valid = x.title.trim() && num(amountStr) > 0 && x.day >= 1 && x.day <= 31;
  const save = () => {
    if (!valid) return;
    const item = { ...x, amount: num(amountStr), title: x.title.trim(), startMonth: per === 'month' ? undefined : x.startMonth ?? Number(today.slice(5, 7)) };
    update(d => ({ ...d, settings: { ...d.settings, planned: p ? d.settings.planned.map(y => (y.id === item.id ? item : y)) : [...d.settings.planned, item] } }));
    onClose();
  };
  const remove = () => {
    update(d => ({ ...d, settings: { ...d.settings, planned: d.settings.planned.filter(y => y.id !== x.id), plannedDismissed: x.key ? [...d.settings.plannedDismissed, x.key] : d.settings.plannedDismissed } }));
    onClose();
  };
  return (
    <Sheet onClose={onClose} title={p ? (x.type === 'income' ? 'Поступление' : 'Постоянный платёж') : x.type === 'income' ? 'Новое поступление' : 'Новый платёж'}>
      <label class="field"><span>Название</span>
        <input class="input" value={x.title} onInput={e => setX({ ...x, title: e.currentTarget.value })} placeholder={x.type === 'income' ? 'Зарплата, аванс, пенсия…' : 'Ипотека, ЖКХ, интернет, садик…'} />
      </label>
      <div class="inline">
        <label class="field"><span>Сумма, ₽</span><input class="input num" inputMode="decimal" value={amountStr} onInput={e => setAmountStr(e.currentTarget.value)} /></label>
        <label class="field"><span>Какого числа</span><input class="input num" inputMode="numeric" value={String(x.day)} onInput={e => setX({ ...x, day: Math.round(num(e.currentTarget.value)) })} /></label>
      </div>
      <div class="field"><span>Как часто</span>
        <div class="seg">
          {(['month', 'quarter', 'year'] as Period[]).map(k => (
            <button key={k} class={per === k ? 'on' : ''} onClick={() => setX({ ...x, period: k })}>{k === 'month' ? 'Каждый месяц' : k === 'quarter' ? 'Раз в квартал' : 'Раз в год'}</button>
          ))}
        </div>
      </div>
      {per !== 'month' && (
        <label class="field"><span>{per === 'year' ? 'В каком месяце' : 'Месяц ближайшего платежа'}</span>
          <select class="input" value={String(x.startMonth ?? Number(today.slice(5, 7)))} onChange={e => setX({ ...x, startMonth: Number(e.currentTarget.value) })}>
            {MONTHS.map((m, i) => <option key={m} value={String(i + 1)}>{m}</option>)}
          </select>
        </label>
      )}
      <label class="field"><span>Категория</span>
        <select class="input" value={x.category ?? cats[0]} onChange={e => setX({ ...x, category: e.currentTarget.value })}>
          {cats.map(c => <option key={c}>{c}</option>)}
        </select>
      </label>
      <label class="check"><input type="checkbox" checked={x.enabled} onChange={e => setX({ ...x, enabled: e.currentTarget.checked })} /><span>Учитывать в прогнозе и напоминаниях</span></label>
      {x.auto && <p class="tiny muted" style={{ marginTop: 10 }}>Найдено автоматически по выпискам — проверьте сумму и число.</p>}
      <div class="btns">
        <button class="btn primary wide" disabled={!valid} onClick={save}>Сохранить</button>
        {p && <button class="btn danger wide" onClick={remove}>Удалить</button>}
      </div>
    </Sheet>
  );
}

function CashSheet({ current, onClose }: { current: number; onClose: () => void }) {
  const { update, toast } = useStore();
  const [v, setV] = useState(String(Math.round(current)));
  const save = () => {
    update(d => ({ ...d, settings: { ...d.settings, balanceOverride: { amount: num(v), at: new Date().toISOString() } } }));
    toast('Остаток обновлён — прогноз пересчитан');
    onClose();
  };
  return (
    <Sheet onClose={onClose} title="Сколько сейчас на картах">
      <p class="muted small" style={{ marginTop: 4 }}>Сложите остатки на дебетовых картах и наличные — без кредитного лимита. Траты, которые вы запишете кнопкой «+» после этого, приложение вычтет само.</p>
      <label class="amount-wrap"><input class="amount-in num" inputMode="decimal" value={v} onInput={e => setV(e.currentTarget.value)} aria-label="Остаток, рублей" /><span>₽</span></label>
      <div class="btns"><button class="btn primary wide" onClick={save}>Сохранить</button></div>
    </Sheet>
  );
}

/** График остатка на 45 дней: ноль, подушка, платежи и поступления */
function BalanceChart({ a }: { a: Advice }) {
  const W = 340, H = 140, padT = 10, padB = 22;
  const pts = [{ date: a.today, v: a.cash.amount }, ...a.timeline.slice(1).map(d => ({ date: d.date, v: d.end }))];
  const vals = pts.map(p => p.v);
  const max = Math.max(...vals, a.buffer, 1);
  const min = Math.min(...vals, 0);
  const x = (i: number) => (i / (pts.length - 1)) * W;
  const y = (v: number) => padT + (1 - (v - min) / (max - min || 1)) * (H - padT - padB);
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
  const area = `${line} L${W},${y(min)} L0,${y(min)} Z`;
  const ev = a.timeline.flatMap((d, i) => d.events.map(e => ({ i, e })));
  const labels = pts.map((p, i) => ({ i, d: p.date })).filter(p => p.i === 0 || p.d.endsWith('-01') || p.i === pts.length - 1);
  return (
    <svg class="chart" viewBox={`0 0 ${W} ${H}`} role="img" style={{ marginTop: 18, overflow: 'visible', height: 'auto' }}
      aria-label={`Прогноз остатка на 45 дней: минимум ${Math.round(a.minPoint?.value ?? 0)} рублей ${a.minPoint ? fmtDate(a.minPoint.date) : ''}`}>
      <path d={area} fill="var(--acc)" opacity="0.08" />
      {min < 0 && <rect x="0" y={y(0)} width={W} height={y(min) - y(0)} fill="var(--bad)" opacity="0.08" />}
      <line x1="0" x2={W} y1={y(a.buffer)} y2={y(a.buffer)} stroke="var(--warn)" stroke-width="1" stroke-dasharray="4 4" vector-effect="non-scaling-stroke" />
      <line x1="0" x2={W} y1={y(0)} y2={y(0)} stroke="var(--ink)" stroke-width="1" opacity="0.5" vector-effect="non-scaling-stroke" />
      <path d={line} fill="none" stroke="var(--acc)" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" />
      {ev.map(({ i, e }) => (
        <circle key={e.occ.key} cx={x(i)} cy={y(e.after)} r="3.2" fill={e.occ.p.type === 'income' ? 'var(--pos)' : e.after < 0 ? 'var(--bad)' : 'var(--card)'} stroke={e.occ.p.type === 'income' ? 'var(--pos)' : e.after < 0 ? 'var(--bad)' : 'var(--acc)'} stroke-width="1.6" vector-effect="non-scaling-stroke" />
      ))}
      {labels.map(l => (
        <text key={l.i} x={x(l.i)} y={H - 4} font-size="10.5" fill="var(--mut)" text-anchor={l.i === 0 ? 'start' : l.i === pts.length - 1 ? 'end' : 'middle'}>{fmtDate(l.d).slice(0, 5)}</text>
      ))}
      <text x={W} y={y(a.buffer) - 4} font-size="10.5" fill="var(--warn)" text-anchor="end">подушка {money(a.buffer)}</text>
    </svg>
  );
}
