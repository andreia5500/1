import { useMemo, useState } from 'preact/hooks';
import { useStore } from '../store';
import { monthCoverage, monthsAvailable, savingTips, summarizeMonth } from '../core/analytics';
import { forecastMonth } from '../core/forecast';
import { catInfo } from '../core/categories';
import { daysInMonth, fmtDate, monthKey, monthTitle, todayIso } from '../core/util';
import { Bar, Dot, Icons, Money, money } from './components';
import { ImportButton } from './App';

export function Overview() {
  const { data, txs, go } = useStore();
  const today = todayIso();
  const months = useMemo(() => {
    const m = monthsAvailable(txs);
    return m.length ? m : [monthKey(today)];
  }, [txs]);
  const [month, setMonth] = useState(months[0]);
  const idx = months.indexOf(month);
  const s = useMemo(() => summarizeMonth(txs, month), [txs, month]);
  const cov = useMemo(() => monthCoverage(data.accounts, data.statements, month), [data, month]);
  const isCurrent = month === monthKey(today);
  const f = useMemo(() => (isCurrent ? forecastMonth(data, txs, today) : null), [data, txs, isCurrent]);
  const tips = useMemo(() => savingTips(txs, month, data.accounts), [txs, month, data.accounts]);

  if (!data.statements.length) return <Empty />;

  const lastDay = `${month}-${String(daysInMonth(month)).padStart(2, '0')}`;
  const gaps = cov.filter(c => c.days < c.total && (!isCurrent || (c.to ?? '') < today));
  const maxCat = s.byCategory[0]?.amount ?? 0;

  return (
    <>
      <div class="top">
        <div class="month-switch">
          <button class="icon-btn" aria-label="Предыдущий месяц" disabled={idx >= months.length - 1} onClick={() => setMonth(months[idx + 1])}>{Icons.left}</button>
          <h1>{monthTitle(month)}</h1>
          <button class="icon-btn" aria-label="Следующий месяц" disabled={idx <= 0} onClick={() => setMonth(months[idx - 1])}>{Icons.right}</button>
        </div>
      </div>

      <div class="stamp">
        {f ? (
          <button class="main cell" onClick={() => go('plan')}>
            <div class="lbl">Останется к {fmtDate(lastDay).slice(0, 5)}, прогноз</div>
            <div class={'val ' + (f.endBalance < 0 ? 'neg' : '')}>{money(f.endBalance)}</div>
            <div class="sub">повседневные траты ≈ {money(f.dailyEveryday)} в день, ещё {f.daysLeft} дн.</div>
          </button>
        ) : (
          <div class="main">
            <div class="lbl">Итог месяца: доходы минус расходы</div>
            <div class={'val ' + (s.net < 0 ? 'neg' : 'pos')}>{s.net > 0 ? '+' : ''}{money(s.net)}</div>
          </div>
        )}
        <button class="cell" onClick={() => go('ops', { kind: 'income', month })}>
          <div class="lbl">Доходы</div><div class="val pos">{money(s.income)}</div>
        </button>
        <button class="cell" onClick={() => go('ops', { kind: 'expense', month })}>
          <div class="lbl">Расходы</div><div class="val">{money(s.expense)}</div>
          {s.refunds > 0 && <div class="sub">с учётом возвратов {money(s.refunds)}</div>}
        </button>
        <button class="cell" onClick={() => go('ops', { kind: 'transfer', month })}>
          <div class="lbl">Отложено на свои счета</div><div class="val">{money(s.toOwnOtherBanks)}</div>
          <div class="sub">вклады, Озон, Яндекс и др.</div>
        </button>
        <button class="cell" onClick={() => go('ops', { kind: 'review', month })}>
          <div class="lbl">Проверить</div>
          <div class={'val ' + (s.needsReview ? 'warn' : '')}>{s.needsReview} опер.</div>
          <div class="sub">{s.needsReview ? 'нужно уточнить' : 'всё разобрано'}</div>
        </button>
      </div>

      {gaps.length > 0 && (
        <div class="note">
          Месяц покрыт выписками не полностью:
          {gaps.map(c => <div key={c.account.id}>{c.account.title}: {c.days ? `есть ${fmtDate(c.from!).slice(0, 5)}–${fmtDate(c.to!).slice(0, 5)}` : 'нет данных'}</div>)}
          Загрузите свежие выписки, чтобы цифры были точными.
        </div>
      )}

      <h2>Куда ушли деньги</h2>
      <div class="rows" style={{ paddingInline: 8 }}>
        {s.byCategory.length === 0 && <p class="muted" style={{ padding: '10px 0' }}>Расходов за этот месяц нет.</p>}
        {s.byCategory.map(c => {
          const limit = data.settings.limits[c.category];
          const over = limit && c.amount > limit;
          return (
            <button class="cat" key={c.category} onClick={() => go('ops', { category: c.category, month })}>
              <div class="head">
                <Dot category={c.category} />
                <span class="grow">{c.category}</span>
                <span class="faint">{Math.round(c.share * 100)}%</span>
                <Money v={c.amount} className={over ? 'neg' : ''} />
              </div>
              <Bar value={c.amount} max={Math.max(maxCat, limit ?? 0)} color={over ? 'var(--red)' : catInfo(c.category).color} marker={limit} />
              {limit ? <div class="faint" style={{ marginTop: 3 }}>лимит {money(limit)}{over ? `, превышен на ${money(c.amount - limit)}` : `, осталось ${money(limit - c.amount)}`}</div> : null}
            </button>
          );
        })}
      </div>

      <DailyChart daily={s.daily} month={month} today={isCurrent ? today : undefined} />

      {tips.length > 0 && (
        <>
          <h2>Где можно сэкономить</h2>
          {tips.map(t => (
            <div class="note blue" key={t.title}>
              <b>{t.title}</b>{t.amount ? <> — <Money v={t.amount} /></> : null}<br />
              <span class="muted">{t.text}</span>
            </div>
          ))}
        </>
      )}

      {s.topMerchants.length > 0 && (
        <>
          <h2>Больше всего денег получили</h2>
          <div class="rows" style={{ paddingInline: 8 }}>
            {s.topMerchants.map(m => (
              <div class="row" key={m.merchant}>
                <div class="grow"><div class="title">{m.label}</div><div class="meta">{m.count} опер.</div></div>
                <Money v={m.amount} />
              </div>
            ))}
          </div>
        </>
      )}

      {s.incomeByCategory.length > 0 && (
        <>
          <h2>Откуда пришли деньги</h2>
          <div class="rows" style={{ paddingInline: 8 }}>
            {s.incomeByCategory.map(c => (
              <button class="row" key={c.category} onClick={() => go('ops', { kind: 'income', category: c.category, month })}>
                <Dot category={c.category} />
                <div class="grow"><div class="title">{c.category}</div></div>
                <Money v={c.amount} className="pos" />
              </button>
            ))}
          </div>
        </>
      )}
    </>
  );
}

function DailyChart({ daily, month, today }: { daily: { date: string; amount: number }[]; month: string; today?: string }) {
  const dim = daysInMonth(month);
  const map = new Map(daily.map(d => [Number(d.date.slice(8)), d.amount]));
  const max = Math.max(1, ...daily.map(d => d.amount));
  if (!daily.length) return null;
  const tDay = today ? Number(today.slice(8)) : 0;
  return (
    <>
      <h2>Траты по дням</h2>
      <div class="days" aria-label="Расходы по дням месяца">
        {Array.from({ length: dim }, (_, i) => {
          const v = map.get(i + 1) ?? 0;
          return <i key={i} class={(v ? '' : 'zero') + (i + 1 === tDay ? ' today' : '')} style={{ height: v ? `${Math.max(3, (v / max) * 100)}%` : '1px' }} title={`${i + 1}: ${money(v)}`} />;
        })}
      </div>
      <div class="axis"><span>1</span><span>{Math.ceil(dim / 2)}</span><span>{dim}</span></div>
      <p class="faint" style={{ marginTop: 4 }}>Самый затратный день: {(() => { const top = [...daily].sort((a, b) => b.amount - a.amount)[0]; return `${fmtDate(top.date).slice(0, 5)} — ${money(top.amount)}`; })()}</p>
    </>
  );
}

function Empty() {
  return (
    <div class="empty">
      <h1>Загрузите первую выписку</h1>
      <p class="muted">Приложение разбирает PDF-выписки банков и показывает, куда уходят деньги. Всё хранится только на этом телефоне.</p>
      <ol>
        <li>В приложении СберБанк Онлайн: карта → «Выписки и справки» → выписка по счёту за месяц → «Поделиться» → выберите это приложение.</li>
        <li>В приложении Т-Банка: «Ещё» → «Документы» → «Выписка по счёту» → PDF → «Поделиться».</li>
        <li>Или сохраните PDF в телефон и нажмите кнопку ниже.</li>
      </ol>
      <ImportButton primary label="Выбрать PDF" />
      <p class="faint" style={{ marginTop: 12 }}>Загрузите выписки по всем своим картам — тогда переводы между ними не будут считаться тратами.</p>
    </div>
  );
}
