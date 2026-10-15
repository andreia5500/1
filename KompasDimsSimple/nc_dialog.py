"""Окно «Проверка УП» и общие части: чтение УП, параметры и библиотека подпрограмм автомата, редактор с номерами строк."""
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk
import nc_engine as E
import transfer as X
import ui as U

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
    """Окно «Проверка УП»: вкладки «Автомат · Diamond», «HAAS VF-2/3», «IMV 10.55».

    Во всех вкладках одинаково: файлы перетаскиваются в окно (или «Добавить
    файлы…»), сверху общее время, ниже карточки, двойной щелчок — подробности.
    """

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        U.window(self, 'Проверка УП', 1360, 880, 1100, 680)
        self.transient(app)
        U.header(self, 'Проверка УП', 'Время цикла и проверка кода · токарный автомат Diamond, фрезерные HAAS VF-2/3 и IMV 10.55',
                 icon='nc')
        self.status = tk.StringVar(value='Перетащите файлы программ в окно: автомат — две программы (S1 и S2), '
                                         'HAAS / IMV — любое количество.')
        bottom = ttk.Frame(self)
        bottom.pack(side='bottom', fill='x', padx=16, pady=(4, 12))
        U.journal_button(bottom, self).pack(side='left')
        ttk.Button(bottom, text='Закрыть', command=self.destroy).pack(side='right')
        ttk.Label(bottom, textvariable=self.status, style='Muted.TLabel').pack(side='left', fill='x', padx=12)
        self.machines = ttk.Notebook(self)
        self.machines.pack(fill='both', expand=True, padx=16, pady=(10, 0))
        import auto_dialog
        import mill_dialog
        self.auto_tab = auto_dialog.build_tab(self, self.machines)
        self.mill_tabs = mill_dialog.build_tabs(self, self.machines)
