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
  const [confirm, setConfirm] = useState<null | { title: string; text: string; run: () => void }>(null);
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
      <div class="btns" style={{ marginTop: 0 }}><ImportButton primary /></div>
      <p class="faint" style={{ marginTop: 8 }}>Удобнее всего — из приложения банка: «Поделиться» на PDF-выписке → это приложение. Повторная загрузка той же выписки не создаёт дублей.</p>

      <h2>Счета</h2>
      {!data.accounts.length && <p class="muted">Пока ничего не загружено.</p>}
      {data.accounts.map(a => {
        const sts = data.statements.filter(s => s.accountId === a.id);
        const n = data.txs.filter(t => t.accountId === a.id).length;
        return (
          <div class="rows" style={{ padding: '10px', marginTop: 10 }} key={a.id}>
            <div class="cat" style={{ padding: 0, border: 0 }}><div class="head"><span class="grow"><b>{a.title}</b></span>
              {a.kind === 'credit' ? <Money v={-(a.debt ?? 0)} className="neg" /> : a.balance !== undefined ? <Money v={a.balance} /> : null}</div></div>
            <div class="faint">{a.kind === 'credit' ? `долг${a.debtDate ? ' на ' + fmtDate(a.debtDate) : ''}` : `остаток${a.balanceDate ? ' на ' + fmtDate(a.balanceDate) : ''}`} · {n} операций</div>
            {sts.map(s => (
              <div key={s.id} style={{ fontSize: 13.5, marginTop: 6 }}>
                {fmtDate(s.periodFrom)} — {fmtDate(s.periodTo)}:{' '}
                {s.verified ? <span class="pos">сверено с итогами выписки</span> : <span class="neg">не сошлось с итогами ({money(s.parsedOut)} из {money(s.totalOut)})</span>}
              </div>
            ))}
            <div class="btns"><button class="btn small danger" onClick={() => setConfirm({
              title: `Удалить «${a.title}»?`, text: `Будут удалены ${n} операций и выписки этого счёта. Ваши правила категорий сохранятся.`,
              run: () => { update(d => removeAccount(d, a.id)); toast('Счёт удалён'); },
            })}>Удалить счёт</button></div>
          </div>
        );
      })}

      <h2>Мои счета в других банках</h2>
      <p class="faint">Переводы в отмеченные банки считаются переводами себе, а не тратами. Банки, чьи выписки загружены, учитываются автоматически.</p>
      <div class="rows" style={{ paddingInline: 8 }}>
        {BANKS.filter(b => !importedBanks.has(b.key as any)).map(b => (
          <label class="row" key={b.key} style={{ cursor: 'pointer' }}>
            <input type="checkbox" style={{ width: 20, height: 20, accentColor: 'var(--blue)' }} checked={data.settings.ownBanks.includes(b.key)} onChange={e => toggleBank(b.key, e.currentTarget.checked)} />
            <span class="grow">{b.name}</span>
          </label>
        ))}
      </div>

      <h2>Спросить ИИ</h2>
      <p class="muted">Соберу обезличенную сводку: категории, суммы, долги и цели — без ФИО, номеров карт, счетов и телефонов. Её можно вставить в GigaChat, Claude или другой ИИ и попросить совет.</p>
      <div class="btns"><button class="btn" onClick={() => setAi(true)} disabled={!txs.length}>Показать сводку для ИИ</button></div>

      <h2>Резервная копия</h2>
      <p class="muted">Данные хранятся только на телефоне. При удалении приложения они пропадут — сохраните копию (в Telegram «Избранное», на Диск или в Файлы).</p>
      <div class="btns">
        <button class="btn" onClick={backup} disabled={!data.accounts.length}>Сохранить копию</button>
        <button class="btn" onClick={() => restoreRef.current?.click()}>Восстановить из копии</button>
        <input ref={restoreRef} type="file" accept="application/json,.json" hidden onChange={async e => {
          const input = e.currentTarget; const f = input.files?.[0]; input.value = '';
          if (!f) return;
          try {
            const obj = JSON.parse(await f.text());
            if (!isAppData(obj)) throw new Error('это не резервная копия этого приложения');
            setConfirm({ title: 'Восстановить из копии?', text: `В копии ${obj.accounts.length} счетов и ${obj.txs.length} операций. Текущие данные будут заменены.`, run: () => { update(() => ({ ...emptyData(), ...obj, settings: { ...emptyData().settings, ...obj.settings } })); toast('Данные восстановлены'); } });
          } catch (err: any) { toast('Не получилось прочитать файл: ' + err.message); }
        }} />
      </div>

      <h2>Удаление</h2>
      <div class="btns" style={{ marginTop: 0 }}>
        <button class="btn danger" onClick={() => setConfirm({ title: 'Удалить все данные?', text: 'Счета, операции, лимиты, цели и правила будут удалены с телефона. Отменить нельзя.', run: async () => { await wipeData(); update(() => emptyData()); toast('Все данные удалены'); } })}>Удалить все данные</button>
      </div>
      <p class="faint" style={{ marginTop: 24 }}>Версия {__APP_VERSION__}. Поддерживаются выписки: СберБанк (дебетовые и кредитные карты), Т-Банк (выписка по договору). Приложение никуда не отправляет ваши данные.</p>

      {ai && <AiSheet onClose={() => setAi(false)} />}
      {confirm && (
        <Sheet onClose={() => setConfirm(null)}>
          <h2 style={{ marginTop: 0 }}>{confirm.title}</h2>
          <p class="muted">{confirm.text}</p>
          <div class="btns">
            <button class="btn danger" onClick={() => { confirm.run(); setConfirm(null); }}>Да</button>
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
    <Sheet onClose={onClose}>
      <h2 style={{ marginTop: 0 }}>Сводка для ИИ</h2>
      <p class="faint">Проверьте текст перед отправкой. Персональных данных в нём нет.</p>
      <pre class="ai">{text}</pre>
      <div class="btns">
        <button class="btn primary" onClick={async () => { toast((await copyText(text)) ? 'Скопировано — вставьте в чат с ИИ' : 'Не удалось скопировать'); }}>Скопировать</button>
        <button class="btn" onClick={() => shareText(text, 'Сводка финансов')}>Поделиться</button>
      </div>
    </Sheet>
  );
}
