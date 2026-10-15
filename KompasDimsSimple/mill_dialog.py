"""Вкладки «HAAS» и «IMV» окна «Проверка УП»: файлы → установы → время и проверка.

Шаг 1 — перетащить файлы .nc в окно (или «Добавить файлы…»): основные
программы и подпрограммы вместе, в любом количестве. Каждая основная
программа (с M30/M02) — отдельный установ и отдельная карточка; подпрограммы
(M99) находятся по номеру O… во всех загруженных файлах.
Шаг 2 — расчёт идёт сразу: общее время сверху, карточки установов,
по двойному щелчку — инструменты, проверка кода с переходом к строке и время
по кадрам.
"""
import copy
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import debug_log as J
import dnd
import mill_engine as M
import transfer as X
import ui as U
from nc_dialog import CodeEditor, read_nc

NC_EXT = {'.nc', '.txt', '.tap', '.cnc', '.prg', '.ngc', '.mpf', '.eia', ''}
FILE_TYPES = [('Программы ЧПУ', '*.nc *.NC *.txt *.tap *.cnc *.prg *.ngc'), ('Все файлы', '*.*')]
CAT_NAMES = (('cut', 'резание', U.BLUE), ('rapid', 'ускоренные', U.GOLD), ('tool', 'смена инстр.', '#7C8796'),
             ('spindle', 'шпиндель', '#5B8C6A'), ('dwell', 'паузы', '#A0785A'), ('aux', 'M-коды', '#B9B2A3'))


def fmt_long(ms):
    total = max(0.0, ms / 1000.0)
    if total >= 3600:
        h = int(total // 3600)
        m = int((total - h * 3600) // 60)
        return '%d:%02d:%02d' % (h, m, int(round(total - h * 3600 - m * 60)))
    return U.fmt_time(ms)


def params_path(machine):
    return X.backup_folder() / ('mill_params_%s.json' % machine)


def load_params(machine):
    base = M.default_params(machine)
    try:
        saved = json.loads(params_path(machine).read_text(encoding='utf-8'))
        return M.merge_params(base, saved)
    except (OSError, ValueError, TypeError):
        return base


def save_params(machine, params):
    params_path(machine).write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding='utf-8')


def nc_files(paths):
    """Пути (файлы и папки) -> файлы УП. Папки просматриваются вложенно."""
    out, skipped = [], []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob('*')):
                if f.is_file() and f.suffix.lower() in NC_EXT:
                    out.append(f)
        elif p.is_file():
            (out if p.suffix.lower() in NC_EXT else skipped).append(p)
    return out, skipped


class MillTab(ttk.Frame):
    def __init__(self, parent, owner, machine):
        super().__init__(parent)
        self.owner = owner
        self.machine = machine
        self.params = load_params(machine)
        self.files = {}          # путь -> текст
        self.report = None
        self.last_dir = None
        bar = ttk.Frame(self)
        bar.pack(side='top', fill='x', pady=(10, 8))
        ttk.Button(bar, text='Добавить файлы…', style='Accent.TButton', command=self.add_files).pack(side='left')
        ttk.Button(bar, text='Папка…', command=self.add_folder).pack(side='left', padx=(8, 0))
        ttk.Button(bar, text='Очистить', command=self.clear).pack(side='left', padx=8)
        ttk.Button(bar, text='Параметры станка…', command=self.edit_params).pack(side='right')
        self.passport = ttk.Label(bar, style='Muted.TLabel')
        self.passport.pack(side='right', padx=12)
        self.update_passport()
        self.body = ttk.Frame(self)
        self.body.pack(fill='both', expand=True)
        self.show_empty()

    # ------------------------------------------------------------ файлы
    def update_passport(self):
        p = self.params
        self.passport.configure(text='%s · ускоренный %g%% · смена инструмента %g с · %s' % (
            p['model'], p['rapid_override_pct'], p['tool_change_s'],
            'кадры «/» пропускаются' if p['block_skip'] else 'кадры «/» выполняются'))

    def add_files(self):
        paths = filedialog.askopenfilenames(parent=self.owner, title='Программы %s' % M.TITLES[self.machine],
                                            filetypes=FILE_TYPES, initialdir=self.last_dir)
        if paths:
            self.load(paths)

    def add_folder(self):
        path = filedialog.askdirectory(parent=self.owner, title='Папка с программами', initialdir=self.last_dir)
        if path:
            self.load([path])

    def clear(self):
        self.files = {}
        self.report = None
        self.show_empty()
        self.owner.status.set('Список файлов очищен.')

    def load(self, paths):
        files, skipped = nc_files(paths)
        if not files:
            messagebox.showinfo('Проверка УП', 'Среди перетащенного нет файлов программ (.nc, .txt, .tap…).', parent=self.owner)
            return
        for f in files:
            try:
                self.files[str(f)] = read_nc(f).replace('\r\n', '\n').replace('\r', '\n')
            except OSError as exc:
                skipped.append(f)
                J.failure('Чтение УП', exc, path=str(f))
        self.last_dir = str(Path(files[0]).parent)
        J.event('Загружены УП фрезерного станка', machine=self.machine, files=[str(f) for f in files],
                skipped=[str(f) for f in skipped])
        self.calculate()
        if skipped:
            self.owner.status.set('Пропущены (не программы ЧПУ): %s' % ', '.join(Path(s).name for s in skipped[:6]))

    # ------------------------------------------------------------ расчёт
    def calculate(self):
        if not self.files:
            self.show_empty()
            return
        U.busy(self.owner, True)
        self.owner.configure(cursor='watch')
        self.owner.update_idletasks()
        try:
            names = {}
            for path, text in self.files.items():
                name = Path(path).name
                if name in names:      # одинаковые имена из разных папок
                    name = '%s (%s)' % (name, Path(path).parent.name)
                names[name] = path
            self.paths = names
            self.report = M.analyze([(n, self.files[p]) for n, p in names.items()], self.params)
        except Exception as exc:
            J.failure('Расчёт фрезерной УП', exc, machine=self.machine)
            messagebox.showerror('Проверка УП', 'Расчёт не выполнен: %s' % exc, parent=self.owner)
            return
        finally:
            U.busy(self.owner, False)
            self.owner.configure(cursor='')
        rep = self.report
        errors = sum(1 for s in rep['setups'] for i in s['issues'] if i['severity'] == 'error') + \
            sum(1 for i in rep['issues'] if i['severity'] == 'error')
        J.event('Расчёт фрезерной УП', machine=self.machine, total_ms=rep['total_ms'],
                setups=[(s['no'], round(s['ms'])) for s in rep['setups']], errors=errors)
        self.show_report()
        self.owner.status.set('%s: установов %d, общее время %s, ошибок %d. Двойной щелчок по карточке — подробности.' % (
            M.TITLES[self.machine], len(rep['setups']), fmt_long(rep['total_ms']), errors))

    # ------------------------------------------------------------ вид
    def clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    def show_empty(self):
        self.clear_body()
        c = tk.Canvas(self.body, background=U.PAPER, highlightthickness=0)
        c.pack(fill='both', expand=True)

        def draw(event=None):
            c.delete('all')
            w, h = c.winfo_width(), c.winfo_height()
            if w < 50:
                return
            c.create_rectangle(24, 24, w - 24, h - 24, outline='#C9BE9F', dash=(6, 5), width=2)
            cx, cy = w // 2, h // 2
            U.draw_icon(c, 'nc', cx, cy - 70, 64, U.BLUE, U.PAPER)
            c.create_text(cx, cy + 10, text='Перетащите сюда файлы программ %s' % M.TITLES[self.machine],
                          font=(U.UI_FONT, 15, 'bold'), fill=U.NAVY)
            c.create_text(cx, cy + 36, anchor='n', width=min(720, w - 80), justify='center', fill=U.MUTED, font=(U.UI_FONT, 10),
                          text='Можно сразу несколько файлов .nc и папки: основные программы (M30) станут установами, '
                               'подпрограммы (M99) найдутся по номеру O… — %s.\nИли нажмите «Добавить файлы…».' % (
                                   'вызов M98 P… (отдельные файлы O…) и M97 P… (метка N в той же программе)'
                                   if self.machine == 'haas' else 'вызов M98 P… (блоки O… в том же файле или в других файлах)'))
        c.bind('<Configure>', draw)
        c.bind('<Double-1>', lambda e: self.add_files())

    def show_report(self):
        self.clear_body()
        rep = self.report
        top = ttk.Frame(self.body, style='Card.TFrame', padding=(18, 12))
        top.pack(fill='x')
        left = ttk.Frame(top, style='Paper.TFrame')
        left.pack(side='left', fill='y')
        ttk.Label(left, text='ОБЩЕЕ ВРЕМЯ · %d %s' % (len(rep['setups']), plural(len(rep['setups']), 'установ', 'установа', 'установов')),
                  style='Muted.TLabel', background=U.PAPER).pack(anchor='w')
        incomplete = any(s['incomplete'] for s in rep['setups'])
        ttk.Label(left, text=fmt_long(rep['total_ms']), style='Big.TLabel', background=U.PAPER,
                  foreground=U.ERROR if incomplete else U.NAVY).pack(anchor='w')
        cats = {k: sum(s['cat'][k] for s in rep['setups']) for k, _, _ in CAT_NAMES}
        ttk.Label(left, text=self.cat_text(cats) + (' · есть неучтённые циклы' if incomplete else ''),
                  style='Muted.TLabel', background=U.PAPER).pack(anchor='w')
        bar = tk.Canvas(left, height=8, width=420, background=U.PAPER, highlightthickness=0)
        bar.pack(anchor='w', pady=(6, 0))
        self.draw_bar(bar, cats, 420)
        right = ttk.Frame(top, style='Paper.TFrame')
        right.pack(side='right', fill='both', expand=True, padx=(30, 0))
        subs = rep['subs']
        ttk.Label(right, text='Файлов: %d · установов: %d · подпрограмм: %d' % (len(self.files), len(rep['setups']), len(subs)),
                  style='Heading.TLabel', background=U.PAPER).pack(anchor='e')
        if subs:
            by_file = {}
            for sub in subs:
                by_file.setdefault(sub['file'], []).append(sub)
            parts = []
            for name, items in by_file.items():
                nums = ', '.join('O%s%s' % (x['no'], '' if x['used'] or x['own'] else ' (не вызывается)') for x in items[:6])
                parts.append('%s: %s%s' % (name, nums, ' … (%d)' % len(items) if len(items) > 6 else ''))
            ttk.Label(right, text='Подпрограммы — ' + '; '.join(parts[:6]), style='Muted.TLabel',
                      background=U.PAPER, wraplength=560, justify='right').pack(anchor='e', pady=(2, 0))
        for i in rep['issues'][:4]:
            ttk.Label(right, text=('✖ ' if i['severity'] == 'error' else '▲ ') + i['message'], background=U.PAPER,
                      foreground=U.ERROR if i['severity'] == 'error' else U.WARN, wraplength=560,
                      justify='right').pack(anchor='e', pady=(2, 0))
        # карточки
        holder = ttk.Frame(self.body)
        holder.pack(fill='both', expand=True, pady=(10, 0))
        canvas = tk.Canvas(holder, background=U.BG, highlightthickness=0)
        scroll = ttk.Scrollbar(holder, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = ttk.Frame(canvas)
        win = canvas.create_window(0, 0, window=inner, anchor='nw')
        cards = [self.card(inner, s) for s in rep['setups']]
        if not cards:
            ttk.Label(inner, text='Основных программ (с M30/M02) не найдено — загружены только подпрограммы.',
                      style='Muted.TLabel').grid(row=0, column=0, padx=10, pady=20)

        def layout(event=None):
            width = canvas.winfo_width()
            cols = max(1, width // 330)
            for k, card in enumerate(cards):
                card.grid(row=k // cols, column=k % cols, padx=(0, 12), pady=(0, 12), sticky='nsew')
            for col in range(6):
                inner.columnconfigure(col, weight=1 if col < cols else 0, uniform='card' if col < cols else '')
            canvas.itemconfigure(win, width=width)
            canvas.configure(scrollregion=(0, 0, width, inner.winfo_reqheight()))
        canvas.bind('<Configure>', layout)
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=(0, 0, canvas.winfo_width(), inner.winfo_reqheight())))
        wheel = lambda e: canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), 'units')
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', wheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

    @staticmethod
    def cat_text(cats):
        return ' · '.join('%s %s' % (name, fmt_long(cats[k])) for k, name, _ in CAT_NAMES if cats.get(k, 0) >= 500)

    @staticmethod
    def draw_bar(canvas, cats, width, names=CAT_NAMES):
        total = sum(cats.values()) or 1
        x = 0
        canvas.create_rectangle(0, 0, width, 8, fill='#ECE7DC', outline='')
        for k, _, color in names:
            w = width * cats.get(k, 0) / total
            if w >= 1:
                canvas.create_rectangle(x, 0, x + w, 8, fill=color, outline='')
                x += w

    def card(self, parent, s):
        card = ttk.Frame(parent, style='Card.TFrame', padding=(14, 10))
        errors = sum(1 for i in s['issues'] if i['severity'] == 'error')
        warns = sum(1 for i in s['issues'] if i['severity'] != 'error' and i['certain'])
        hints = sum(1 for i in s['issues'] if i['severity'] != 'error' and not i['certain'])
        row = ttk.Frame(card, style='Paper.TFrame')
        row.pack(fill='x')
        ttk.Label(row, text='O' + s['no'], font=(U.UI_FONT, 12, 'bold'), background=U.PAPER, foreground=U.NAVY).pack(side='left')
        ttk.Label(row, text=s['file'], style='Muted.TLabel', background=U.PAPER).pack(side='right')
        ttk.Label(card, text=s['title'] or '—', background=U.PAPER, wraplength=290, foreground=U.TEXT).pack(anchor='w', pady=(2, 4))
        line = ttk.Frame(card, style='Paper.TFrame')
        line.pack(fill='x')
        ttk.Label(line, text=fmt_long(s['ms']), font=(U.UI_FONT, 22, 'bold'), background=U.PAPER,
                  foreground=U.ERROR if s['incomplete'] else U.NAVY).pack(side='left')
        if s['alt_ms'] is not None and abs(s['alt_ms'] - s['ms']) > 500:
            ttk.Label(line, text='%s\nс кадрами «/»: %s' % ('кадры «/» пропущены' if s['block_skip'] else 'кадры «/» выполнены',
                                                           fmt_long(s['alt_ms'])),
                      style='Muted.TLabel', background=U.PAPER, justify='right').pack(side='right')
        bar = tk.Canvas(card, height=6, width=290, background=U.PAPER, highlightthickness=0)
        bar.pack(fill='x', pady=(4, 4))
        bar.bind('<Configure>', lambda e, c=bar: (c.delete('all'), self.draw_bar(c, s['cat'], e.width)))
        holes = sum(t['holes'] for t in s['tools'])
        ttk.Label(card, text='резание %s · инстр. %d%s' % (
            fmt_long(s['cat']['cut']), len(s['tools']), (' · отв. %d' % holes) if holes else ''),
            style='Muted.TLabel', background=U.PAPER).pack(anchor='w')
        if errors:
            text, color = '✖ Ошибок: %d%s' % (errors, (' · ▲ %d' % warns) if warns else ''), U.ERROR
        elif warns:
            text, color = '▲ Предупреждений: %d' % warns, U.WARN
        else:
            text, color = '✔ Ошибок не найдено', U.OK
        if hints:
            text += ' · ? %d' % hints
        ttk.Label(card, text=text, background=U.PAPER, foreground=color, font=(U.UI_FONT, 10, 'bold')).pack(anchor='w', pady=(4, 0))
        first = next((i for i in s['issues'] if i['severity'] == 'error'), None) or next(
            (i for i in s['issues'] if i['certain']), None)
        if first:
            ttk.Label(card, text='стр. %s: %s' % (first['line'] or '—', first['message']), background=U.PAPER, foreground=U.MUTED,
                      wraplength=290, justify='left').pack(anchor='w')
        ttk.Label(card, text='Двойной щелчок — подробности', style='Muted.TLabel', background=U.PAPER,
                  font=(U.UI_FONT, 8)).pack(anchor='e', pady=(4, 0))

        def bind(widget):
            widget.bind('<Double-1>', lambda e: self.open_setup(s))
            for ch in widget.winfo_children():
                bind(ch)
        bind(card)
        return card

    def open_setup(self, setup):
        SetupWindow(self, setup)

    # ------------------------------------------------------------ параметры
    def edit_params(self):
        p = copy.deepcopy(self.params)
        w = U.dialog(self.owner, 'Параметры станка · %s' % M.TITLES[self.machine], 700, 640)
        body = ttk.Frame(w, padding=16)
        body.pack(fill='both', expand=True)
        rows = []

        def field(label, getter, setter, kind='entry', values=None, col=0):
            r = len([x for x in rows if x[2] == col])
            ttk.Label(body, text=label).grid(row=r, column=col * 2, sticky='w', pady=3, padx=(0 if col == 0 else 24, 8))
            var = tk.StringVar(value=str(getter()))
            if kind == 'combo':
                ttk.Combobox(body, textvariable=var, values=values, state='readonly', width=16).grid(row=r, column=col * 2 + 1, sticky='w', pady=3)
            else:
                ttk.Entry(body, textvariable=var, width=12).grid(row=r, column=col * 2 + 1, sticky='w', pady=3)
            rows.append((var, setter, col))
            return var

        num = lambda key: (lambda: p[key], lambda v: p.update({key: float(v)}))
        if self.machine == 'haas':
            def set_model(v):
                p['model'] = v
                p['travel'] = dict(M.HAAS_MODELS[v])
            field('Модель', lambda: p['model'], set_model, 'combo', list(M.HAAS_MODELS))
        field('Ускоренный ход, %', lambda: '%g' % p['rapid_override_pct'], lambda v: p.update(rapid_override_pct=float(v)),
              'combo', ['25', '50', '100'])
        for a in ('X', 'Y', 'Z'):
            field('Ускоренный %s, мм/мин' % a, lambda a=a: '%g' % p['rapid'][a], lambda v, a=a: p['rapid'].update({a: float(v)}))
        field('Поворот A, °/мин', lambda: '%g' % p['rapid']['A'], lambda v: p['rapid'].update(A=float(v)))
        field('Разгон до ускоренного, мс', *num('accel_ms'))
        field('Разгон на подаче, мс', *num('feed_accel_ms'))
        field('Макс. подача, мм/мин', *num('max_feed'))
        field('Макс. обороты, об/мин', *num('max_rpm'))
        field('Смена инструмента, с', *num('tool_change_s'), col=1)
        field('Разгон шпинделя до макс., с', *num('spindle_ramp_s'), col=1)
        field('Реверс в G84, с', *num('tap_reverse_s'), col=1)
        field('Ориентация M19, с', *num('orient_s'), col=1)
        field('Отвод G73, мм', *num('peck_retract'), col=1)
        field('Зазор G83, мм', *num('peck_clear'), col=1)
        field('M-код по умолчанию, с', *num('m_default_s'), col=1)
        if self.machine == 'imv':
            modes = {'fanuc': 'FANUC (Q>0, K — повторы)', 'hnc8': 'HNC-8 (Q<0, K — отвод, L — повторы)'}
            field('Совместимость циклов (010083)', lambda: modes[p['cycle_mode']],
                  lambda v: p.update(cycle_mode=next(k for k, t in modes.items() if t == v)), 'combo', list(modes.values()), col=1)
        field('Кадры «/»', lambda: 'пропускать' if p['block_skip'] else 'выполнять',
              lambda v: p.update(block_skip=v == 'пропускать'), 'combo', ['пропускать', 'выполнять'], col=1)
        field('M01', lambda: 'останавливает' if p['optional_stop'] else 'пропускается',
              lambda v: p.update(optional_stop=v == 'останавливает'), 'combo', ['пропускается', 'останавливает'], col=1)
        r0 = max(len([x for x in rows if x[2] == 0]), len([x for x in rows if x[2] == 1])) + 1
        ttk.Label(body, text='Ход станка и положение нуля детали (машинные координаты, для проверки выхода за ход)',
                  style='Heading.TLabel').grid(row=r0, column=0, columnspan=4, sticky='w', pady=(14, 4))
        grid = ttk.Frame(body)
        grid.grid(row=r0 + 1, column=0, columnspan=4, sticky='w')
        for k, a in enumerate(('X', 'Y', 'Z')):
            ttk.Label(grid, text=a).grid(row=0, column=k * 3, padx=(0 if k == 0 else 18, 6))
            tv = tk.StringVar(value='%g' % p['travel'][a])
            zv = tk.StringVar(value='%g' % p['part_zero'][a])
            ttk.Entry(grid, textvariable=tv, width=8).grid(row=0, column=k * 3 + 1)
            ttk.Entry(grid, textvariable=zv, width=8).grid(row=0, column=k * 3 + 2, padx=(4, 0))
            rows.append((tv, lambda v, a=a: p['travel'].update({a: float(v)}), 9))
            rows.append((zv, lambda v, a=a: p['part_zero'].update({a: float(v)}), 9))
        ttk.Label(body, text='В каждой паре: ход, мм · ноль детали (Z — с учётом вылета инструмента), мм.\n'
                  'Значения по умолчанию — паспортные/типовые; уточните по своему станку. Сохраняются отдельно для каждого станка.',
                  style='Muted.TLabel', wraplength=640).grid(row=r0 + 2, column=0, columnspan=4, sticky='w', pady=(8, 0))
        bar = ttk.Frame(w, padding=(16, 0, 16, 16))
        bar.pack(fill='x')

        def apply():
            try:
                for var, setter, _ in rows:
                    setter(var.get().replace(',', '.').strip())
            except (ValueError, StopIteration, KeyError):
                messagebox.showerror('Параметры станка', 'Проверьте числовые значения.', parent=w)
                return
            self.params = p
            save_params(self.machine, p)
            J.event('Параметры фрезерного станка сохранены', machine=self.machine, path=str(params_path(self.machine)))
            w._close()
            self.update_passport()
            if self.files:
                self.calculate()

        def reset():
            if messagebox.askyesno('Параметры станка', 'Вернуть параметры по умолчанию?', parent=w):
                self.params = M.default_params(self.machine)
                save_params(self.machine, self.params)
                w._close()
                self.update_passport()
                if self.files:
                    self.calculate()
        ttk.Button(bar, text='Сохранить', style='Accent.TButton', command=apply).pack(side='right')
        ttk.Button(bar, text='Отмена', command=w._close).pack(side='right', padx=8)
        ttk.Button(bar, text='По умолчанию', command=reset).pack(side='left')


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


class SetupWindow(tk.Toplevel):
    """Подробности установа: текст программы слева, справа — сводка, инструменты, проверка, по кадрам."""

    def __init__(self, tab, setup):
        super().__init__(tab.owner)
        self.tab = tab
        self.setup = setup
        title = 'O%s · %s' % (setup['no'], setup['file'])
        U.window(self, title, 1360, 860, 1000, 620)
        U.header(self, title, '%s · %s · время %s' % (getattr(tab, 'machine_title', None) or M.TITLES[tab.machine], setup['title'] or 'без названия',
                                                     fmt_long(setup['ms'])), icon='nc')
        bar = ttk.Frame(self)
        bar.pack(side='bottom', fill='x', padx=16, pady=(8, 12))
        ttk.Button(bar, text='Закрыть', command=self.destroy).pack(side='right')
        U.journal_button(bar, self).pack(side='left')
        panes = ttk.Panedwindow(self, orient='horizontal')
        panes.pack(fill='both', expand=True, padx=16, pady=(12, 0))
        left = ttk.Frame(panes)
        panes.add(left, weight=4)
        right = ttk.Frame(panes)
        panes.add(right, weight=5)
        top = ttk.Frame(left)
        top.pack(fill='x', pady=(0, 6))
        ttk.Label(top, text='Файл:').pack(side='left')
        files = [setup['file']] + sorted({i['file'] for i in setup['issues'] if i['file'] and i['file'] != setup['file']} |
                                         {b['file'] for b in setup['blocks'] if b['file'] != setup['file']})
        self.file_box = ttk.Combobox(top, values=files, state='readonly', width=40)
        self.file_box.pack(side='left', padx=6)
        self.file_box.bind('<<ComboboxSelected>>', lambda e: self.show_file(self.file_box.get()))
        self.editor = CodeEditor(left)
        self.editor.pack(fill='both', expand=True)
        self.book = ttk.Notebook(right)
        self.book.pack(fill='both', expand=True, padx=(12, 0))
        self.summary_tab()
        self.tools_tab()
        self.check_tab()
        self.blocks_tab()
        self.current = None
        self.show_file(setup['file'])
        if any(i['severity'] == 'error' for i in setup['issues']):
            self.book.select(2)

    def show_file(self, name, line=None):
        if name != self.current:
            path = self.tab.paths.get(name)
            text = self.tab.files.get(path, '') if path else ''
            self.editor.set(text)
            self.current = name
            self.file_box.set(name)
            self.editor.mark([i['line'] for i in self.setup['issues'] if i['file'] == name and i['severity'] == 'error' and i['line']])
        if line:
            self.editor.goto(line)

    def summary_tab(self):
        s = self.setup
        page = ttk.Frame(self.book, padding=14)
        self.book.add(page, text='Сводка')
        ttk.Label(page, text='ВРЕМЯ УСТАНОВА', style='Muted.TLabel').pack(anchor='w')
        ttk.Label(page, text=fmt_long(s['ms']), style='Big.TLabel', foreground=U.ERROR if s['incomplete'] else U.NAVY).pack(anchor='w')
        bar = tk.Canvas(page, height=10, background=U.BG, highlightthickness=0)
        bar.pack(fill='x', pady=(4, 10))
        bar.bind('<Configure>', lambda e: (bar.delete('all'), MillTab.draw_bar(bar, s['cat'], e.width)))
        frame = ttk.Frame(page)
        frame.pack(fill='x')
        table = ttk.Treeview(frame, columns=('cat', 'time', 'pct'), show='headings', height=6)
        for c, t, w in (('cat', 'Составляющая', 200), ('time', 'Время', 110), ('pct', 'Доля', 80)):
            table.heading(c, text=t)
            table.column(c, width=w, anchor='w' if c == 'cat' else 'center')
        U.table_scroll(table)
        total = s['ms'] or 1
        for k, name, _ in CAT_NAMES:
            table.insert('', 'end', values=(name, fmt_long(s['cat'][k]), '%.0f%%' % (100 * s['cat'][k] / total)))
        p = self.tab.params
        notes = ['Ускоренный ход %g%% (X/Y/Z %g/%g/%g мм/мин), смена инструмента %g с, разгон шпинделя до %g об/мин — %g с.' % (
            p['rapid_override_pct'], p['rapid']['X'], p['rapid']['Y'], p['rapid']['Z'], p['tool_change_s'], p['max_rpm'],
            p['spindle_ramp_s'])]
        if s['alt_ms'] is not None and abs(s['alt_ms'] - s['ms']) > 500:
            notes.append('Кадры с «/» %s. Если %s — время %s.' % (
                'пропущены' if s['block_skip'] else 'выполнены', 'выполнять их' if s['block_skip'] else 'пропустить их',
                fmt_long(s['alt_ms'])))
        if s['stops']:
            notes.append('Остановы M00/M01 в строках %s — время ожидания оператора не учтено.' % ', '.join(map(str, s['stops'][:12])))
        if s['incomplete']:
            notes.append('Часть программы не смоделирована (см. «Проверка кода») — время меньше реального.')
        span = s.get('span') or {}
        if span:
            notes.append('Размах перемещений: ' + ', '.join('%s %.1f…%.1f' % (a, lo, hi) for a, (lo, hi) in span.items()
                                                        if a != 'A' or hi - lo > 0))
        ttk.Label(page, text='\n'.join('• ' + n for n in notes), wraplength=560, justify='left').pack(anchor='w', pady=(12, 0))
        page.bind('<Configure>', lambda e: [w.configure(wraplength=max(300, e.width - 30)) for w in page.winfo_children()
                                            if isinstance(w, ttk.Label) and w.cget('wraplength')])

    def tools_tab(self):
        page = ttk.Frame(self.book, padding=14)
        self.book.add(page, text='Инструменты · %d' % len(self.setup['tools']))
        ttk.Label(page, text='В порядке смены. Двойной щелчок — к строке M6.', style='Muted.TLabel').pack(anchor='w', pady=(0, 8))
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        cols = (('n', '№', 34), ('t', 'T', 46), ('name', 'Инструмент', 150), ('hd', 'H / D', 70), ('s', 'S', 60),
                ('f', 'F', 110), ('holes', 'Отв.', 44), ('cut', 'Резание', 70), ('ms', 'Всего', 70))
        table = ttk.Treeview(frame, columns=[c[0] for c in cols], show='headings')
        for c, t, w in cols:
            table.heading(c, text=t)
            table.column(c, width=w, anchor='w' if c == 'name' else 'center', stretch=c == 'name')
        U.table_scroll(table)
        table.tag_configure('bad', foreground=U.ERROR)
        self.tool_rows = {}
        for k, t in enumerate(self.setup['tools']):
            hd = '/'.join(filter(None, [','.join('H%d' % h for h in t['H']), ','.join('D%d' % d for d in t['D'])]))
            f = ', '.join('%g' % x for x in t['F'][:4]) + (' …' if len(t['F']) > 4 else '')
            bad = (t['H'] and t['H'] != [t['T']]) or not t['H']
            iid = table.insert('', 'end', tags=('bad',) if bad else (('stripe',) if k % 2 else ()),
                               values=(k + 1, 'T%s' % t['T'], t['name'] or '—', hd or 'нет G43', ', '.join('%g' % x for x in t['S']),
                                       f, t['holes'] or '', fmt_long(t['cut_ms']), fmt_long(t['ms'])))
            self.tool_rows[iid] = (t['file'], t['line'])
        table.bind('<Double-1>', lambda e: self.jump(table, self.tool_rows, e))

    def check_tab(self):
        s = self.setup
        page = ttk.Frame(self.book, padding=14)
        errors = sum(1 for i in s['issues'] if i['severity'] == 'error')
        self.book.add(page, text='Проверка кода · %d' % len(s['issues']))
        ok = not errors
        ttk.Label(page, text='%s Ошибок: %d · предупреждений: %d' % ('✔' if ok else '✖', errors, len(s['issues']) - errors),
                  style='Ok.TLabel' if ok else 'Error.TLabel', font=(U.UI_FONT, 11, 'bold')).pack(anchor='w')
        ttk.Label(page, text='✖ — станок выдаст аварию или обработает не так; ▲ — проверьте; ? — эвристика. '
                  'Двойной щелчок — перейти к строке.', style='Muted.TLabel', wraplength=600).pack(anchor='w', pady=(2, 8))
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        table = ttk.Treeview(frame, columns=('sev', 'file', 'line', 'code', 'msg'), show='headings')
        for c, t, w in (('sev', '', 34), ('file', 'Файл', 100), ('line', 'Стр.', 55), ('code', 'Код', 90), ('msg', 'Описание', 520)):
            table.heading(c, text=t)
            table.column(c, width=w, anchor='w' if c == 'msg' else 'center', stretch=c == 'msg')
        U.table_scroll(table)
        table.tag_configure('error', foreground=U.ERROR)
        table.tag_configure('warning', foreground=U.WARN)
        table.tag_configure('uncertain', foreground=U.MUTED)
        rows = {}
        for i in s['issues']:
            tag = 'error' if i['severity'] == 'error' else ('warning' if i['certain'] else 'uncertain')
            mark = '✖' if tag == 'error' else ('▲' if tag == 'warning' else '?')
            iid = table.insert('', 'end', tags=(tag,), values=(mark, i['file'] or '', i['line'] or '', i['code'], i['message']))
            rows[iid] = (i['file'], i['line'])
        detail = ttk.Label(page, text='Выберите строку — здесь будет полное описание.' if rows else 'Замечаний нет.',
                           wraplength=600, justify='left')
        detail.pack(fill='x', pady=(8, 0))
        page.bind('<Configure>', lambda e: detail.configure(wraplength=max(300, e.width - 30)))
        table.bind('<<TreeviewSelect>>', lambda e: detail.configure(
            text=table.item(table.selection()[0], 'values')[4] if table.selection() else ''))
        table.bind('<Double-1>', lambda e: self.jump(table, rows, e))

    def blocks_tab(self):
        s = self.setup
        page = ttk.Frame(self.book, padding=14)
        self.book.add(page, text='По кадрам')
        ttk.Label(page, text='Кадры с временем в порядке выполнения (подпрограммы — в общем ходе). Двойной щелчок — к строке.',
                  style='Muted.TLabel').pack(anchor='w', pady=(0, 8))
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        table = ttk.Treeview(frame, columns=('file', 'line', 'raw', 'ms', 'sum', 'note'), show='headings')
        for c, t, w in (('file', 'Файл', 90), ('line', 'Стр.', 50), ('raw', 'Кадр', 200), ('ms', 'Время, с', 75),
                        ('sum', 'Нараст., мин:с', 95), ('note', 'Расчёт', 300)):
            table.heading(c, text=t)
            table.column(c, width=w, anchor='w' if c in ('raw', 'note') else 'center', stretch=c == 'note')
        U.table_scroll(table)
        rows = {}
        total = 0.0
        for k, b in enumerate(s['blocks'][:20000]):
            total += b['ms']
            iid = table.insert('', 'end', tags=('stripe',) if k % 2 else (),
                               values=(b['file'], b['line'], b['raw'][:60], '%.2f' % (b['ms'] / 1000), U.fmt_time(total), b['note']))
            rows[iid] = (b['file'], b['line'])
        if len(s['blocks']) > 20000:
            table.insert('', 'end', values=('', '', '… показаны первые 20 000 кадров', '', '', ''))
        table.bind('<Double-1>', lambda e: self.jump(table, rows, e))

    def jump(self, table, rows, event):
        iid = table.identify_row(event.y)
        if iid not in rows:
            return
        name, line = rows[iid]
        if name:
            self.show_file(name, line)


def build_tabs(window, book):
    """Добавить вкладки HAAS и IMV в notebook окна «Проверка УП» и подключить перетаскивание."""
    tabs = {}
    for machine, text in (('haas', 'HAAS VF-2/3'), ('imv', 'IMV 10.55')):
        tab = MillTab(book, window, machine)
        book.add(tab, text=text)
        tabs[machine] = tab

    def dropped(paths):
        current = book.nametowidget(book.select())
        if hasattr(current, 'load'):
            current.load(paths)
    window.dnd_enabled = dnd.enable(window, dropped)
    return tabs
