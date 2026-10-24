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

export function Sheet({ onClose, title, children }: { onClose: () => void; title?: ComponentChildren; children: ComponentChildren }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', h);
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', h); document.body.style.overflow = ''; };
  }, []);
  return (
    <div class="scrim" onClick={e => e.target === e.currentTarget && onClose()}>
      <div class="sheet" role="dialog" aria-modal="true">
        <div class="grip" />
        {title !== undefined && (
          <div class="head">
            <h2>{title}</h2>
            <button class="icon-btn" aria-label="Закрыть" onClick={onClose}>{Icons.close}</button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

export function Bar({ value, max, color, marker, flush }: { value: number; max: number; color: string; marker?: number; flush?: boolean }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const mk = marker && max > 0 ? Math.min(100, (marker / max) * 100) : undefined;
  return (
    <div class={'bar' + (flush ? ' flush' : '')}>
      <i style={{ width: Math.max(pct, value > 0 ? 1.5 : 0) + '%', background: color }} />
      {mk !== undefined && <b style={{ left: `calc(${mk}% - 1px)` }} />}
    </div>
  );
}

const P = { fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' } as const;
const svg = (d: string, size = 22) => <svg width={size} height={size} viewBox="0 0 24 24" {...P}><path d={d} /></svg>;
export const Icons = {
  overview: svg('M4 5h16v14H4zM4 13h16M11 13v6'),
  ops: svg('M5 7h14M5 12h14M5 17h9'),
  payments: svg('M4 6h16v14H4zM4 10h16M8 3v5M16 3v5M8 14h3M8 17h6'),
  budget: svg('M4 18l5-6 4 3 7-8M15 7h5v5'),
  accounts: svg('M7 3h8l4 4v14H7zM14 3v5h5M10 13h6M10 17h4'),
  left: svg('M15 5l-7 7 7 7'),
  right: svg('M9 5l7 7-7 7'),
  chevron: svg('M9 5l7 7-7 7', 20),
  upload: svg('M12 15V4M7.5 8.5L12 4l4.5 4.5M5 15v4h14v-4', 20),
  close: svg('M6 6l12 12M18 6L6 18'),
  plus: svg('M12 5v14M5 12h14', 28),
  check: svg('M5 12.5l4.5 4.5L19 7.5', 18),
  bag: svg('M4 7h16l-1.5 11a2 2 0 0 1-2 1.7h-9A2 2 0 0 1 5.5 18L4 7zM9 7a3 3 0 0 1 6 0', 24),
  clock: svg('M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2', 18),
  bell: svg('M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20a2 2 0 0 0 4 0', 20),
};

export const uid = () => Math.random().toString(36).slice(2, 10);
export const num = (s: string) => Number(String(s).replace(/\s/g, '').replace(',', '.')) || 0;
