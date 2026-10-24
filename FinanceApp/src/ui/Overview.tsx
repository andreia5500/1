import { useMemo, useState } from 'preact/hooks';
import { useStore } from '../store';
import { monthCoverage, monthsAvailable, savingTips, summarizeMonth } from '../core/analytics';
import { advise } from '../core/advisor';
import { collectDebts, simulatePayoff } from '../core/debts';
import { catInfo } from '../core/categories';
import { byMonthAfter, daysInMonth, dayTitle, fmtDate, monthKey, monthTitle } from '../core/util';
import { Bar, Dot, Icons, Money, money } from './components';
import { ImportButton } from './App';

const MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

export function Overview() {
  const { data, txs, go, update, toast, today } = useStore();
  const months = useMemo(() => {
    const m = monthsAvailable(txs.filter(t => t.kind !== 'matched'));
    return m.includes(monthKey(today)) ? m : [monthKey(today), ...m];
  }, [txs, today]);
  const [month, setMonth] = useState(monthKey(today));
  const idx = months.indexOf(month);
  const s = useMemo(() => summarizeMonth(txs, month), [txs, month]);
  const cov = useMemo(() => monthCoverage(data.accounts, data.statements, month), [data, month]);
  const isCurrent = month === monthKey(today);
  const a = useMemo(() => advise(data, txs, today), [data, txs, today]);
  const tips = useMemo(() => savingTips(txs, month), [txs, month]);
  const [allCats, setAllCats] = useState(false);

  if (!data.statements.length && !data.txs.length) return <Empty />;

  const dim = daysInMonth(month);
  const lastDay = `${month}-${String(dim).padStart(2, '0')}`;
  const day = isCurrent ? Number(today.slice(8)) : dim;
  const gaps = cov.filter(c => c.days < c.total && (!isCurrent || (c.to ?? '') < today));
  const maxCat = s.byCategory[0]?.amount ?? 0;
  const debts = collectDebts(data);
  const totalDebt = debts.reduce((x, d) => x + d.debt, 0);
  const soon = a.upcoming.filter(u => u.occ.p.type === 'payment' && u.occ.date <= fmtPlus(today, 3));
  const top = a.warnings.find(w => w.level === 'danger') ?? a.warnings.find(w => w.level === 'warn');

  return (
    <>
      <div class="top">
        <button class="icon-btn" aria-label="Предыдущий месяц" disabled={idx >= months.length - 1} onClick={() => setMonth(months[idx + 1])}>{Icons.left}</button>
        <h1 style={{ padding: 0 }}>{monthTitle(month)}</h1>
        <button class="icon-btn" aria-label="Следующий месяц" disabled={idx <= 0} onClick={() => setMonth(months[idx - 1])}>{Icons.right}</button>
        <div class="grow" />
        <ImportButton round label="Загрузить выписку" />
      </div>

      <section class="card big hero">
        {isCurrent ? (
          <>
            <div class="label">Останется к {Number(lastDay.slice(8))} {MONTHS_GEN[Number(month.slice(5)) - 1]}</div>
            <div class={'big num' + ((a.monthEnd ?? 0) < 0 ? ' neg' : '')}>{money(a.monthEnd ?? a.cash.amount)}</div>
            <div class="sub">На повседневное уходит около {money(a.rate)} в день, впереди {dim - day} {dim - day === 1 ? 'день' : dim - day < 5 ? 'дня' : 'дней'}</div>
          </>
        ) : (
          <>
            <div class="label">Итог месяца: доходы минус расходы</div>
            <div class={'big num ' + (s.net < 0 ? 'neg' : 'pos')}>{s.net > 0 ? '+' : ''}{money(s.net)}</div>
          </>
        )}
        <Ruler daily={s.daily} month={month} today={isCurrent ? today : undefined} rate={a.rate} spent={s.expense} />
      </section>

      <section class="card strip gap12">
        <button onClick={() => go('ops', { kind: 'income', month })}><div class="l">Доходы</div><div class="v num pos">{money(s.income)}</div></button>
        <button onClick={() => go('ops', { kind: 'expense', month })}><div class="l">Расходы</div><div class="v num">{money(s.expense)}</div></button>
        <button onClick={() => go('ops', { kind: 'transfer', month })}><div class="l">Отложено</div><div class="v num">{money(s.toOwnOtherBanks)}</div></button>
      </section>

      {isCurrent && (
        top ? (
          <button class={'banner ' + (top.level === 'danger' ? 'bad' : '')} onClick={() => go('payments')}>
            <span class="badge">!</span>
            <span class="grow"><div class="t">{top.title}</div><div class="s">{top.text}</div></span>
            {Icons.chevron}
          </button>
        ) : data.settings.planned.some(p => p.enabled) ? (
          <button class="banner ok" onClick={() => go('payments')}>
            <span class="badge">{Icons.check}</span>
            <span class="grow">
              <div class="t">Можно тратить до {money(Math.max(0, a.safePerDay))} в день</div>
              <div class="s">На все постоянные платежи хватит{a.nextIncome ? `; следующее поступление — ${a.nextIncome.p.title.toLowerCase()} ${dayTitle(a.nextIncome.date)}` : ''}</div>
            </span>
            {Icons.chevron}
          </button>
        ) : null
      )}

      {s.needsReview > 0 && (
        <button class="banner" onClick={() => go('ops', { kind: 'review', month })}>
          <span class="badge num">{s.needsReview}</span>
          <span class="grow"><div class="t">Операции нужно уточнить</div><div class="s">Переводы и платежи, по которым из выписки не понять, что это</div></span>
          {Icons.chevron}
        </button>
      )}

      {gaps.length > 0 && (
        <div class="note warnbg" style={{ margin: '12px 16px 0' }}>
          Месяц покрыт выписками не полностью: {gaps.map(c => `${c.account.title} — ${c.days ? `есть ${fmtDate(c.from!).slice(0, 5)}–${fmtDate(c.to!).slice(0, 5)}` : 'нет данных'}`).join('; ')}. Загрузите свежие выписки или записывайте траты кнопкой «+».
        </div>
      )}

      <div class="sec-head">
        <h2>Куда ушли деньги</h2>
        {s.byCategory.length > 5 && <button class="link-btn" onClick={() => setAllCats(!allCats)}>{allCats ? 'Свернуть' : 'Все категории'}</button>}
      </div>
      <section class="card" style={{ padding: '4px 0' }}>
        {!s.byCategory.length && <p class="muted" style={{ padding: 16 }}>Расходов за этот месяц пока нет.</p>}
        {(allCats ? s.byCategory : s.byCategory.slice(0, 5)).map(c => {
          const limit = data.settings.limits[c.category];
          const projected = isCurrent ? c.amount / day * dim : c.amount;
          const note = limit
            ? c.amount > limit ? `Лимит ${money(limit)} превышен на ${money(c.amount - limit)}`
              : projected > limit ? `Лимит ${money(limit)}: в таком темпе к ${dim}-му будет ${money(projected)}`
                : `Лимит ${money(limit)}: осталось ${money(limit - c.amount)}`
            : '';
          return (
            <button class="cat" key={c.category} onClick={() => go('ops', { category: c.category, month })}>
              <div class="head">
                <Dot category={c.category} />
                <span class="grow">{c.category}</span>
                <span class="num small muted">{Math.round(c.share * 100)}%</span>
                <span class="amt num">{money(c.amount)}</span>
              </div>
              <Bar value={c.amount} max={maxCat} color={limit && c.amount > limit ? 'var(--bad)' : catInfo(c.category).color} />
              {note && <div class="tiny" style={{ margin: '7px 0 0 20px', color: limit && projected > limit ? 'var(--warn)' : 'var(--mut)' }}>{note}</div>}
            </button>
          );
        })}
      </section>

      {tips.length > 0 && <div class="sec-head"><h2>Где сэкономить</h2></div>}
      {tips.map((t, i) => (
        <section class="card soft inner" key={t.title} style={{ marginTop: i ? 10 : 0, padding: '18px 18px 16px' }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <span class="acc" style={{ flex: 'none', marginTop: 1 }}>{Icons.bag}</span>
            <div>
              <h3>{t.title}</h3>
              <p class="muted" style={{ marginTop: 4, fontSize: 14, lineHeight: 1.45 }}>{t.text}</p>
            </div>
          </div>
          {t.suggestLimit && t.category && !data.settings.limits[t.category] && (
            <div class="btns" style={{ paddingLeft: 36 }}>
              <button class="btn primary small" onClick={() => {
                update(d => ({ ...d, settings: { ...d.settings, limits: { ...d.settings.limits, [t.category!]: t.suggestLimit! } } }));
                toast(`Лимит ${money(t.suggestLimit!)} в месяц на «${t.category}» поставлен`);
              }}>Лимит {money(t.suggestLimit)} в месяц</button>
            </div>
          )}
        </section>
      ))}

      {debts.length > 0 && (
        <>
          <div class="sec-head"><h2>Кредитки</h2><button class="link-btn" onClick={() => go('budget')}>План погашения</button></div>
          <section class="card inner">
            {soon.filter(u => u.occ.p.key?.startsWith('min:')).map(u => (
              <div key={u.occ.key} class="note warnbg" style={{ marginTop: 0, marginBottom: 14, display: 'flex', gap: 10, alignItems: 'center' }}>
                <span class="warn">{Icons.clock}</span>
                <span>{u.occ.date === today ? 'Сегодня последний день' : `До ${fmtDate(u.occ.date).slice(0, 5)}`}: <b>{money(u.occ.p.amount)}</b> — {u.occ.p.title.replace('Мин. платёж: ', 'минимальный платёж, ')}</span>
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
              <span class="muted small">Общий долг</span>
              <span class="num" style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>{money(totalDebt)}</span>
            </div>
            {debts.map(d => {
              const use = d.limit ? d.debt / d.limit : 0;
              return (
                <div key={d.id} style={{ marginTop: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}><span>{d.title}</span><Money v={d.debt} className="bold" /></div>
                  {d.limit ? <Bar value={d.debt} max={d.limit} color={use > 0.9 ? 'var(--warn)' : 'var(--ink)'} flush /> : null}
                  <div class={'tiny ' + (use > 0.9 ? 'warn' : 'muted')} style={{ marginTop: 5 }}>
                    {d.limit ? `${Math.round(use * 100)}% лимита` : ''}{use > 0.9 ? ' — почти исчерпан' : ''}{d.rate ? `, ${String(d.rate).replace('.', ',')}% годовых` : ''}
                  </div>
                </div>
              );
            })}
            <DebtLine />
          </section>
        </>
      )}
    </>
  );
}

function fmtPlus(date: string, n: number) {
  const d = new Date(date + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10);
}

function DebtLine() {
  const { data, today } = useStore();
  const debts = collectDebts(data);
  const budget = data.settings.debtBudget ?? 10000;
  const r = simulatePayoff(debts, budget);
  if (!r.enough || !Number.isFinite(r.months)) return null;
  return (
    <p style={{ marginTop: 16, paddingTop: 14, boxShadow: 'inset 0 1px 0 var(--line)', fontSize: 14 }}>
      Отдавая <b class="num">{money(budget)}</b> в месяц, закроете {debts.length > 1 ? 'все долги' : 'долг'} <b>к {byMonthAfter(today, r.months)}</b>
    </p>
  );
}

function Ruler({ daily, month, today, rate, spent }: { daily: { date: string; amount: number }[]; month: string; today?: string; rate: number; spent: number }) {
  const dim = daysInMonth(month);
  const map = new Map(daily.map(d => [Number(d.date.slice(8)), d.amount]));
  const nonzero = daily.map(d => d.amount).filter(v => v > 0).sort((x, y) => x - y);
  const median = nonzero.length ? nonzero[Math.floor(nonzero.length / 2)] : 1000;
  const cap = Math.max(1000, median * 3);
  const H = 70;
  const tDay = today ? Number(today.slice(8)) : 0;
  const outliers: number[] = [];
  const cols = Array.from({ length: dim }, (_, i) => {
    const d = i + 1;
    const v = map.get(d) ?? 0;
    const future = !!today && d > tDay;
    const out = v > cap;
    if (out) outliers.push(d);
    const h = future ? Math.max(3, Math.round(Math.min(rate, cap) / cap * H)) : v > 0 ? Math.max(3, Math.round(Math.min(v, cap) / cap * H) + (out ? 6 : 0)) : 2;
    const major = d === 1 || d === 10 || d === 20 || d === dim || d === tDay;
    return (
      <div class="col" key={d}>
        <div class="area"><div class={'b' + (future ? ' fc' : v > 0 ? '' : ' zero')} style={{ height: h + 'px' }}>{out && <span class="brk" />}</div></div>
        <div class={'tick' + (d === tDay ? ' today' : major ? ' major' : '')} />
        <div class={'lab num' + (d === tDay ? ' today' : '')}>{major ? d : ''}</div>
      </div>
    );
  });
  const rest = today ? Math.round(rate * (dim - tDay)) : 0;
  return (
    <>
      <div class="ruler" role="img" aria-label={`Траты по дням: потрачено ${Math.round(spent)} рублей${today ? `, прогноз до конца месяца ещё около ${rest} рублей` : ''}`}>
        <div class="base" />
        <div class="cols">{cols}</div>
      </div>
      <div class="legend">
        <span><i />Потрачено <b class="num">{money(spent)}</b></span>
        {today && <span><i class="fc" />Прогноз ещё <b class="num">≈ {money(rest)}</b></span>}
      </div>
      {outliers.length > 0 && (
        <p class="tiny muted" style={{ marginTop: 8 }}>Столбцы {outliers.join(', ')} обрезаны: там крупные разовые суммы</p>
      )}
    </>
  );
}

function Empty() {
  const { openAdd } = useStore();
  return (
    <section class="card big empty">
      <h1>С чего начать</h1>
      <p class="muted" style={{ marginTop: 8 }}>Приложение разбирает PDF-выписки банков, показывает, куда уходят деньги, и подсказывает, чтобы на постоянные платежи всегда хватало. Всё хранится только на этом телефоне.</p>
      <ol>
        <li>В приложении СберБанк Онлайн: карта → «Выписки и справки» → выписка за месяц → «Поделиться» → «Мои финансы».</li>
        <li>В приложении Т-Банка: «Ещё» → «Документы» → выписка → PDF → «Поделиться».</li>
        <li>Или сохраните PDF в телефон и нажмите кнопку ниже.</li>
      </ol>
      <div class="btns">
        <ImportButton primary label="Выбрать PDF" />
        <button class="btn" onClick={() => openAdd()}>Записать вручную</button>
      </div>
    </section>
  );
}
