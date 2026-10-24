import { useMemo, useRef, useState } from 'preact/hooks';
import { useStore, isAppData, wipeData } from '../store';
import { BANKS } from '../core/categories';
import { removeAccount } from '../core/merge';
import { buildAiSummary } from '../core/aiSummary';
import { monthsAvailable } from '../core/analytics';
import { emptyData } from '../core/types';
import { fmtDate, todayIso } from '../core/util';
import { copyText, shareFile, shareText } from '../platform';
import { Money, Sheet, money } from './components';
import { ImportButton } from './App';

export function Accounts() {
  const { data, txs, update, toast } = useStore();
  const [ai, setAi] = useState(false);
  const [confirm, setConfirm] = useState<null | { title: string; text: string; run: () => void; ok?: string }>(null);
  const restoreRef = useRef<HTMLInputElement>(null);
  const importedBanks = new Set(data.accounts.map(a => a.bank));

  const toggleBank = (key: string, on: boolean) => update(d => ({
    ...d, settings: { ...d.settings, ownBanks: on ? [...new Set([...d.settings.ownBanks, key])] : d.settings.ownBanks.filter(k => k !== key) },
  }));

  const backup = async () => {
    try {
      await shareFile(`finance-backup-${todayIso()}.json`, JSON.stringify(data), 'Резервная копия');
    } catch (e: any) { toast('Не удалось сохранить: ' + (e?.message ?? e)); }
  };

  return (
    <>
      <div class="top"><h1>Выписки и счета</h1></div>
      <div class="pad">
        <ImportButton primary />
        <p class="small muted" style={{ marginTop: 10 }}>Удобнее всего — из приложения банка: «Поделиться» на PDF-выписке → «Мои финансы». Повторная загрузка той же выписки не создаёт дублей.</p>
      </div>

      <div class="sec-head"><h2>Счета</h2></div>
      {!data.accounts.length && <p class="muted pad">Пока ничего не загружено.</p>}
      {data.accounts.map((a, i) => {
        const sts = data.statements.filter(s => s.accountId === a.id);
        const n = data.txs.filter(t => t.accountId === a.id).length;
        return (
          <section class="card inner" key={a.id} style={{ marginTop: i ? 10 : 0 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
              <h3 style={{ flex: 1 }}>{a.title}</h3>
              {a.kind === 'credit' ? <Money v={-(a.debt ?? 0)} className="bold" /> : a.balance !== undefined ? <Money v={a.balance} className="bold" /> : null}
            </div>
            <p class="tiny muted" style={{ marginTop: 3 }}>{a.kind === 'credit' ? `долг${a.debtDate ? ' на ' + fmtDate(a.debtDate) : ''}` : `остаток${a.balanceDate ? ' на ' + fmtDate(a.balanceDate) : ''}`}, {n} операций</p>
            {sts.map(s => (
              <p key={s.id} class="small" style={{ marginTop: 6 }}>
                {fmtDate(s.periodFrom)} — {fmtDate(s.periodTo)}:{' '}
                {s.verified ? <span class="pos">сверено с итогами выписки</span> : <span class="neg">не сошлось с итогами ({money(s.parsedOut)} из {money(s.totalOut)})</span>}
              </p>
            ))}
            <div class="btns" style={{ marginTop: 10 }}><button class="btn small danger" onClick={() => setConfirm({
              title: `Удалить «${a.title}»?`, text: `Будут удалены ${n} операций и выписки этого счёта. Ваши правила категорий сохранятся.`,
              run: () => { update(d => removeAccount(d, a.id)); toast('Счёт удалён'); },
            })}>Удалить счёт</button></div>
          </section>
        );
      })}

      <div class="sec-head"><h2>Мои счета в других банках</h2></div>
      <p class="small muted pad" style={{ marginBottom: 10 }}>Переводы в отмеченные банки считаются переводами себе, а не тратами. Банки, чьи выписки загружены, учитываются автоматически.</p>
      <section class="card" style={{ padding: '2px 0' }}>
        {BANKS.filter(b => !importedBanks.has(b.key as any)).map(b => (
          <label class="row" key={b.key} style={{ cursor: 'pointer' }}>
            <input type="checkbox" style={{ width: 20, height: 20, accentColor: 'var(--acc)', margin: 0 }} checked={data.settings.ownBanks.includes(b.key)} onChange={e => toggleBank(b.key, e.currentTarget.checked)} />
            <span class="grow">{b.name}</span>
          </label>
        ))}
      </section>

      <div class="sec-head"><h2>Спросить ИИ</h2></div>
      <section class="card inner">
        <p class="small muted">Соберу обезличенную сводку: категории, суммы, постоянные платежи, долги и цели — без ФИО, номеров карт, счетов и телефонов. Её можно вставить в GigaChat, Claude или другой ИИ и попросить совет.</p>
        <div class="btns"><button class="btn" onClick={() => setAi(true)} disabled={!txs.length}>Показать сводку для ИИ</button></div>
      </section>

      <div class="sec-head"><h2>Резервная копия</h2></div>
      <section class="card inner">
        <p class="small muted">Данные хранятся только на телефоне. При удалении приложения они пропадут — сохраните копию в Telegram «Избранное», на Диск или в Файлы.</p>
        <div class="btns">
          <button class="btn" onClick={backup} disabled={!data.accounts.length && !data.txs.length}>Сохранить копию</button>
          <button class="btn" onClick={() => restoreRef.current?.click()}>Восстановить</button>
          <input ref={restoreRef} type="file" accept="application/json,.json" hidden onChange={async e => {
            const input = e.currentTarget; const f = input.files?.[0]; input.value = '';
            if (!f) return;
            try {
              const obj = JSON.parse(await f.text());
              if (!isAppData(obj)) throw new Error('это не резервная копия этого приложения');
              setConfirm({ ok: 'Восстановить', title: 'Восстановить из копии?', text: `В копии ${obj.accounts.length} счетов и ${obj.txs.length} операций. Текущие данные будут заменены.`, run: () => { update(() => ({ ...emptyData(), ...obj, settings: { ...emptyData().settings, ...obj.settings } })); toast('Данные восстановлены'); } });
            } catch (err: any) { toast('Не получилось прочитать файл: ' + err.message); }
          }} />
        </div>
      </section>

      <div class="pad" style={{ marginTop: 28 }}>
        <button class="btn danger" onClick={() => setConfirm({ title: 'Удалить все данные?', text: 'Счета, операции, постоянные платежи, лимиты, цели и правила будут удалены с телефона. Отменить нельзя.', run: async () => { await wipeData(); update(() => emptyData()); toast('Все данные удалены'); } })}>Удалить все данные</button>
        <p class="tiny muted" style={{ marginTop: 18 }}>Версия {__APP_VERSION__}. Поддерживаются выписки: СберБанк (дебетовые и кредитные карты), Т-Банк (выписка по договору). Приложение никуда не отправляет ваши данные.</p>
      </div>

      {ai && <AiSheet onClose={() => setAi(false)} />}
      {confirm && (
        <Sheet onClose={() => setConfirm(null)} title={confirm.title}>
          <p class="muted" style={{ marginTop: 4 }}>{confirm.text}</p>
          <div class="btns">
            <button class={'btn ' + (confirm.ok ? 'primary' : 'danger')} onClick={() => { confirm.run(); setConfirm(null); }}>{confirm.ok ?? 'Да, удалить'}</button>
            <button class="btn" onClick={() => setConfirm(null)}>Отмена</button>
          </div>
        </Sheet>
      )}
    </>
  );
}

function AiSheet({ onClose }: { onClose: () => void }) {
  const { data, txs, toast } = useStore();
  const text = useMemo(() => buildAiSummary(data, txs, monthsAvailable(txs), todayIso()), [data, txs]);
  return (
    <Sheet onClose={onClose} title="Сводка для ИИ">
      <p class="small muted" style={{ marginTop: 4, marginBottom: 10 }}>Проверьте текст перед отправкой. Персональных данных в нём нет.</p>
      <pre class="ai">{text}</pre>
      <div class="btns">
        <button class="btn primary" onClick={async () => { toast((await copyText(text)) ? 'Скопировано — вставьте в чат с ИИ' : 'Не удалось скопировать'); }}>Скопировать</button>
        <button class="btn" onClick={() => shareText(text, 'Сводка финансов')}>Поделиться</button>
      </div>
    </Sheet>
  );
}
