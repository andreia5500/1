// Уведомления на телефон: за день до постоянного платежа и в день зарплаты
import { LocalNotifications } from '@capacitor/local-notifications';
import { isNative } from './platform';
import { advise, rub } from './core/advisor';
import type { AppData, ClassifiedTx } from './core/types';
import { addDays, fmtDate } from './core/util';

export async function enableNotifications(): Promise<boolean> {
  if (!isNative()) return false;
  const p = await LocalNotifications.requestPermissions();
  return p.display === 'granted';
}

const at = (date: string, hour: number) => {
  const [y, m, d] = date.split('-').map(Number);
  return new Date(y, m - 1, d, hour, 0, 0);
};

export async function syncNotifications(data: AppData, txs: ClassifiedTx[], today: string) {
  if (!isNative()) return;
  const pending = await LocalNotifications.getPending();
  if (pending.notifications.length) await LocalNotifications.cancel({ notifications: pending.notifications.map(n => ({ id: n.id })) });
  if (!data.settings.notifications) return;

  const a = advise(data, txs, today, 35);
  const now = Date.now();
  const list: { id: number; title: string; body: string; schedule: { at: Date; allowWhileIdle: boolean } }[] = [];
  let id = 1000;
  for (const u of a.upcoming) {
    if (u.occ.p.type !== 'payment') continue;
    const when = at(addDays(u.occ.date, -1), 10);
    if (when.getTime() < now + 60_000) continue;
    const status = u.status === 'short'
      ? `Не хватит ≈ ${rub(-u.after)} — пополните карту заранее.`
      : u.status === 'tight' ? `После платежа останется около ${rub(u.after)}.` : 'Денег хватает.';
    list.push({
      id: id++,
      title: `Завтра: ${u.occ.p.title} — ${rub(u.occ.p.amount)}`,
      body: status,
      schedule: { at: when, allowWhileIdle: true },
    });
  }
  for (const w of a.warnings.filter(w => w.level === 'info' && w.date)) {
    const when = at(w.date!, 12);
    if (when.getTime() < now + 60_000) continue;
    list.push({ id: id++, title: w.title, body: w.text, schedule: { at: when, allowWhileIdle: true } });
  }
  for (const w of a.warnings.filter(w => w.level === 'danger' && w.date)) {
    // заранее, за 5 дней до проблемы (или завтра утром, если ближе)
    let d = addDays(w.date!, -5);
    if (d <= today) d = addDays(today, 1);
    if (d >= w.date!) continue;
    list.push({ id: id++, title: `Скоро может не хватить денег`, body: `${w.title}. Платёж ${fmtDate(w.date!).slice(0, 5)}.`, schedule: { at: at(d, 9), allowWhileIdle: true } });
  }
  if (list.length) await LocalNotifications.schedule({ notifications: list.slice(0, 60) });
}
