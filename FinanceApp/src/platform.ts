// Связь с Android: приём PDF через «Поделиться», сохранение резервной копии
import { Capacitor, registerPlugin } from '@capacitor/core';
import { Filesystem, Directory, Encoding } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';

export interface SharedFile { name: string; data: string } // data — base64

interface SharedPdfPlugin { take(): Promise<{ files: SharedFile[] }> }
const SharedPdf = registerPlugin<SharedPdfPlugin>('SharedPdf');

export const isNative = () => Capacitor.isNativePlatform();

/** Забрать PDF, присланные в приложение через «Поделиться» / «Открыть с помощью» */
export async function takeSharedFiles(): Promise<{ name: string; bytes: Uint8Array }[]> {
  if (!isNative()) return [];
  try {
    const r = await SharedPdf.take();
    return (r.files ?? []).map(f => ({ name: f.name, bytes: base64ToBytes(f.data) }));
  } catch {
    return [];
  }
}

export function onAppResume(cb: () => void) {
  window.addEventListener('sharedpdf', cb);
  document.addEventListener('resume', cb);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') cb(); });
}

export function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

/** Сохранить файл: на телефоне — через меню «Поделиться» (Диск, Telegram, Файлы…), в браузере — скачиванием */
export async function shareFile(name: string, text: string, title: string) {
  if (isNative()) {
    const res = await Filesystem.writeFile({ path: name, data: text, directory: Directory.Cache, encoding: Encoding.UTF8 });
    await Share.share({ title, files: [res.uri], dialogTitle: title });
    return;
  }
  const blob = new Blob([text], { type: name.endsWith('.json') ? 'application/json' : 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

export async function shareText(text: string, title: string) {
  if (isNative()) { await Share.share({ title, text, dialogTitle: title }); return; }
  await copyText(text);
}

export async function copyText(text: string): Promise<boolean> {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* ниже запасной способ */ }
  const ta = document.createElement('textarea');
  ta.value = text; document.body.appendChild(ta); ta.select();
  const ok = document.execCommand('copy');
  ta.remove();
  return ok;
}
