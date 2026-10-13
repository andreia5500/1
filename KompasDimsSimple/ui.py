"""Оформление «Технолог 2.0»: единая тема, шапки окон, чертёжный фон, значки.

Палитра — тёмный ин­ковый графит-навy + сдержанное золото как фирменный
акцент (логотип, рамка шапки, активный пункт навигации, штамп чертежа).
Акцент используется скупо — это держит интерфейс спокойным, но даёт тот
самый «дорогой» блеск там, где он уместен.

Все окна строятся одинаково: шапка (название + путь к файлу), рабочая
область по шагам 1-2-3, внизу слева «Журнал», справа «Закрыть» и одна
главная кнопка действия.
"""
import math
import tkinter as tk
from tkinter import ttk, font

APP_NAME = 'Технолог 2.0'

# ---------------------------------------------------------------- палитра
# Нейтральные тона — тёплый камень, не холодная синь: спокойнее для глаза
# при длительной работе и выглядит дороже, чем типовой «офисный» серо-синий.
BG = '#F3F1EC'          # фон рабочих окон — тёплый светлый камень
PAPER = '#FFFFFF'
TEXT = '#1B2430'        # графит с синим подтоном
MUTED = '#6E6A61'
LINE = '#E1DCD1'
BLUE = '#2C4F8C'        # главное действие — глубокий сапфир (не ярко-синий)
BLUE_HOVER = '#3A5FA0'
BLUE_PRESS = '#1E3A6B'
NAVY = '#0B1420'        # шапки и боковая панель — почти чёрный индиго
NAVY_2 = '#152233'      # вторичные тёмные панели / активный пункт навигации
NAVY_TEXT = '#ECEEF3'
NAVY_MUTED = '#8C94A6'
OK = '#2E7D32'
WARN = '#9C5B18'
ERROR = '#B23A3A'

# Золото — фирменный акцент. Использовать только там, где он подчёркивает
# бренд (логотип, разделительная линия шапки, активная навигация, штамп),
# а не как обычный интерфейсный цвет.
GOLD = '#C6A15B'
GOLD_HOVER = '#D4B36F'
GOLD_PRESS = '#A8863F'
GOLD_SOFT = '#4A3E26'   # мягкая золотая тень/подсветка на тёмном фоне

# Чертёжный лист («синька») — та же тёмная индиго-палитра, что и у шапок,
# чтобы главный экран и диалоги читались как единая дорогая система.
PRINT_BG = NAVY
PRINT_MINOR = '#16222E'
PRINT_MAJOR = '#213244'
PRINT_LINE = '#9FB8D9'
PRINT_THIN = '#5C7693'
PRINT_TEXT = '#E7EEF7'
SHADOW = '#05090E'      # мягкая тень под карточками на тёмном фоне

UI_FONT = 'Segoe UI'
MONO_FONT = 'Consolas'


def theme(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
        font.nametofont(name).configure(family=UI_FONT, size=10)
    root.configure(background=BG)
    for key, value in (('*background', BG), ('*foreground', TEXT), ('*Listbox.background', PAPER),
                       ('*Listbox.selectBackground', '#E4DCC4'), ('*Listbox.selectForeground', TEXT),
                       ('*Listbox.highlightThickness', 1), ('*Listbox.highlightBackground', LINE),
                       ('*Listbox.highlightColor', GOLD), ('*Listbox.relief', 'flat'),
                       ('*Text.background', PAPER), ('*Text.highlightThickness', 1),
                       ('*Text.highlightBackground', LINE), ('*Text.highlightColor', GOLD), ('*Text.relief', 'flat'),
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
    # кнопки: обычная (обводка), главная (сапфир), в шапке (на тёмном)
    style.configure('TButton', padding=(14, 7), background=PAPER, foreground=TEXT, bordercolor='#D4CDBD',
                    lightcolor=PAPER, darkcolor=PAPER, relief='flat', focuscolor=GOLD, font=(UI_FONT, 10))
    style.map('TButton', background=[('disabled', '#F1EFEA'), ('pressed', '#E9E3D3'), ('active', '#F6F1E6')],
              foreground=[('disabled', '#A6A096')],
              bordercolor=[('disabled', '#E6E1D5'), ('focus', GOLD), ('active', '#C9B98F')])
    style.configure('Accent.TButton', background=BLUE, foreground=PAPER, bordercolor=BLUE,
                    lightcolor=BLUE, darkcolor=BLUE, font=(UI_FONT, 10, 'bold'), padding=(18, 8))
    style.map('Accent.TButton', background=[('disabled', '#C9D1DE'), ('pressed', BLUE_PRESS), ('active', BLUE_HOVER)],
              foreground=[('disabled', '#8C99AA'), ('!disabled', PAPER)],
              bordercolor=[('disabled', '#C9D1DE'), ('!disabled', BLUE)],
              lightcolor=[('active', BLUE_HOVER)], darkcolor=[('active', BLUE_HOVER)])
    # фирменная «золотая» кнопка — для редких акцентных действий
    style.configure('Gold.TButton', background=GOLD, foreground=NAVY, bordercolor=GOLD,
                    lightcolor=GOLD, darkcolor=GOLD, font=(UI_FONT, 10, 'bold'), padding=(18, 8))
    style.map('Gold.TButton', background=[('disabled', '#E7DCC0'), ('pressed', GOLD_PRESS), ('active', GOLD_HOVER)],
              foreground=[('disabled', '#A6A096')], bordercolor=[('!disabled', GOLD)])
    style.configure('Banner.TButton', background=NAVY_2, foreground=NAVY_TEXT, bordercolor='#2C3C52',
                    lightcolor=NAVY_2, darkcolor=NAVY_2, padding=(12, 6))
    style.map('Banner.TButton', background=[('active', '#1C2C42'), ('pressed', '#070C13')],
              foreground=[('disabled', '#5C6576')], bordercolor=[('active', GOLD)])
    # боковая навигация
    style.configure('Nav.TButton', background=NAVY, foreground=NAVY_TEXT, bordercolor=NAVY, lightcolor=NAVY,
                    darkcolor=NAVY, anchor='w', padding=(16, 9), font=(UI_FONT, 10), relief='flat')
    style.map('Nav.TButton', background=[('active', '#172333'), ('pressed', '#070C13')],
              foreground=[('disabled', '#5C6576'), ('active', GOLD)], bordercolor=[('active', '#172333')])
    style.configure('NavActive.TButton', background=NAVY_2, foreground=GOLD, bordercolor=NAVY_2,
                    lightcolor=NAVY_2, darkcolor=NAVY_2, anchor='w', padding=(16, 9), font=(UI_FONT, 10, 'bold'))
    style.map('NavActive.TButton', background=[('active', NAVY_2)], foreground=[('active', GOLD)])
    # поля
    style.configure('TEntry', fieldbackground=PAPER, padding=6, bordercolor='#D4CDBD', lightcolor=PAPER)
    style.map('TEntry', bordercolor=[('focus', GOLD)])
    style.configure('TCombobox', fieldbackground=PAPER, background=PAPER, padding=5, bordercolor='#D4CDBD',
                    arrowcolor=MUTED, arrowsize=14)
    style.map('TCombobox', fieldbackground=[('readonly', PAPER), ('disabled', '#F1EFEA')],
              foreground=[('disabled', '#A6A096'), ('readonly', TEXT)], selectbackground=[('readonly', PAPER)],
              selectforeground=[('readonly', TEXT)], bordercolor=[('focus', GOLD)])
    style.configure('TCheckbutton', background=BG)
    style.configure('Paper.TCheckbutton', background=PAPER)
    style.configure('TNotebook', background=BG, bordercolor=LINE, tabmargins=(0, 4, 0, 0))
    style.configure('TNotebook.Tab', padding=(16, 7), background='#E8E3D7', foreground=MUTED, bordercolor=LINE,
                    font=(UI_FONT, 10))
    style.map('TNotebook.Tab', background=[('selected', PAPER)], foreground=[('selected', NAVY)],
              font=[('selected', (UI_FONT, 10, 'bold'))])
    style.configure('Treeview', background=PAPER, fieldbackground=PAPER, foreground=TEXT,
                    rowheight=max(28, font.nametofont('TkDefaultFont').metrics('linespace') + 10),
                    bordercolor=LINE, borderwidth=1, font=(UI_FONT, 10))
    style.configure('Treeview.Heading', background='#EAE5D9', foreground=NAVY,
                    font=(UI_FONT, 10, 'bold'), padding=(8, 8), relief='flat')
    style.map('Treeview', background=[('selected', '#E4DCC4')], foreground=[('selected', '#3A2F10')])
    style.map('Treeview.Heading', background=[('active', '#E2DCC9')])
    style.configure('TScrollbar', background='#D6CFBD', troughcolor=BG, arrowcolor=MUTED,
                    bordercolor=BG, lightcolor=BG, darkcolor=BG, arrowsize=13)
    style.configure('TProgressbar', background=GOLD, troughcolor='#E6E1D3', bordercolor=BG, thickness=6)
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
    """Тёмная шапка окна: золотой значок, название, подпись, тонкая золотая
    линия внизу — фирменный штрих, повторяющийся в каждом окне программы."""
    band = tk.Frame(parent, background=NAVY, height=74)
    band.pack(fill='x')
    band.pack_propagate(False)
    mark = tk.Canvas(band, width=46, height=46, background=NAVY, highlightthickness=0)
    mark.pack(side='left', padx=(18, 12))
    draw_icon(mark, icon or 'logo', 23, 23, 40, GOLD, NAVY)
    text = tk.Frame(band, background=NAVY)
    text.pack(side='left', fill='y', pady=(12, 10))
    ttk.Label(text, text=title, style='Banner.TLabel').pack(anchor='w')
    if subtitle:
        label = ttk.Label(text, text=subtitle, style='BannerMuted.TLabel')
        label.pack(anchor='w')
    right = ttk.Frame(band, style='Banner.TFrame')
    right.pack(side='right', padx=16)
    tk.Frame(parent, background=GOLD, height=2).pack(fill='x')
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
    table.tag_configure('stripe', background='#F8F6F1')


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


# ---------------------------------------------------------------- тон и тень

def _lerp(c1, c2, t):
    """Линейная интерполяция между двумя цветами '#rrggbb'."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgradient(canvas, x0, y0, x1, y1, top, bottom, tag, steps=48):
    """Мягкий вертикальный градиент — используется для «дорогой» подложки
    шапки главного экрана вместо плоской заливки."""
    height = max(1, y1 - y0)
    for i in range(steps):
        a = y0 + height * i / steps
        b = y0 + height * (i + 1) / steps
        canvas.create_rectangle(x0, a, x1, b + 1, outline='', fill=_lerp(top, bottom, i / max(1, steps - 1)), tags=tag)


def shadow(canvas, x, y, w, h, tag='shadow', offset=7, blur=3, color=SHADOW):
    """Мягкая многослойная тень-«подложка» под карточкой (имитация blur)."""
    for i in range(blur, 0, -1):
        d = offset + i * 2
        canvas.create_rectangle(x + d - blur, y + d - blur, x + w + d, y + h + d, outline='',
                                 fill=color, tags=tag, stipple='gray25' if i > 1 else '')


# ---------------------------------------------------------------- чертёжный фон

def blueprint(canvas, width, height):
    """Синька: сетка 5/25 мм, деталь «вал» с размерами, рамка и штамп.

    Верхняя треть — мягкий градиент (светлее к центру заголовка) и тонкая
    золотая линия под заголовком: фирменный, но сдержанный «вау»-штрих.
    """
    canvas.delete('bp')
    canvas.configure(background=PRINT_BG)
    vgradient(canvas, 0, 0, width, 210, '#182A3F', PRINT_BG, tag='bp', steps=36)
    for x in range(0, width, 12):
        canvas.create_line(x, 0, x, height, fill=PRINT_MAJOR if x % 60 == 0 else PRINT_MINOR, tags='bp')
    for y in range(0, height, 12):
        canvas.create_line(0, y, width, y, fill=PRINT_MAJOR if y % 60 == 0 else PRINT_MINOR, tags='bp')
    m = 18
    canvas.create_rectangle(m, m, width - m, height - m, outline=PRINT_THIN, width=1, tags='bp')
    canvas.create_rectangle(m + 30, m + 6, width - m - 6, height - m - 6, outline=PRINT_LINE, width=2, tags='bp')
    canvas.create_line(64, 146, min(620, width - 160), 146, fill=GOLD, width=2, tags='bp')
    # штамп (основная надпись) в правом нижнем углу — золотая рамка-акцент
    sw, sh = min(370, width // 3), 110
    x0, y0 = width - m - 6 - sw, height - m - 6 - sh
    canvas.create_rectangle(x0, y0, x0 + sw, y0 + sh, outline=GOLD, width=2, tags='bp')
    for k in (22, 44, 66, 88):
        canvas.create_line(x0, y0 + k, x0 + sw * 0.42, y0 + k, fill=PRINT_THIN, tags='bp')
    canvas.create_line(x0 + sw * 0.42, y0, x0 + sw * 0.42, y0 + sh, fill=GOLD, width=1, tags='bp')
    canvas.create_line(x0 + sw * 0.42, y0 + 44, x0 + sw, y0 + 44, fill=PRINT_LINE, width=2, tags='bp')
    canvas.create_text(x0 + sw * 0.71, y0 + 22, text=APP_NAME.upper(), fill=GOLD, font=(UI_FONT, 13, 'bold'), tags='bp')
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
