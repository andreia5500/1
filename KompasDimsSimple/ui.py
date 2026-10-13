"""Оформление «Технолог 2.0»: единая тема, шапки окон, чертёжный фон, значки.

Все окна строятся одинаково: шапка (название + путь к файлу), рабочая
область по шагам 1-2-3, внизу слева «Журнал», справа «Закрыть» и одна
главная синяя кнопка действия.
"""
import math
import tkinter as tk
from tkinter import ttk, font

APP_NAME = 'Технолог 2.0'

# Палитра: инженерная «синька» + светлая рабочая область.
BG = '#EEF2F6'          # фон рабочих окон
PAPER = '#FFFFFF'
TEXT = '#17212E'
MUTED = '#5E6D80'
LINE = '#D3DCE6'
BLUE = '#1565C0'        # главное действие
BLUE_HOVER = '#1E74D6'
BLUE_PRESS = '#0D4A94'
NAVY = '#0C2340'        # шапки и боковая панель
NAVY_2 = '#13325A'
NAVY_TEXT = '#E8F0FA'
NAVY_MUTED = '#9FB4CF'
OK = '#2E7D32'
WARN = '#A15C00'
ERROR = '#C62828'
# Чертёжный лист («синька»)
PRINT_BG = '#0F355E'
PRINT_MINOR = '#16416F'
PRINT_MAJOR = '#215283'
PRINT_LINE = '#8DB7E6'
PRINT_THIN = '#5E8DC2'
PRINT_TEXT = '#D6E6FA'

UI_FONT = 'Segoe UI'
MONO_FONT = 'Consolas'


def theme(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
        font.nametofont(name).configure(family=UI_FONT, size=10)
    root.configure(background=BG)
    for key, value in (('*background', BG), ('*foreground', TEXT), ('*Listbox.background', PAPER),
                       ('*Listbox.selectBackground', '#D6E6FB'), ('*Listbox.selectForeground', TEXT),
                       ('*Listbox.highlightThickness', 1), ('*Listbox.highlightBackground', LINE),
                       ('*Listbox.highlightColor', BLUE), ('*Listbox.relief', 'flat'),
                       ('*Text.background', PAPER), ('*Text.highlightThickness', 1),
                       ('*Text.highlightBackground', LINE), ('*Text.highlightColor', BLUE), ('*Text.relief', 'flat'),
                       ('*TCombobox*Listbox.background', PAPER), ('*TCombobox*Listbox.font', (UI_FONT, 10))):
        root.option_add(key, value)
    style.configure('.', background=BG, foreground=TEXT, font=(UI_FONT, 10))
    style.configure('TFrame', background=BG)
    style.configure('Paper.TFrame', background=PAPER)
    style.configure('Card.TFrame', background=PAPER, relief='solid', borderwidth=1, bordercolor=LINE)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('Paper.TLabel', background=PAPER)
    style.configure('Title.TLabel', font=(UI_FONT, 18, 'bold'))
    style.configure('Heading.TLabel', font=(UI_FONT, 11, 'bold'))
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('Big.TLabel', font=(UI_FONT, 26, 'bold'), foreground=NAVY)
    style.configure('Ok.TLabel', foreground=OK)
    style.configure('Warn.TLabel', foreground=WARN)
    style.configure('Error.TLabel', foreground=ERROR)
    # шапка окна
    style.configure('Banner.TFrame', background=NAVY)
    style.configure('Banner.TLabel', background=NAVY, foreground=NAVY_TEXT, font=(UI_FONT, 17, 'bold'))
    style.configure('BannerMuted.TLabel', background=NAVY, foreground=NAVY_MUTED, font=(UI_FONT, 9))
    style.configure('TLabelframe', background=BG, bordercolor=LINE, relief='solid', borderwidth=1)
    style.configure('TLabelframe.Label', background=BG, font=(UI_FONT, 10, 'bold'), foreground=NAVY)
    # кнопки: обычная (обводка), главная (синяя), в шапке (на тёмном)
    style.configure('TButton', padding=(14, 7), background=PAPER, foreground=TEXT, bordercolor='#BFCCDA',
                    lightcolor=PAPER, darkcolor=PAPER, relief='flat', focuscolor=BLUE, font=(UI_FONT, 10))
    style.map('TButton', background=[('disabled', '#EEF1F5'), ('pressed', '#DCE8F8'), ('active', '#EEF4FD')],
              foreground=[('disabled', '#9AA6B4')],
              bordercolor=[('disabled', '#DDE3EA'), ('focus', BLUE), ('active', '#8FB0DA')])
    style.configure('Accent.TButton', background=BLUE, foreground=PAPER, bordercolor=BLUE,
                    lightcolor=BLUE, darkcolor=BLUE, font=(UI_FONT, 10, 'bold'), padding=(18, 8))
    style.map('Accent.TButton', background=[('disabled', '#DCE3EC'), ('pressed', BLUE_PRESS), ('active', BLUE_HOVER)],
              foreground=[('disabled', '#8C99AA'), ('!disabled', PAPER)],
              bordercolor=[('disabled', '#DCE3EC'), ('!disabled', BLUE)],
              lightcolor=[('active', BLUE_HOVER)], darkcolor=[('active', BLUE_HOVER)])
    style.configure('Banner.TButton', background=NAVY_2, foreground=NAVY_TEXT, bordercolor='#2F5584',
                    lightcolor=NAVY_2, darkcolor=NAVY_2, padding=(12, 6))
    style.map('Banner.TButton', background=[('active', '#1D4472'), ('pressed', '#0A1C33')],
              foreground=[('disabled', '#6F86A3')], bordercolor=[('active', '#5D86B8')])
    # боковая навигация
    style.configure('Nav.TButton', background=NAVY, foreground=NAVY_TEXT, bordercolor=NAVY, lightcolor=NAVY,
                    darkcolor=NAVY, anchor='w', padding=(18, 9), font=(UI_FONT, 10), relief='flat')
    style.map('Nav.TButton', background=[('active', '#17385F'), ('pressed', '#0A1C33')],
              foreground=[('disabled', '#6F86A3')], bordercolor=[('active', '#17385F')])
    style.configure('NavActive.TButton', background='#1B3F6B', foreground=PAPER, bordercolor='#1B3F6B',
                    lightcolor='#1B3F6B', darkcolor='#1B3F6B', anchor='w', padding=(18, 9), font=(UI_FONT, 10, 'bold'))
    style.map('NavActive.TButton', background=[('active', '#22507F')])
    # поля
    style.configure('TEntry', fieldbackground=PAPER, padding=6, bordercolor='#BFCCDA', lightcolor=PAPER)
    style.map('TEntry', bordercolor=[('focus', BLUE)])
    style.configure('TCombobox', fieldbackground=PAPER, background=PAPER, padding=5, bordercolor='#BFCCDA',
                    arrowcolor=MUTED, arrowsize=14)
    style.map('TCombobox', fieldbackground=[('readonly', PAPER), ('disabled', '#EEF1F5')],
              foreground=[('disabled', '#9AA6B4'), ('readonly', TEXT)], selectbackground=[('readonly', PAPER)],
              selectforeground=[('readonly', TEXT)], bordercolor=[('focus', BLUE)])
    style.configure('TCheckbutton', background=BG)
    style.configure('Paper.TCheckbutton', background=PAPER)
    style.configure('TNotebook', background=BG, bordercolor=LINE, tabmargins=(0, 4, 0, 0))
    style.configure('TNotebook.Tab', padding=(16, 7), background='#E2E8EF', foreground=MUTED, bordercolor=LINE,
                    font=(UI_FONT, 10))
    style.map('TNotebook.Tab', background=[('selected', PAPER)], foreground=[('selected', NAVY)],
              font=[('selected', (UI_FONT, 10, 'bold'))])
    style.configure('Treeview', background=PAPER, fieldbackground=PAPER, foreground=TEXT,
                    rowheight=max(28, font.nametofont('TkDefaultFont').metrics('linespace') + 10),
                    bordercolor=LINE, borderwidth=1, font=(UI_FONT, 10))
    style.configure('Treeview.Heading', background='#E4EBF3', foreground=NAVY,
                    font=(UI_FONT, 10, 'bold'), padding=(8, 8), relief='flat')
    style.map('Treeview', background=[('selected', '#D6E6FB')], foreground=[('selected', '#0D3A73')])
    style.map('Treeview.Heading', background=[('active', '#D8E2EE')])
    style.configure('TScrollbar', background='#C7D2DF', troughcolor=BG, arrowcolor=MUTED,
                    bordercolor=BG, lightcolor=BG, darkcolor=BG, arrowsize=13)
    style.configure('TProgressbar', background=BLUE, troughcolor='#DCE4EE', bordercolor=BG, thickness=6)
    style.configure('TPanedwindow', background=BG)
    return style


def window(win, title, width, height, min_width=850, min_height=550):
    win.title(title if title.startswith(APP_NAME) else '%s · %s' % (title, APP_NAME))
    win.configure(background=BG)
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    width = min(width, sw - 60)
    height = min(height, sh - 100)
    win.minsize(min(min_width, width), min(min_height, height))
    win.geometry('%dx%d+%d+%d' % (width, height, max(0, (sw - width) // 2), max(0, (sh - height) // 2 - 20)))


def header(parent, title, subtitle=None, icon=None):
    """Тёмная шапка окна: значок, название, подпись. Возвращает правую панель для кнопок."""
    band = tk.Frame(parent, background=NAVY, height=74)
    band.pack(fill='x')
    band.pack_propagate(False)
    mark = tk.Canvas(band, width=46, height=46, background=NAVY, highlightthickness=0)
    mark.pack(side='left', padx=(18, 12))
    draw_icon(mark, icon or 'logo', 23, 23, 40, PRINT_LINE, NAVY)
    text = tk.Frame(band, background=NAVY)
    text.pack(side='left', fill='y', pady=(12, 10))
    ttk.Label(text, text=title, style='Banner.TLabel').pack(anchor='w')
    if subtitle:
        label = ttk.Label(text, text=subtitle, style='BannerMuted.TLabel')
        label.pack(anchor='w')
    right = ttk.Frame(band, style='Banner.TFrame')
    right.pack(side='right', padx=16)
    tk.Frame(parent, background=BLUE, height=3).pack(fill='x')
    return right


def dialog(parent, title, width=520, height=330):
    win = tk.Toplevel(parent)
    had_grab = parent.grab_current() == parent
    window(win, title, width, height, min_width=width, min_height=height)
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)

    def close():
        win.destroy()
        if had_grab and parent.winfo_exists():
            parent.grab_set()
    win.protocol('WM_DELETE_WINDOW', close)
    win.bind('<Escape>', lambda e: close())
    win._close = close

    def fit():
        if win.winfo_exists():
            window(win, title, max(width, win.winfo_reqwidth() + 20), max(height, win.winfo_reqheight() + 20), width, height)
    win.after_idle(fit)
    return win


def table_scroll(table):
    parent = table.master
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)
    vertical = ttk.Scrollbar(parent, orient='vertical', command=table.yview)
    horizontal = ttk.Scrollbar(parent, orient='horizontal', command=table.xview)
    table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    table.grid(row=0, column=0, sticky='nsew')
    vertical.grid(row=0, column=1, sticky='ns')
    horizontal.grid(row=1, column=0, sticky='ew')
    table.tag_configure('stripe', background='#F6F8FB')


def journal_button(parent, owner, style='TButton'):
    import debug_log as J
    button = ttk.Button(parent, text='Журнал отладки', command=lambda: J.show_window(owner), style=style)
    button._allow_busy = True
    return button


def busy(root, yes):
    if yes:
        saved = []

        def visit(widget):
            if getattr(widget, '_is_debug_window', False):
                return
            if not getattr(widget, '_allow_busy', False) and widget.winfo_class() in ('TButton', 'TCombobox', 'TCheckbutton', 'Listbox'):
                saved.append((widget, widget.cget('state')))
                widget.configure(state='disabled')
            for child in widget.winfo_children():
                visit(child)
        visit(root)
        root._busy_widgets = saved
    else:
        for widget, state in getattr(root, '_busy_widgets', []):
            if widget.winfo_exists():
                widget.configure(state=state)
        root._busy_widgets = []


# ---------------------------------------------------------------- чертёжный фон

def blueprint(canvas, width, height):
    """Синька: сетка 5/25 мм, деталь «вал» с размерами, рамка и штамп."""
    canvas.delete('bp')
    canvas.configure(background=PRINT_BG)
    for x in range(0, width, 12):
        canvas.create_line(x, 0, x, height, fill=PRINT_MAJOR if x % 60 == 0 else PRINT_MINOR, tags='bp')
    for y in range(0, height, 12):
        canvas.create_line(0, y, width, y, fill=PRINT_MAJOR if y % 60 == 0 else PRINT_MINOR, tags='bp')
    m = 18
    canvas.create_rectangle(m, m, width - m, height - m, outline=PRINT_THIN, width=1, tags='bp')
    canvas.create_rectangle(m + 30, m + 6, width - m - 6, height - m - 6, outline=PRINT_LINE, width=2, tags='bp')
    # штамп (основная надпись) в правом нижнем углу
    sw, sh = min(370, width // 3), 110
    x0, y0 = width - m - 6 - sw, height - m - 6 - sh
    canvas.create_rectangle(x0, y0, x0 + sw, y0 + sh, outline=PRINT_LINE, width=2, tags='bp')
    for k in (22, 44, 66, 88):
        canvas.create_line(x0, y0 + k, x0 + sw * 0.42, y0 + k, fill=PRINT_THIN, tags='bp')
    canvas.create_line(x0 + sw * 0.42, y0, x0 + sw * 0.42, y0 + sh, fill=PRINT_LINE, width=2, tags='bp')
    canvas.create_line(x0 + sw * 0.42, y0 + 44, x0 + sw, y0 + 44, fill=PRINT_LINE, width=2, tags='bp')
    canvas.create_text(x0 + sw * 0.71, y0 + 22, text=APP_NAME.upper(), fill=PRINT_TEXT, font=(UI_FONT, 13, 'bold'), tags='bp')
    canvas.create_text(x0 + sw * 0.71, y0 + 76, text='Технологическая\nподготовка производства', fill=PRINT_LINE,
                       font=(UI_FONT, 9), justify='center', tags='bp')
    for i, t in enumerate(('Разраб.', 'Пров.', 'Т.контр.', 'Н.контр.', 'Утв.')):
        canvas.create_text(x0 + 6, y0 + 11 + i * 22, text=t, anchor='w', fill=PRINT_THIN, font=(UI_FONT, 8, 'italic'), tags='bp')
    # вал: ступенчатый профиль с осью и размерами (правая верхняя часть листа)
    free = x0 - 140 - (m + 70)
    if free > 260 and height - m - 210 > 560:  # ниже карточек модулей
        _shaft(canvas, m + 70, height - m - 160, min(520, free))


def _shaft(c, x, y, w):
    steps = [(0.00, 0.20, 26), (0.20, 0.46, 40), (0.46, 0.70, 32), (0.70, 0.86, 22), (0.86, 1.00, 16)]
    axis = y + 64
    c.create_line(x - 16, axis, x + w + 16, axis, fill=PRINT_THIN, dash=(18, 4, 3, 4), tags='bp')
    prev = None
    for a, b, h in steps:
        xa, xb = x + a * w, x + b * w
        c.create_rectangle(xa, axis - h, xb, axis + h, outline=PRINT_LINE, width=2, tags='bp')
        if prev is not None:
            c.create_line(xa, axis - min(h, prev), xa, axis + min(h, prev), fill=PRINT_LINE, width=2, tags='bp')
        prev = h
    # фаска и канавка
    c.create_line(x + w - 6, axis - 16, x + w, axis - 10, fill=PRINT_LINE, width=2, tags='bp')
    c.create_line(x + w - 6, axis + 16, x + w, axis + 10, fill=PRINT_LINE, width=2, tags='bp')
    # размер длины снизу
    ly = axis + 62
    c.create_line(x, axis + 30, x, ly + 6, fill=PRINT_THIN, tags='bp')
    c.create_line(x + w, axis + 20, x + w, ly + 6, fill=PRINT_THIN, tags='bp')
    c.create_line(x, ly, x + w, ly, fill=PRINT_LINE, arrow='both', arrowshape=(9, 10, 3), tags='bp')
    c.create_text(x + w / 2, ly - 9, text='120 ±0,2', fill=PRINT_TEXT, font=(UI_FONT, 9, 'italic'), tags='bp')
    # диаметр крупной ступени
    dx = x + 0.33 * w
    c.create_line(dx, axis - 40, dx, axis - 96, fill=PRINT_THIN, tags='bp')
    c.create_line(dx - 30, axis - 88, dx + 30, axis - 88, fill=PRINT_THIN, tags='bp')
    c.create_text(dx + 4, axis - 104, text='Ø40h7', fill=PRINT_TEXT, font=(UI_FONT, 9, 'italic'), anchor='w', tags='bp')
    c.create_text(x + 0.78 * w, axis - 48, text='Ra 0,8', fill=PRINT_TEXT, font=(UI_FONT, 9, 'italic'), tags='bp')
    c.create_line(x + 0.74 * w, axis - 40, x + 0.76 * w, axis - 26, x + 0.80 * w, axis - 54, fill=PRINT_LINE, tags='bp')


# ---------------------------------------------------------------- значки модулей

def draw_icon(c, kind, cx, cy, size, color, bg=PAPER):
    """Простые векторные значки (линии в стиле чертежа)."""
    s = size / 2
    w = max(2, int(size / 18))
    if kind == 'logo':
        c.create_oval(cx - s + 2, cy - s + 2, cx + s - 2, cy + s - 2, outline=color, width=w)
        c.create_line(cx - s * 0.55, cy + s * 0.35, cx, cy - s * 0.5, cx + s * 0.55, cy + s * 0.35, fill=color, width=w)
        c.create_line(cx - s * 0.3, cy + s * 0.02, cx + s * 0.3, cy + s * 0.02, fill=color, width=w)
        c.create_oval(cx - 3, cy - s * 0.5 - 3, cx + 3, cy - s * 0.5 + 3, fill=color, outline=color)
    elif kind == 'drawing':      # штангенциркуль
        c.create_rectangle(cx - s, cy - s * 0.25, cx + s, cy + s * 0.05, outline=color, width=w)
        c.create_line(cx - s * 0.75, cy - s * 0.25, cx - s * 0.75, cy - s * 0.85, fill=color, width=w)
        c.create_line(cx - s * 0.35, cy - s * 0.25, cx - s * 0.35, cy - s * 0.65, fill=color, width=w)
        c.create_line(cx - s * 0.75, cy + s * 0.05, cx - s * 0.75, cy + s * 0.75, fill=color, width=w)
        c.create_line(cx - s * 0.35, cy + s * 0.05, cx - s * 0.35, cy + s * 0.55, fill=color, width=w)
        for k in range(6):
            xx = cx + k * s * 0.22 - s * 0.1
            c.create_line(xx, cy - s * 0.25, xx, cy - s * 0.1, fill=color)
    elif kind == 'card':         # карта контроля
        c.create_rectangle(cx - s * 0.75, cy - s, cx + s * 0.75, cy + s, outline=color, width=w)
        for k in range(4):
            yy = cy - s * 0.55 + k * s * 0.42
            c.create_line(cx - s * 0.45, yy, cx - s * 0.3, yy + s * 0.12, cx - s * 0.08, yy - s * 0.15, fill=color, width=w)
            c.create_line(cx + s * 0.05, yy, cx + s * 0.55, yy, fill=color, width=w)
    elif kind == 'sketch':       # допуски на эскизе
        c.create_line(cx - s, cy + s * 0.2, cx + s, cy + s * 0.2, fill=color, width=w, arrow='both', arrowshape=(8, 9, 3))
        c.create_line(cx - s, cy - s * 0.7, cx - s, cy + s * 0.5, fill=color, width=w)
        c.create_line(cx + s, cy - s * 0.7, cx + s, cy + s * 0.5, fill=color, width=w)
        c.create_text(cx, cy - s * 0.25, text='±', fill=color, font=(UI_FONT, int(size * 0.38), 'bold'))
    elif kind == 'tools':        # ведомость оснастки — резец
        c.create_polygon(cx - s, cy + s * 0.2, cx + s * 0.35, cy + s * 0.2, cx + s * 0.35, cy - s * 0.25, cx - s, cy - s * 0.25,
                         outline=color, fill='', width=w)
        c.create_polygon(cx + s * 0.35, cy + s * 0.2, cx + s, cy + s * 0.75, cx + s * 0.35, cy - s * 0.25,
                         outline=color, fill='', width=w)
        c.create_line(cx - s * 0.7, cy - s * 0.7, cx + s * 0.2, cy - s * 0.7, fill=color, width=w)
        c.create_line(cx - s * 0.7, cy - s * 0.95, cx + s * 0.6, cy - s * 0.95, fill=color, width=w)
    elif kind == 'pages':        # нумерация листов
        for k, d in enumerate((0.3, 0.15, 0)):
            c.create_rectangle(cx - s * 0.7 + d * s, cy - s + d * s, cx + s * 0.55 + d * s, cy + s * 0.75 + d * s,
                               outline=color, fill=bg, width=w)
        c.create_text(cx + s * 0.2, cy + s * 0.35, text='2', fill=color, font=(UI_FONT, int(size * 0.36), 'bold'))
    elif kind == 'nc':           # проверка УП — экран ЧПУ с часами
        c.create_rectangle(cx - s, cy - s * 0.8, cx + s * 0.6, cy + s * 0.6, outline=color, width=w)
        c.create_text(cx - s * 0.2, cy - s * 0.1, text='G', fill=color, font=(MONO_FONT, int(size * 0.32), 'bold'))
        c.create_oval(cx + s * 0.15, cy + s * 0.05, cx + s, cy + s * 0.9, outline=color, fill=bg, width=w)
        c.create_line(cx + s * 0.575, cy + s * 0.475, cx + s * 0.575, cy + s * 0.2, fill=color, width=w)
        c.create_line(cx + s * 0.575, cy + s * 0.475, cx + s * 0.8, cy + s * 0.5, fill=color, width=w)
    elif kind == 'home':
        c.create_polygon(cx - s, cy, cx, cy - s, cx + s, cy, outline=color, fill='', width=w)
        c.create_rectangle(cx - s * 0.65, cy, cx + s * 0.65, cy + s * 0.9, outline=color, width=w)


def fmt_time(ms):
    """мм:сс,с — как на станке."""
    total = max(0.0, ms / 1000.0)
    minutes = int(total // 60)
    return '%d:%04.1f' % (minutes, total - minutes * 60)
