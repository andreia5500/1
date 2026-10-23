import type { ComponentChildren } from 'preact';
import { useEffect } from 'preact/hooks';
import { catInfo } from '../core/categories';

export function Money({ v, sign, className = '' }: { v: number; sign?: boolean; className?: string }) {
  const abs = Math.abs(v);
  const s = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: abs >= 100 ? 0 : 2, minimumFractionDigits: 0 }).format(abs);
  const prefix = v < 0 ? '−' : sign && v > 0 ? '+' : '';
  return <span class={'num ' + className}>{prefix}{s} ₽</span>;
}

export function money(v: number): string {
  const abs = Math.abs(v);
  return (v < 0 ? '−' : '') + new Intl.NumberFormat('ru-RU', { maximumFractionDigits: abs >= 100 ? 0 : 2 }).format(abs) + ' ₽';
}

export function Dot({ category }: { category: string }) {
  return <span class="dot" style={{ background: catInfo(category).color }} />;
}

export function Sheet({ onClose, children }: { onClose: () => void; children: ComponentChildren }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', h);
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, []);
  return (
    <div class="scrim" onClick={e => e.target === e.currentTarget && onClose()}>
      <div class="sheet" role="dialog" aria-modal="true"><div class="grip" />{children}</div>
    </div>
  );
}

export function Bar({ value, max, color, marker }: { value: number; max: number; color: string; marker?: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const mk = marker && max > 0 ? Math.min(100, (marker / max) * 100) : undefined;
  return (
    <div class="bar">
      <i style={{ width: pct + '%', background: color }} />
      {mk !== undefined && <b style={{ left: `calc(${mk}% - 1px)` }} />}
    </div>
  );
}

const P = { fill: 'none', stroke: 'currentColor', 'stroke-width': 1.7, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' } as const;
export const Icons = {
  overview: <svg viewBox="0 0 24 24" {...P}><rect x="3" y="4" width="18" height="16" /><path d="M3 14h18M11 14v6" /></svg>,
  ops: <svg viewBox="0 0 24 24" {...P}><path d="M4 6h16M4 12h16M4 18h10" /></svg>,
  plan: <svg viewBox="0 0 24 24" {...P}><path d="M4 19l5-6 4 3 7-9" /><path d="M15 7h5v5" /></svg>,
  debts: <svg viewBox="0 0 24 24" {...P}><rect x="3" y="6" width="18" height="12" rx="1" /><path d="M3 10h18M7 15h4" /></svg>,
  accounts: <svg viewBox="0 0 24 24" {...P}><path d="M6 3h9l4 4v14H6z" /><path d="M14 3v5h5M9 13h7M9 17h5" /></svg>,
  left: <svg viewBox="0 0 24 24" width="22" height="22" {...P}><path d="M15 5l-7 7 7 7" /></svg>,
  right: <svg viewBox="0 0 24 24" width="22" height="22" {...P}><path d="M9 5l7 7-7 7" /></svg>,
  upload: <svg viewBox="0 0 24 24" width="22" height="22" {...P}><path d="M12 16V4M7 9l5-5 5 5M4 20h16" /></svg>,
  close: <svg viewBox="0 0 24 24" width="22" height="22" {...P}><path d="M6 6l12 12M18 6L6 18" /></svg>,
};
