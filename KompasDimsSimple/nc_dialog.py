"""Окно «Проверка УП»: время цикла и полная проверка кода (имитация Diamond CSB)."""
import copy
import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
import debug_log as J
import nc_engine as E
import transfer as X
import ui as U

SYSTEMS = (('S1 · Главный', '1'), ('S2 · Контршпиндель', '2'))
SPINDLES = ('1', '2', '3')
NC_TYPES = [('Все файлы', '*.*'), ('Программы ЧПУ', '*.nc *.txt *.tap *.mpf *.cnc *.prg')]


def read_nc(path):
    raw = Path(path).read_bytes()
    for enc in ('utf-8', 'cp1251'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode('latin-1')


def params_path():
    return X.backup_folder() / 'nc_params.json'


def load_params():
    params = E.default_params()
    try:
        saved = json.loads(params_path().read_text(encoding='utf-8'))
        merge(params, saved)
    except (OSError, ValueError):
        pass
    return params


def merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        else:
            base[key] = value


def library_path():
    return X.backup_folder() / 'nc_subprograms.json'


def load_library():
    """Постоянная библиотека подпрограмм: встроенные O5000-O5002 + добавленные пользователем."""
    try:
        data = json.loads(library_path().read_text(encoding='utf-8'))
        return {no: dict(text=v['text'], file=v.get('file') or '', source=v.get('source') or 'библиотека') for no, v in data.items()}
    except (OSError, ValueError, KeyError, TypeError):
        return builtin_subs()


def builtin_subs():
    return {no: dict(text=t, file='', source='встроенная') for no, t in E.DEFAULT_SUBPROGRAMS.items()}


def save_library(subs):
    library_path().write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding='utf-8')


def save_params(params):
    params_path().write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding='utf-8')


class CodeEditor(ttk.Frame):
    """Текст УП с номерами строк и подсветкой выбранной строки."""

    def __init__(self, parent):
        super().__init__(parent)
        self.gutter = tk.Text(self, width=5, padx=6, takefocus=0, border=0, state='disabled', background='#F1F4F8',
                              foreground='#8A97A8', font=(U.MONO_FONT, 10), highlightthickness=0, wrap='none', cursor='arrow')
        self.text = tk.Text(self, wrap='none', undo=True, font=(U.MONO_FONT, 10), padx=8, pady=0)
        bar = ttk.Scrollbar(self, orient='vertical', command=self.yview)
        hbar = ttk.Scrollbar(self, orient='horizontal', command=self.text.xview)
        self.text.configure(yscrollcommand=lambda a, b: (bar.set(a, b), self.gutter.yview_moveto(a)), xscrollcommand=hbar.set)
        self.gutter.grid(row=0, column=0, sticky='ns')
        self.text.grid(row=0, column=1, sticky='nsew')
        bar.grid(row=0, column=2, sticky='ns')
        hbar.grid(row=1, column=1, sticky='ew')
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.text.tag_configure('hit', background='#FFF1C2')
        self.text.tag_configure('error', background='#FDE3E3')
        self.text.bind('<<Modified>>', self.changed)

    def yview(self, *args):
        self.text.yview(*args)
        self.gutter.yview(*args)

    def changed(self, event=None):
        self.text.edit_modified(False)
        lines = int(self.text.index('end-1c').split('.')[0])
        self.gutter.configure(state='normal')
        self.gutter.delete('1.0', 'end')
        self.gutter.insert('1.0', '\n'.join(str(i) for i in range(1, lines + 1)))
        self.gutter.configure(state='disabled')
        self.gutter.yview_moveto(self.text.yview()[0])

    def get(self):
        return self.text.get('1.0', 'end-1c')

    def set(self, value):
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', value)
        self.text.edit_reset()
        self.changed()

    def mark(self, lines, tag='error'):
        self.text.tag_remove(tag, '1.0', 'end')
        for line in lines:
            self.text.tag_add(tag, '%d.0' % line, '%d.0+1l' % line)

    def goto(self, line):
        self.text.tag_remove('hit', '1.0', 'end')
        self.text.tag_add('hit', '%d.0' % line, '%d.0+1l' % line)
        self.text.see('%d.0' % line)
        self.text.mark_set('insert', '%d.0' % line)
        self.text.focus_set()


class NcWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.params = load_params()
        self.subs = load_library()   # номер -> dict(text, file, source)
        self.last_dir = None
        self.sims = []
        U.window(self, 'Проверка УП', 1360, 880, 1100, 680)
        self.transient(app)
        right = U.header(self, 'Проверка УП', 'Время цикла и полная проверка кода · имитация Diamond CSB II/III (Mitsubishi)', icon='nc')
        ttk.Button(right, text='Параметры станка…', style='Banner.TButton', command=self.edit_params).pack(side='right')
        bar = ttk.Frame(self)
        bar.pack(side='bottom', fill='x', padx=16, pady=(8, 12))
        ttk.Button(bar, text='Рассчитать время цикла', style='Accent.TButton', command=self.calculate).pack(side='right')
        ttk.Button(bar, text='Полная проверка кода', command=self.check).pack(side='right', padx=8)
        ttk.Button(bar, text='Закрыть', command=self.destroy).pack(side='right', padx=(0, 8))
        U.journal_button(bar, self).pack(side='left')
        self.status = tk.StringVar(value='Шаг 1: откройте программы систем S1 и S2 (подпрограммы O5000–O5002 встроены, остальные M98 подгружаются из папки УП). '
                                         'Шаг 2: «Рассчитать время цикла» или «Полная проверка кода».')
        ttk.Label(self, textvariable=self.status, style='Muted.TLabel').pack(side='bottom', fill='x', padx=16)
        panes = ttk.Panedwindow(self, orient='horizontal')
        panes.pack(fill='both', expand=True, padx=16, pady=(12, 0))
        left = ttk.Frame(panes)
        panes.add(left, weight=5)
        rightp = ttk.Frame(panes)
        panes.add(rightp, weight=4)
        ttk.Label(left, text='1. Программы', style='Heading.TLabel').pack(anchor='w', pady=(0, 6))
        self.book = ttk.Notebook(left)
        self.book.pack(fill='both', expand=True)
        self.systems = [self.system_tab(name, spindle) for name, spindle in SYSTEMS]
        self.sub_tab()
        ttk.Label(rightp, text='2. Результат', style='Heading.TLabel').pack(anchor='w', padx=(12, 0), pady=(0, 6))
        self.results = ttk.Notebook(rightp)
        self.results.pack(fill='both', expand=True, padx=(12, 0))
        self.time_tab()
        self.check_tab()
        self.block_tab()

    # ------------------------------------------------------------ программы
    def system_tab(self, name, spindle):
        page = ttk.Frame(self.book, padding=(0, 8, 0, 0))
        self.book.add(page, text=name)
        tools = ttk.Frame(page)
        tools.pack(fill='x', pady=(0, 6))
        sys = dict(name=name.split(' · ')[0], page=page, file=None)
        ttk.Button(tools, text='Открыть УП…', style='Accent.TButton', command=lambda: self.open_program(sys)).pack(side='left')
        ttk.Button(tools, text='Очистить', command=lambda: (sys['editor'].set(''), sys['label'].configure(text='Программа не открыта'))).pack(side='left', padx=8)
        sys['spindle'] = tk.StringVar(value=spindle)
        ttk.Combobox(tools, textvariable=sys['spindle'], values=SPINDLES, width=3, state='readonly').pack(side='right')
        ttk.Label(tools, text='Шпиндель системы:').pack(side='right', padx=6)
        sys['label'] = ttk.Label(page, text='Программа не открыта', style='Muted.TLabel')
        sys['label'].pack(anchor='w', pady=(0, 6))
        sys['editor'] = CodeEditor(page)
        sys['editor'].pack(fill='both', expand=True)
        return sys

    def sub_tab(self):
        page = ttk.Frame(self.book, padding=(0, 8, 0, 0))
        self.book.add(page, text='Подпрограммы')
        tools = ttk.Frame(page)
        tools.pack(fill='x', pady=(0, 6))
        ttk.Button(tools, text='Добавить файлы…', style='Accent.TButton', command=self.add_subs).pack(side='left')
        ttk.Button(tools, text='Удалить', command=self.remove_sub).pack(side='left', padx=8)
        ttk.Button(tools, text='Вернуть встроенные', command=self.restore_builtin).pack(side='left')
        ttk.Label(page, text='Библиотека постоянная: подпрограммы сохраняются и доступны при каждом запуске. '
                  'O5000–O5002 встроены. Номер — из строки «O5000» или имени файла.', style='Muted.TLabel',
                  wraplength=560).pack(anchor='w', pady=(0, 6))
        body = ttk.Panedwindow(page, orient='vertical')
        body.pack(fill='both', expand=True)
        frame = ttk.Frame(body)
        body.add(frame, weight=1)
        self.sub_table = ttk.Treeview(frame, columns=('num', 'file', 'lines'), show='headings', height=5)
        for c, t, w in (('num', 'Номер', 90), ('file', 'Источник', 300), ('lines', 'Строк', 70)):
            self.sub_table.heading(c, text=t)
            self.sub_table.column(c, width=w, stretch=c == 'file', anchor='w' if c == 'file' else 'center')
        U.table_scroll(self.sub_table)
        self.sub_table.bind('<<TreeviewSelect>>', lambda e: self.show_sub())
        self.sub_view = CodeEditor(body)
        body.add(self.sub_view, weight=2)
        self.refresh_subs()

    def open_program(self, sys):
        path = filedialog.askopenfilename(parent=self, title='Программа %s' % sys['name'], filetypes=NC_TYPES,
                                          initialdir=self.last_dir)
        if not path:
            return
        self.last_dir = str(Path(path).parent)
        text = read_nc(path)
        sys['editor'].set(text)
        sys['file'] = path
        sys['label'].configure(text=path)
        found, missing = self.autoload_subs(path, text)
        note = ''
        if found:
            note += ' Подпрограммы из папки: %s.' % ', '.join('O' + n for n in found)
        if missing:
            note += ' Не найдены: %s — добавьте на вкладке «Подпрограммы».' % ', '.join('O' + n for n in missing)
        self.status.set('Открыта %s.%s' % (Path(path).name, note))
        J.event('Открыта УП', system=sys['name'], path=path, subs_found=found, subs_missing=missing)

    def called_subs(self, text, seen=None):
        out = []
        for stmt in E.parse_program(text):
            words = [t for t in stmt['tokens'] if t['type'] == 'word']
            if any(w['letter'] == 'M' and E.js_round(E._safe(w['valueExpr'])) == 98 for w in words):
                p = next((w for w in words if w['letter'] == 'P'), None)
                if p:
                    raw = E.js_num(E.js_round(E._safe(p['valueExpr'])))
                    out.append(E.js_key(raw[-4:] if len(raw) > 4 else raw))
        return out

    def autoload_subs(self, path, text):
        folder = Path(path).parent
        found, missing, queue = [], [], self.called_subs(text)
        while queue:
            no = queue.pop(0)
            if no in self.subs or no in found or no in missing:  # уже в библиотеке
                continue
            match = None
            for f in sorted(folder.iterdir()):
                if f.is_file() and re.fullmatch(r'O0*%s(\..*)?' % re.escape(no), f.name, re.I):
                    match = f
                    break
            if match:
                sub_text = read_nc(match)
                self.subs[no] = dict(text=sub_text, file=str(match), source='из папки УП')
                found.append(no)
                queue.extend(self.called_subs(sub_text))
            else:
                missing.append(no)
        if found:
            save_library(self.subs)
        self.refresh_subs()
        return found, missing

    def add_subs(self):
        paths = filedialog.askopenfilenames(parent=self, title='Подпрограммы', filetypes=NC_TYPES, initialdir=self.last_dir)
        bad = []
        for path in paths:
            text = read_nc(path)
            no = E.detect_sub_number(text, Path(path).name)
            if no is None:
                bad.append(Path(path).name)
                continue
            self.subs[no] = dict(text=text, file=path, source='добавлена')
        save_library(self.subs)
        self.refresh_subs()
        if bad:
            messagebox.showwarning('Подпрограммы', 'Не удалось определить номер (нужна строка «O5000»):\n' + '\n'.join(bad), parent=self)

    def remove_sub(self):
        sel = self.sub_table.selection()
        if not sel or not messagebox.askyesno('Подпрограммы', 'Удалить из библиотеки: %s?' % ', '.join('O' + n for n in sel), parent=self):
            return
        for item in sel:
            self.subs.pop(item, None)
        save_library(self.subs)
        self.refresh_subs()

    def restore_builtin(self):
        self.subs.update(builtin_subs())
        save_library(self.subs)
        self.refresh_subs()
        self.status.set('Встроенные подпрограммы O5000–O5002 восстановлены.')

    def refresh_subs(self):
        self.sub_table.delete(*self.sub_table.get_children())
        for i, no in enumerate(sorted(self.subs, key=lambda n: int(n) if n.isdigit() else 0)):
            s = self.subs[no]
            self.sub_table.insert('', 'end', iid=no, tags=('stripe',) if i % 2 else (),
                                  values=('O' + no, s['source'] + (' · ' + Path(s['file']).name if s['file'] else ''), s['text'].count('\n') + 1))
        self.book.tab(2, text='Подпрограммы · %d' % len(self.subs))

    def show_sub(self):
        sel = self.sub_table.selection()
        self.sub_view.set(self.subs[sel[0]]['text'] if sel else '')

    def inputs(self):
        systems = [dict(name=s['name'], spindle=s['spindle'].get(), text=s['editor'].get()) for s in self.systems]
        systems = [s for s in systems if s['text'].strip()]
        if not systems:
            messagebox.showinfo('Проверка УП', 'Откройте или вставьте хотя бы одну программу.', parent=self)
            return None
        return systems, {no: s['text'] for no, s in self.subs.items()}

    # ------------------------------------------------------------ время
    def time_tab(self):
        page = ttk.Frame(self.results, padding=14)
        self.results.add(page, text='Время цикла')
        ttk.Label(page, text='ОБЩЕЕ ВРЕМЯ ЦИКЛА', style='Muted.TLabel').pack(anchor='w')
        self.total = ttk.Label(page, text='—', style='Big.TLabel')
        self.total.pack(anchor='w')
        self.total_sub = ttk.Label(page, text='Нажмите «Рассчитать время цикла».', style='Muted.TLabel')
        self.total_sub.pack(anchor='w', pady=(0, 10))
        frame = ttk.Frame(page)
        frame.pack(fill='x')
        self.sys_table = ttk.Treeview(frame, columns=('sys', 'finish', 'own', 'cut', 'wait'), show='headings', height=3)
        for c, t, w in (('sys', 'Система', 90), ('finish', 'Конец, мин:с', 110), ('own', 'Своя работа', 110),
                        ('cut', 'Резание', 100), ('wait', 'Ожидание !L', 110)):
            self.sys_table.heading(c, text=t)
            self.sys_table.column(c, width=w, anchor='center')
        U.table_scroll(self.sys_table)
        ttk.Label(page, text='Синхронизация систем (барьеры !L)', style='Heading.TLabel').pack(anchor='w', pady=(14, 4))
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        self.barrier_table = ttk.Treeview(frame, columns=('label', 'time', 'who'), show='headings', height=6)
        for c, t, w in (('label', 'Метка', 80), ('time', 'Момент, с', 120), ('who', 'Кто ждёт и сколько', 300)):
            self.barrier_table.heading(c, text=t)
            self.barrier_table.column(c, width=w, anchor='w' if c == 'who' else 'center', stretch=c == 'who')
        U.table_scroll(self.barrier_table)
        ttk.Label(page, text='Замечания расчёта', style='Heading.TLabel').pack(anchor='w', pady=(14, 4))
        self.time_notes = tk.Text(page, height=6, wrap='word', font=(U.UI_FONT, 9), padx=8, pady=6, state='disabled')
        self.time_notes.pack(fill='both', expand=True)

    def calculate(self):
        data = self.inputs()
        if not data:
            return
        systems, subs = data
        try:
            sims, rep = E.calculate(systems, subs, self.params)
        except Exception as exc:
            J.failure('Расчёт времени УП', exc)
            messagebox.showerror('Проверка УП', 'Расчёт не выполнен: %s' % exc, parent=self)
            return
        self.sims = sims
        self.total.configure(text=U.fmt_time(rep['totalMs']),
                             style='Error.TLabel' if any(s.incomplete for s in sims) else 'Big.TLabel')
        self.total_sub.configure(text='%.2f с · ускоренный ход %s%% · %s' % (
            rep['totalMs'] / 1000, self.params.get('rapid_override_pct'),
            'время НЕ достоверно (см. замечания)' if any(s.incomplete for s in sims) else 'мин:сек'))
        self.sys_table.delete(*self.sys_table.get_children())
        waits = {}
        for b in rep['barriers']:
            for name, w in b['waits'].items():
                waits[name] = waits.get(name, 0) + w
        for sim, finish in zip(sims, rep['finishMs']):
            own = sum(e['segMs'] for e in sim.events) + sim.tail_ms
            self.sys_table.insert('', 'end', values=(sim.name, U.fmt_time(finish), '%.1f с' % (own / 1000),
                                                     '%.1f с' % (sim.cutting_ms / 1000), '%.1f с' % (waits.get(sim.name, 0) / 1000)))
        self.barrier_table.delete(*self.barrier_table.get_children())
        for i, b in enumerate(rep['barriers']):
            who = ', '.join('%s ждёт %.2f с' % (n, w / 1000) for n, w in b['waits'].items() if w > 1)
            self.barrier_table.insert('', 'end', tags=('stripe',) if i % 2 else (),
                                      values=('!' + b['label'], '%.2f' % (b['barrierTime'] / 1000), who or 'одновременно'))
        notes = ['%s: %s' % (s.name, w) for s in sims for w in s.warnings] + rep['warnings']
        self.set_text(self.time_notes, '\n'.join('• ' + n for n in notes) or 'Замечаний нет.')
        self.block_sys.configure(values=[s.name for s in sims])
        self.block_sys.set(sims[0].name)
        self.show_blocks()
        self.results.select(0)
        self.status.set('Время цикла %s (%.2f с). По кадрам — на вкладке «По кадрам».' % (U.fmt_time(rep['totalMs']), rep['totalMs'] / 1000))
        J.event('Расчёт времени УП', total_ms=rep['totalMs'], systems=[s.name for s in sims], warnings=notes)

    @staticmethod
    def set_text(widget, value):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', value)
        widget.configure(state='disabled')

    # ------------------------------------------------------------ проверка
    def check_tab(self):
        page = ttk.Frame(self.results, padding=14)
        self.results.add(page, text='Проверка кода')
        self.check_summary = ttk.Label(page, text='Нажмите «Полная проверка кода».', style='Heading.TLabel')
        self.check_summary.pack(anchor='w')
        ttk.Label(page, text='Двойной щелчок — перейти к кадру. Серым — эвристика, проверьте вручную.', style='Muted.TLabel').pack(anchor='w', pady=(2, 8))
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        self.check_table = ttk.Treeview(frame, columns=('sev', 'file', 'line', 'code', 'msg'), show='headings')
        for c, t, w in (('sev', '', 34), ('file', 'Программа', 110), ('line', 'Стр.', 60), ('code', 'Код', 120), ('msg', 'Описание', 520)):
            self.check_table.heading(c, text=t)
            self.check_table.column(c, width=w, anchor='w' if c == 'msg' else 'center', stretch=c == 'msg')
        U.table_scroll(self.check_table)
        self.check_table.tag_configure('error', foreground=U.ERROR)
        self.check_table.tag_configure('warning', foreground=U.WARN)
        self.check_table.tag_configure('uncertain', foreground=U.MUTED)
        self.check_table.bind('<Double-1>', self.jump)
        self.check_table.bind('<<TreeviewSelect>>', self.show_detail)
        self.check_detail = ttk.Label(page, text='', wraplength=620, justify='left')
        self.check_detail.pack(fill='x', pady=(8, 0))
        page.bind('<Configure>', lambda e: self.check_detail.configure(wraplength=max(300, e.width - 30)))
        self.check_rows = {}

    def check(self):
        data = self.inputs()
        if not data:
            return
        systems, subs = data
        files = [dict(name=s['name'], text=s['text'], kind='system', spindle=s['spindle']) for s in systems]
        files += [dict(name='O' + no, text=t, kind='subprogram') for no, t in subs.items()]
        max_rpm = max([sp.get('max_rpm', 0) for sp in self.params['spindles'].values()] + [0])
        try:
            rep = E.full_program_check(files, subs, max_rpm)
        except Exception as exc:
            J.failure('Проверка кода УП', exc)
            messagebox.showerror('Проверка УП', 'Проверка не выполнена: %s' % exc, parent=self)
            return
        self.check_table.delete(*self.check_table.get_children())
        self.check_rows = {}
        rows = [(f, p['file']['name']) for p in rep['perFile'] for f in p['findings']] + [(f, '—') for f in rep['crossFindings']]
        rows.sort(key=lambda r: (r[0]['severity'] != 'error', not r[0]['certain']))
        self.check_detail.configure(text='Выберите строку — здесь будет полное описание.' if rows else 'Замечаний нет.')
        for i, (f, name) in enumerate(rows):
            tag = 'error' if f['severity'] == 'error' else ('warning' if f['certain'] else 'uncertain')
            iid = self.check_table.insert('', 'end', tags=(tag,), values=('✖' if f['severity'] == 'error' else '▲', name,
                                                                         f.get('line') or '', f['code'], f['message']))
            self.check_rows[iid] = (name, f.get('line'))
        for sys in self.systems:
            lines = [f['line'] for p in rep['perFile'] if p['file']['name'] == sys['name'] for f in p['findings']
                     if f['severity'] == 'error' and f['certain'] and f.get('line')]
            sys['editor'].mark(lines)
        ok = not rep['totalErrors']
        self.check_summary.configure(text='%s Ошибок: %d · предупреждений: %d' % ('✔' if ok else '✖', rep['totalErrors'], rep['totalWarnings']),
                                     style='Ok.TLabel' if ok else 'Error.TLabel')
        self.results.select(1)
        self.status.set('Проверка кода: ошибок %d, предупреждений %d.' % (rep['totalErrors'], rep['totalWarnings']))
        J.event('Проверка кода УП', errors=rep['totalErrors'], warnings=rep['totalWarnings'])

    def show_detail(self, event=None):
        sel = self.check_table.selection()
        self.check_detail.configure(text=self.check_table.item(sel[0], 'values')[4] if sel else '')

    def jump(self, event):
        row = self.check_table.identify_row(event.y)
        if not row or row not in self.check_rows:
            return
        name, line = self.check_rows[row]
        if not line:
            return
        for i, sys in enumerate(self.systems):
            if sys['name'] == name:
                self.book.select(i)
                sys['editor'].goto(line)
                return
        no = name[1:]
        if no in self.subs:
            self.book.select(2)
            self.sub_table.selection_set(no)
            self.show_sub()
            self.sub_view.goto(line)

    # ------------------------------------------------------------ по кадрам
    def block_tab(self):
        page = ttk.Frame(self.results, padding=14)
        self.results.add(page, text='По кадрам')
        top = ttk.Frame(page)
        top.pack(fill='x', pady=(0, 8))
        ttk.Label(top, text='Система:').pack(side='left')
        self.block_sys = ttk.Combobox(top, values=[], width=10, state='readonly')
        self.block_sys.pack(side='left', padx=6)
        self.block_sys.bind('<<ComboboxSelected>>', lambda e: self.show_blocks())
        ttk.Label(top, text='Кадры подпрограмм входят в общий ход программы.', style='Muted.TLabel').pack(side='left', padx=10)
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        self.block_table = ttk.Treeview(frame, columns=('line', 'raw', 'ms', 'sum', 'note'), show='headings')
        for c, t, w in (('line', 'Стр.', 55), ('raw', 'Кадр', 220), ('ms', 'Время, с', 80), ('sum', 'Нарастающее, с', 110), ('note', 'Расчёт', 420)):
            self.block_table.heading(c, text=t)
            self.block_table.column(c, width=w, anchor='w' if c in ('raw', 'note') else 'center', stretch=c == 'note')
        U.table_scroll(self.block_table)

    def show_blocks(self):
        self.block_table.delete(*self.block_table.get_children())
        sim = next((s for s in self.sims if s.name == self.block_sys.get()), None)
        if not sim:
            return
        total = 0
        for i, b in enumerate(sim.block_log):
            total += b['ms']
            self.block_table.insert('', 'end', tags=('stripe',) if i % 2 else (),
                                    values=(b['lineNo'], b['raw'].strip()[:60], '%.3f' % (b['ms'] / 1000), '%.2f' % (total / 1000), b['note']))

    # ------------------------------------------------------------ параметры
    def edit_params(self):
        p = copy.deepcopy(self.params)
        w = U.dialog(self, 'Параметры станка', 640, 560)
        body = ttk.Frame(w, padding=16)
        body.pack(fill='both', expand=True)
        rows = []

        def field(label, getter, setter, kind='entry', values=None):
            r = len(rows)
            ttk.Label(body, text=label).grid(row=r, column=0, sticky='w', pady=4)
            var = tk.StringVar(value=str(getter()))
            if kind == 'combo':
                ttk.Combobox(body, textvariable=var, values=values, state='readonly', width=22).grid(row=r, column=1, sticky='w', pady=4)
            else:
                ttk.Entry(body, textvariable=var, width=24).grid(row=r, column=1, sticky='w', pady=4)
            rows.append((var, setter))
        field('Коррекция ускоренного хода, %', lambda: p['rapid_override_pct'], lambda v: p.update(rapid_override_pct=float(v)), 'combo', ['0', '25', '50', '100'])
        field('M-код по умолчанию, мс', lambda: p['m_codes']['default_exec_time_ms'], lambda v: p['m_codes'].update(default_exec_time_ms=float(v)))
        field('Смена инструмента (T-код), мс', lambda: p['t_code_exec_time_ms'], lambda v: p.update(t_code_exec_time_ms=float(v)))
        field('Разгон/торможение шпинделя', lambda: 'учитывать' if p['model_spindle_ramp'] else 'не учитывать',
              lambda v: p.update(model_spindle_ramp=v == 'учитывать'), 'combo', ['учитывать', 'не учитывать'])
        field('Индексация гребёнки T01–T19', lambda: 'учитывать' if p['tool_travel_model']['enabled'] else 'не учитывать',
              lambda v: p['tool_travel_model'].update(enabled=v == 'учитывать'), 'combo', ['учитывать', 'не учитывать'])
        modes = {'by_d': 'отвод на d (быстрый)', 'to_r': 'возврат в R (медленный)'}
        field('Отвод в G83/G87', lambda: modes[p['canned_cycle']['g83_retract_mode']],
              lambda v: p['canned_cycle'].update(g83_retract_mode=next(k for k, t in modes.items() if t == v)), 'combo', list(modes.values()))
        aux = {'overlap': 'одновременно с движением', 'sequential': 'после движения'}
        field('M/T-коды и движение', lambda: aux[p['aux_code_timing_model']],
              lambda v: p.update(aux_code_timing_model=next(k for k, t in aux.items() if t == v)), 'combo', list(aux.values()))
        for sp in sorted(p['spindles']):
            field('Шпиндель %s: макс. обороты' % sp, lambda sp=sp: p['spindles'][sp]['max_rpm'],
                  lambda v, sp=sp: p['spindles'][sp].update(max_rpm=float(v)))
        ttk.Label(body, text='Оси, M-коды по отдельности и особые G-коды — в файле параметров:\n%s' % params_path(),
                  style='Muted.TLabel', wraplength=580).grid(row=len(rows), column=0, columnspan=2, sticky='w', pady=(12, 0))
        bar = ttk.Frame(w, padding=(16, 0, 16, 16))
        bar.pack(fill='x')

        def apply():
            try:
                for var, setter in rows:
                    setter(var.get().replace(',', '.'))
            except (ValueError, StopIteration):
                messagebox.showerror('Параметры станка', 'Проверьте числовые значения.', parent=w)
                return
            self.params = p
            save_params(p)
            J.event('Параметры станка сохранены', path=str(params_path()))
            w._close()
            self.status.set('Параметры станка сохранены. Пересчитайте время цикла.')

        def reset():
            if messagebox.askyesno('Параметры станка', 'Вернуть параметры по умолчанию?', parent=w):
                self.params = E.default_params()
                save_params(self.params)
                w._close()
        ttk.Button(bar, text='Сохранить', style='Accent.TButton', command=apply).pack(side='right')
        ttk.Button(bar, text='Отмена', command=w._close).pack(side='right', padx=8)
        ttk.Button(bar, text='По умолчанию', command=reset).pack(side='left')
