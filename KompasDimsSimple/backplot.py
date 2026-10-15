"""Прорисовка траектории (бэкплот) как в CIMCO: токарный вид Z–X и фрезерные XY / XZ / YZ / изометрия.

Сегменты: dict(kind, pts=[(x, y, z), …], line, file, tool, note).
  kind: rapid — ускоренный (красный пунктир), feed/cycle/groove/drill — рабочие (цвет инструмента),
        thread — резьба (оранжевый).
Токарный режим: точка (x, 0, z), где x — радиус (X/2); рисуется верхняя половина и
зеркальная нижняя, заготовка и деталь (модель lathe_check.Stock).
Щелчок по линии — переход к кадру (on_pick(file, line)); колесо — масштаб у курсора;
перетаскивание — сдвиг; ползунок — пошаговый проход по траектории.
"""
import math
import tkinter as tk
from tkinter import ttk

import ui as U

PALETTE = ('#2C4F8C', '#2E7D32', '#8E44AD', '#00838F', '#6D4C41', '#C2185B', '#3F51B5', '#558B2F', '#EF6C00', '#00695C',
           '#5D4037', '#1565C0', '#AD1457', '#4E342E')
RAPID = '#D9534F'
THREAD = '#E67E22'
PART = '#D7D1C2'
PART_EDGE = '#8C8576'
VIEWS = {
    'ZX': lambda p: (p[2], p[0]),
    'XY': lambda p: (p[0], p[1]),
    'XZ': lambda p: (p[0], p[2]),
    'YZ': lambda p: (p[1], p[2]),
    'ISO': lambda p: ((p[0] - p[1]) * 0.8660254, p[2] + (p[0] + p[1]) * 0.5),
}
VIEW_NAMES = {'XY': 'Сверху (XY)', 'XZ': 'Спереди (XZ)', 'YZ': 'Сбоку (YZ)', 'ISO': 'Изометрия'}


class Backplot(ttk.Frame):
    def __init__(self, parent, segments, mode='mill', stock=None, bar=None, markers=None, on_pick=None):
        super().__init__(parent)
        self.segments = segments
        self.mode = mode
        self.stock = stock
        self.bar = bar
        self.markers = markers or []        # dict(pt=(x, y, z), text, line, file)
        self.on_pick = on_pick
        self.view = 'ZX' if mode == 'lathe' else 'XY'
        self.tools = []
        for s in segments:
            if s.get('tool') and s['tool'] not in self.tools:
                self.tools.append(s['tool'])
        self.colors = {t: PALETTE[k % len(PALETTE)] for k, t in enumerate(self.tools)}
        self.selected = None
        self.scale = 1.0
        self.center = (0.0, 0.0)
        self._drag = None
        bar_ = ttk.Frame(self)
        bar_.pack(fill='x', pady=(0, 6))
        if mode != 'lathe':
            ttk.Label(bar_, text='Вид:').pack(side='left')
            self.view_box = ttk.Combobox(bar_, values=[VIEW_NAMES[k] for k in ('XY', 'XZ', 'YZ', 'ISO')], state='readonly', width=13)
            self.view_box.set(VIEW_NAMES['XY'])
            self.view_box.pack(side='left', padx=(4, 12))
            self.view_box.bind('<<ComboboxSelected>>', lambda e: self.set_view())
        ttk.Label(bar_, text='Инструмент:').pack(side='left')
        self.tool_box = ttk.Combobox(bar_, values=['Все'] + ['T' + t for t in self.tools], state='readonly', width=10)
        self.tool_box.set('Все')
        self.tool_box.pack(side='left', padx=(4, 12))
        self.tool_box.bind('<<ComboboxSelected>>', lambda e: self.redraw(fit=True))
        self.show_rapid = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar_, text='Ускоренные', variable=self.show_rapid, command=self.redraw).pack(side='left')
        if mode == 'lathe':
            self.show_part = tk.BooleanVar(value=True)
            ttk.Checkbutton(bar_, text='Деталь', variable=self.show_part, command=self.redraw).pack(side='left', padx=(8, 0))
        ttk.Button(bar_, text='Вписать', command=lambda: self.redraw(fit=True)).pack(side='right')
        self.canvas = tk.Canvas(self, background=U.PAPER, highlightthickness=1, highlightbackground=U.LINE)
        self.canvas.pack(fill='both', expand=True)
        self.hint = tk.StringVar(value='Щелчок по линии — к кадру; колесо — масштаб; перетаскивание — сдвиг.')
        sim = ttk.Frame(self)
        sim.pack(fill='x', pady=(6, 0))
        ttk.Label(sim, text='Проход по траектории:').pack(side='left')
        self.upto = tk.IntVar(value=len(segments))
        self.slider = ttk.Scale(sim, from_=0, to=max(1, len(segments)), orient='horizontal',
                                command=lambda v: self.on_slide(int(float(v))))
        self.slider.set(len(segments))
        self.slider.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Label(self, textvariable=self.hint, style='Muted.TLabel').pack(fill='x', pady=(4, 0))
        legend = ttk.Frame(self)
        legend.pack(fill='x')
        for text, color, dash in (('ускоренный', RAPID, True), ('рабочий', U.BLUE, False), ('резьба', THREAD, False)):
            c = tk.Canvas(legend, width=26, height=10, background=U.BG, highlightthickness=0)
            c.create_line(2, 5, 24, 5, fill=color, width=2, dash=(4, 3) if dash else None)
            c.pack(side='left')
            ttk.Label(legend, text=text, style='Muted.TLabel').pack(side='left', padx=(0, 10))
        if self.markers:
            c = tk.Canvas(legend, width=14, height=12, background=U.BG, highlightthickness=0)
            c.create_oval(2, 2, 11, 11, outline=U.ERROR, width=2)
            c.pack(side='left')
            ttk.Label(legend, text='место ошибки', style='Muted.TLabel').pack(side='left')
        self.canvas.bind('<Configure>', lambda e: self.redraw(fit=not getattr(self, '_fitted', False)))
        self.canvas.bind('<MouseWheel>', self.on_wheel)
        self.canvas.bind('<Button-4>', lambda e: self.zoom(e.x, e.y, 1.2))
        self.canvas.bind('<Button-5>', lambda e: self.zoom(e.x, e.y, 1 / 1.2))
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Motion>', self.on_motion)

    # ------------------------------------------------------------ геометрия
    def proj(self, p):
        return VIEWS[self.view](p)

    def to_screen(self, h, v):
        w, hh = self.canvas.winfo_width(), self.canvas.winfo_height()
        return (w / 2 + (h - self.center[0]) * self.scale, hh / 2 - (v - self.center[1]) * self.scale)

    def to_world(self, sx, sy):
        w, hh = self.canvas.winfo_width(), self.canvas.winfo_height()
        return (self.center[0] + (sx - w / 2) / self.scale, self.center[1] - (sy - hh / 2) / self.scale)

    def visible(self):
        tool = self.tool_box.get()
        n = self.upto.get()
        out = []
        for k, s in enumerate(self.segments[:n]):
            if tool != 'Все' and 'T' + str(s.get('tool')) != tool:
                continue
            if s['kind'] == 'rapid' and not self.show_rapid.get():
                continue
            out.append((k, s))
        return out

    def fit(self):
        pts = [self.proj(p) for _, s in self.visible() for p in s['pts'] if s['kind'] != 'rapid'] or \
            [self.proj(p) for _, s in self.visible() for p in s['pts']]
        if self.mode == 'lathe':
            pts = pts + [(h, -v) for h, v in pts]
            if self.stock is not None and self.bar:
                pts += [(self.stock.z0, self.bar / 2), (self.stock.z0, -self.bar / 2)]
        if not pts:
            return
        hs, vs = [p[0] for p in pts], [p[1] for p in pts]
        w, hh = max(50, self.canvas.winfo_width()), max(50, self.canvas.winfo_height())
        span_h, span_v = max(hs) - min(hs) or 1, max(vs) - min(vs) or 1
        self.scale = min((w - 40) / span_h, (hh - 40) / span_v)
        self.center = ((max(hs) + min(hs)) / 2, (max(vs) + min(vs)) / 2)
        self._fitted = True

    # ------------------------------------------------------------ рисование
    def redraw(self, fit=False):
        c = self.canvas
        if c.winfo_width() < 20:
            return
        if fit:
            self.fit()
        c.delete('all')
        self.draw_axes()
        if self.mode == 'lathe' and self.stock is not None and getattr(self, 'show_part', None) and self.show_part.get():
            self.draw_part()
        for k, s in self.visible():
            coords = []
            for p in s['pts']:
                coords.extend(self.to_screen(*self.proj(p)))
            if len(coords) < 4:
                continue
            color, width, dash = self.style(s)
            if k == self.selected:
                color, width = '#F2B705', width + 3
            c.create_line(*coords, fill=color, width=width, dash=dash, tags=('seg',))
        for m in self.markers:
            sx, sy = self.to_screen(*self.proj(m['pt']))
            c.create_oval(sx - 7, sy - 7, sx + 7, sy + 7, outline=U.ERROR, width=2)
            c.create_line(sx - 4, sy - 4, sx + 4, sy + 4, fill=U.ERROR, width=2)
            c.create_line(sx - 4, sy + 4, sx + 4, sy - 4, fill=U.ERROR, width=2)
        vis = self.visible()
        if vis and self.upto.get() < len(self.segments):
            last = vis[-1][1]['pts'][-1]
            sx, sy = self.to_screen(*self.proj(last))
            c.create_polygon(sx, sy, sx - 7, sy - 14, sx + 7, sy - 14, fill='#F2B705', outline=U.NAVY)

    def style(self, s):
        if s['kind'] == 'rapid':
            return RAPID, 1, (4, 3)
        if s['kind'] == 'thread':
            return THREAD, 1, None
        color = self.colors.get(s.get('tool'), U.BLUE)
        if s['kind'] == 'cycle' and not s.get('profile'):
            return self.light(color), 1, None
        return color, 2 if s['kind'] in ('feed', 'groove', 'drill') or s.get('profile') else 1, None

    @staticmethod
    def light(color):
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        return '#%02x%02x%02x' % tuple(int(v + (255 - v) * 0.55) for v in (r, g, b))

    def draw_axes(self):
        c = self.canvas
        w, h = c.winfo_width(), c.winfo_height()
        ox, oy = self.to_screen(0, 0)
        c.create_line(0, oy, w, oy, fill='#C9C2B4', dash=(8, 4) if self.mode == 'lathe' else (2, 4))
        c.create_line(ox, 0, ox, h, fill='#E3DED3', dash=(2, 4))
        names = {'ZX': ('Z', 'X'), 'XY': ('X', 'Y'), 'XZ': ('X', 'Z'), 'YZ': ('Y', 'Z'), 'ISO': ('', '')}[self.view]
        c.create_text(w - 12, oy - 10, text=names[0], fill=U.MUTED, font=(U.UI_FONT, 9, 'bold'))
        c.create_text(ox + 12, 12, text=names[1], fill=U.MUTED, font=(U.UI_FONT, 9, 'bold'))
        # линейка масштаба
        base = 10 ** math.floor(math.log10(60 / max(self.scale, 1e-9)))
        step = next(base * k for k in (1, 2, 5, 10) if base * k * self.scale >= 60)
        x0, y0 = 16, h - 16
        c.create_line(x0, y0, x0 + step * self.scale, y0, fill=U.NAVY, width=2)
        c.create_text(x0 + step * self.scale / 2, y0 - 9, text='%g мм' % step, fill=U.NAVY, font=(U.UI_FONT, 8))

    def draw_part(self):
        st, c = self.stock, self.canvas
        if self.bar:
            r = self.bar / 2
            z_end = st.z_of(st.n - 1)
            for sgn in (1, -1):
                a = self.to_screen(st.z0, sgn * r)
                b = self.to_screen(z_end, sgn * r)
                c.create_line(a[0], a[1], b[0], b[1], fill=PART_EDGE, dash=(3, 3))
        step = max(1, st.n // 1500)
        for sgn, fill in ((1, PART), (-1, '#E7E2D6')):
            top, bot = [], []
            for i in range(0, st.n, step):
                z = st.z_of(i)
                if st.R[i] <= st.B[i] + 1e-6:
                    if top:
                        self._poly(top, bot, fill)
                    top, bot = [], []
                    continue
                top.append(self.to_screen(z, sgn * st.R[i]))
                bot.append(self.to_screen(z, sgn * st.B[i]))
            if top:
                self._poly(top, bot, fill)

    def _poly(self, top, bot, fill):
        pts = top + bot[::-1]
        if len(pts) >= 3:
            flat = [v for p in pts for v in p]
            self.canvas.create_polygon(*flat, fill=fill, outline='')
            line = [v for p in top for v in p]
            if len(line) >= 4:
                self.canvas.create_line(*line, fill=PART_EDGE)

    # ------------------------------------------------------------ мышь
    def set_view(self):
        self.view = next(k for k, v in VIEW_NAMES.items() if v == self.view_box.get())
        self.redraw(fit=True)

    def on_slide(self, n):
        self.upto.set(n)
        if 0 < n <= len(self.segments):
            s = self.segments[n - 1]
            self.hint.set('Кадр %s · стр. %s · T%s · %s' % (n, s.get('line') or '—', s.get('tool') or '—', s.get('file') or ''))
        self.redraw()

    def on_wheel(self, e):
        self.zoom(e.x, e.y, 1.2 if e.delta > 0 else 1 / 1.2)

    def zoom(self, sx, sy, k):
        wx, wy = self.to_world(sx, sy)
        self.scale *= k
        nx, ny = self.to_world(sx, sy)
        self.center = (self.center[0] + wx - nx, self.center[1] + wy - ny)
        self.redraw()

    def on_press(self, e):
        self._drag = (e.x, e.y, self.center, False)

    def on_drag(self, e):
        if not self._drag:
            return
        x0, y0, c0, moved = self._drag
        if abs(e.x - x0) + abs(e.y - y0) > 4 or moved:
            self._drag = (x0, y0, c0, True)
            self.center = (c0[0] - (e.x - x0) / self.scale, c0[1] + (e.y - y0) / self.scale)
            self.redraw()

    def on_release(self, e):
        if self._drag and not self._drag[3]:
            k = self.nearest(e.x, e.y)
            if k is not None:
                self.selected = k
                s = self.segments[k]
                self.hint.set('Стр. %s · T%s · %s · %s' % (s.get('line') or '—', s.get('tool') or '—', s.get('file') or '',
                                                          s.get('note') or s['kind']))
                self.redraw()
                if self.on_pick and s.get('line'):
                    self.on_pick(s.get('file'), s['line'])
        self._drag = None

    def on_motion(self, e):
        wx, wy = self.to_world(e.x, e.y)
        axes = {'ZX': ('Z', 'X'), 'XY': ('X', 'Y'), 'XZ': ('X', 'Z'), 'YZ': ('Y', 'Z'), 'ISO': ('', '')}[self.view]
        if axes[0] and self.selected is None:
            if self.mode == 'lathe':
                self.hint.set('Z%.3f  X%.3f (Ø)' % (wx, abs(wy) * 2))
            else:
                self.hint.set('%s%.3f  %s%.3f' % (axes[0], wx, axes[1], wy))

    def nearest(self, sx, sy, tol=7):
        best, best_d = None, tol
        for k, s in self.visible():
            poly = [self.to_screen(*self.proj(p)) for p in s['pts']]
            for a, b in zip(poly, poly[1:]):
                d = _dist(sx, sy, a, b)
                if d < best_d:
                    best, best_d = k, d
        return best


def _dist(px, py, a, b):
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def lathe_segments(path, file_of):
    """Сегменты Simulator.path -> формат Backplot (x — радиус)."""
    out = []
    for s in path:
        if s['plane'] != 18:
            continue
        pts = [(x / 2, 0.0, z) for x, z in s['pts']]
        out.append(dict(kind=s['kind'], pts=pts, line=s['line'], file=file_of(s['prog']), tool=_tool(s.get('tool')),
                        profile=s['info'].get('profile')))
    return out


def _tool(raw):
    if raw is None:
        return None
    t = str(raw).strip()
    return t if t.isdigit() and int(t) else None
