"""Вкладка «Автомат · Diamond» окна «Проверка УП» — как у фрезерных станков.

Перетащите в окно программы автомата (или «Добавить файлы…»). Систем у
автомата ровно две — главный шпиндель (S1) и контршпиндель (S2), поэтому
программ можно загрузить не больше двух; какая из них главная, определяется
само (по названию в строке O…, S1=/S2=, G43.1/G44.1, а при равенстве — по
номеру O). Подпрограммы (M98 P…) из перетащенных файлов и из папки УП
попадают в постоянную библиотеку (O5000–O5002 встроены).
Расчёт сразу: общее время цикла сверху, карточки S1/S2, двойной щелчок —
подробности (текст, сводка и барьеры !L, инструменты, проверка кода, по кадрам).
"""
import copy
import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import debug_log as J
import nc_engine as E
import nc_dialog as D
import mill_dialog as MD
import ui as U

SIDES = (('S1', '1', 'Главный шпиндель'), ('S2', '2', 'Контршпиндель'))
AUTO_CATS = (('cut', 'резание', U.BLUE), ('move', 'перемещения и M/T', U.GOLD), ('wait', 'ожидание !L', '#B9B2A3'))
MAIN_WORDS = ('GLAV', 'ГЛАВ', 'MAIN', 'OSN', 'ОСНОВ')
COUNTER_WORDS = ('KONTR', 'КОНТР', 'SUB SP', 'SUB-SP', 'SUBSP', 'PROTIV', 'ПРОТИВ', 'COUNTER', 'ВСТРЕЧ', 'VSTRE')


def program_number(name, text):
    m = re.search(r'^\s*O\s*(\d+)', text or '', re.I | re.M)
    if m:
        return E.js_key(m.group(1))
    f = re.search(r'(\d+)', name or '')
    return E.js_key(f.group(1)) if f else None


def header_comment(text):
    m = re.search(r'^\s*O\s*\d+\s*\(([^)]*)\)', text or '', re.I | re.M)
    return m.group(1).strip() if m else ''


def called_subs(text):
    out = []
    for stmt in E.parse_program(text):
        words = [t for t in stmt['tokens'] if t['type'] == 'word']
        if any(w['letter'] == 'M' and E.js_round(E._safe(w['valueExpr'])) == 98 for w in words):
            p = next((w for w in words if w['letter'] == 'P'), None)
            if p:
                raw = E.js_num(E.js_round(E._safe(p['valueExpr'])))
                out.append(E.js_key(raw[-4:] if len(raw) > 4 else raw))
    return out


def is_system(text):
    """Программа системы, а не подпрограмма: есть барьеры !L, или M30/M02, или вызывает 3+ разных
    инструмента. Подпрограммы автомата (O5000…) — короткие, с M99, без !L."""
    code = '\n'.join(E.strip_comment(l) for l in (text or '').splitlines())
    if re.search(r'!L\w*', code, re.I) or re.search(r'M\s*0*(30|2)\b', code, re.I):
        return True
    if not re.search(r'M\s*99\b', code, re.I):
        return True
    tools = {t for t in re.findall(r'T(\d{3,4})', code) if int(t)}
    return len(tools) >= 3


def side_score(text):
    """>0 — главный шпиндель (S1), <0 — контршпиндель (S2), 0 — не понятно. Плюс пояснение."""
    head = header_comment(text).upper()
    code = '\n'.join(E.strip_comment(l) for l in (text or '').splitlines()).upper()
    score, why = 0, []
    if any(w in head for w in COUNTER_WORDS):
        score -= 4
        why.append('название «%s»' % header_comment(text))
    elif any(w in head for w in MAIN_WORDS):
        score += 4
        why.append('название «%s»' % header_comment(text))
    s1, s2 = len(re.findall(r'S1\s*=', code)), len(re.findall(r'S2\s*=', code))
    if s1 != s2:
        score += 2 if s1 > s2 else -2
        why.append('S1= ×%d, S2= ×%d' % (s1, s2))
    if 'G43.1' in code and 'G44.1' not in code:
        score += 1
        why.append('G43.1')
    elif 'G44.1' in code and 'G43.1' not in code:
        score -= 1
        why.append('G44.1')
    return score, why


def assign(programs, current=None):
    """programs: [dict(name, text, …)] (1–2 шт.) -> ({'S1': prog, 'S2': prog}, пояснение)."""
    current = dict(current or {})
    scored = [(p, *side_score(p['text'])) for p in programs]
    if len(scored) == 2:
        (a, sa, wa), (b, sb, wb) = scored
        if sa != sb:
            main, other = (a, b) if sa > sb else (b, a)
            note = 'главный — %s (%s)' % (main['name'], ', '.join((wa if main is a else wb)) or 'остальные признаки')
        else:
            na, nb = int(a['no'] or 0), int(b['no'] or 0)
            main, other = (a, b) if na <= nb else (b, a)
            note = 'признаки одинаковые — главный по меньшему номеру O%s; проверьте, при ошибке нажмите «⇄ Поменять»' % main['no']
        return {'S1': main, 'S2': other}, note
    p, score, why = scored[0]
    if score > 0:
        side = 'S1'
    elif score < 0:
        side = 'S2'
    else:
        side = 'S1' if 'S1' not in current else 'S2'
    current[side] = p
    return current, '%s → %s (%s)' % (p['name'], side, ', '.join(why) or 'свободная система')


class AutoTab(ttk.Frame):
    machine = 'auto'
    machine_title = 'Автомат Diamond CSB (Mitsubishi)'

    def __init__(self, parent, owner):
        super().__init__(parent)
        self.owner = owner
        self.params = D.load_params()
        self.subs = D.load_library()        # номер -> dict(text, file, source)
        self.slots = {}                     # 'S1'/'S2' -> dict(name, path, text, no, title)
        self.result = None
        self.last_dir = None
        self.files, self.paths = {}, {}     # для окна подробностей: путь -> текст, имя -> путь
        bar = ttk.Frame(self)
        bar.pack(side='top', fill='x', pady=(10, 8))
        ttk.Button(bar, text='Добавить файлы…', style='Accent.TButton', command=self.add_files).pack(side='left')
        ttk.Button(bar, text='⇄ Поменять S1/S2', command=self.swap).pack(side='left', padx=(8, 0))
        ttk.Button(bar, text='Очистить', command=self.clear).pack(side='left', padx=8)
        ttk.Button(bar, text='Параметры станка…', command=self.edit_params).pack(side='right')
        ttk.Button(bar, text='Подпрограммы…', command=self.library).pack(side='right', padx=8)
        self.passport = ttk.Label(bar, style='Muted.TLabel')
        self.passport.pack(side='right', padx=12)
        self.update_passport()
        self.body = ttk.Frame(self)
        self.body.pack(fill='both', expand=True)
        self.show()

    def update_passport(self):
        self.passport.configure(text='ускоренный %g%% · подпрограмм в библиотеке: %d' % (
            self.params.get('rapid_override_pct', 50), len(self.subs)))

    # ------------------------------------------------------------ файлы
    def add_files(self):
        paths = filedialog.askopenfilenames(parent=self.owner, title='Программы автомата (S1 и S2)', filetypes=MD.FILE_TYPES,
                                            initialdir=self.last_dir)
        if paths:
            self.load(paths)

    def clear(self):
        self.slots = {}
        self.result = None
        self.show()
        self.owner.status.set('Автомат: программы убраны.')

    def swap(self):
        if not self.slots:
            return
        self.slots = {'S1': self.slots.get('S2'), 'S2': self.slots.get('S1')}
        self.slots = {k: v for k, v in self.slots.items() if v}
        J.event('Автомат: системы поменяны местами', S1=self.slot_name('S1'), S2=self.slot_name('S2'))
        self.calculate()

    def slot_name(self, side):
        return self.slots[side]['name'] if side in self.slots else None

    def load(self, paths):
        files, skipped = MD.nc_files(paths)
        programs, subs = [], []
        for f in files:
            try:
                text = D.read_nc(f).replace('\r\n', '\n').replace('\r', '\n')
            except OSError as exc:
                J.failure('Чтение УП', exc, path=str(f))
                skipped.append(f)
                continue
            item = dict(name=f.name, path=str(f), text=text, no=program_number(f.name, text), title=header_comment(text))
            (programs if is_system(text) else subs).append(item)
        called = {n for p in programs + subs for n in called_subs(p['text'])}
        for p in [p for p in programs if p['no'] in called and '!L' not in p['text'].upper()]:
            programs.remove(p)
            subs.append(p)
        if not programs and not subs:
            messagebox.showinfo('Проверка УП', 'Среди перетащенного нет программ ЧПУ.', parent=self.owner)
            return
        if len(programs) > 2:
            messagebox.showerror('Проверка УП', 'У автомата две системы — главный шпиндель (S1) и контршпиндель (S2).\n'
                                 'Перетащено программ: %d (%s).\nПеретащите не больше двух; подпрограммы (с M99, без !L) '
                                 'можно добавлять сколько угодно.' % (len(programs), ', '.join(p['name'] for p in programs)),
                                 parent=self.owner)
            J.event('Автомат: больше двух программ', files=[p['name'] for p in programs])
            return
        for s in subs:
            no = s['no']
            if no is None:
                skipped.append(Path(s['path']))
                continue
            self.subs[no] = dict(text=s['text'], file=s['path'], source='перетащена')
        note = ''
        if programs:
            self.slots, note = assign(programs, self.slots)
            self.last_dir = str(Path(programs[0]['path']).parent)
        found, missing = self.autoload()
        D.save_library(self.subs)
        J.event('Автомат: загружены программы', S1=self.slot_name('S1'), S2=self.slot_name('S2'), note=note,
                subs=[s['name'] for s in subs], from_folder=found, missing=missing)
        self.calculate()
        extra = []
        if note:
            extra.append('Определено: ' + note + '.')
        if found:
            extra.append('Подпрограммы из папки: %s.' % ', '.join('O' + n for n in found))
        if missing:
            extra.append('Не найдены: %s — перетащите их файлы.' % ', '.join('O' + n for n in missing))
        if skipped:
            extra.append('Пропущены: %s.' % ', '.join(Path(s).name for s in skipped[:5]))
        if extra:
            self.owner.status.set(' '.join(extra))

    def autoload(self):
        """Подпрограммы M98 из папок загруженных программ (файлы O5000, O5000.nc …)."""
        found, missing = [], []
        queue = [(n, Path(p['path']).parent) for p in self.slots.values() for n in called_subs(p['text'])]
        while queue:
            no, folder = queue.pop(0)
            if no in self.subs or no in found or no in missing:
                continue
            match = None
            try:
                for f in sorted(folder.iterdir()):
                    if f.is_file() and re.fullmatch(r'O0*%s(\..*)?' % re.escape(no), f.name, re.I):
                        match = f
                        break
            except OSError:
                pass
            if match:
                text = D.read_nc(match).replace('\r\n', '\n')
                self.subs[no] = dict(text=text, file=str(match), source='из папки УП')
                found.append(no)
                queue.extend((n, folder) for n in called_subs(text))
            else:
                missing.append(no)
        return found, missing

    # ------------------------------------------------------------ расчёт
    def calculate(self):
        self.update_passport()
        if not self.slots:
            self.result = None
            self.show()
            return
        systems = [dict(name=side, spindle=sp, text=self.slots[side]['text']) for side, sp, _ in SIDES if side in self.slots]
        subs = {no: s['text'] for no, s in self.subs.items()}
        try:
            sims, rep = E.calculate(systems, subs, self.params)
            max_rpm = max([sp.get('max_rpm', 0) for sp in self.params['spindles'].values()] + [0])
            used = self.used_subs()
            files = [dict(name=s['name'], text=s['text'], kind='system', spindle=s['spindle']) for s in systems]
            files += [dict(name='O' + no, text=subs[no], kind='subprogram') for no in used if no in subs]
            check = E.full_program_check(files, {no: subs[no] for no in used if no in subs}, max_rpm)
        except Exception as exc:
            J.failure('Расчёт автомата', exc)
            messagebox.showerror('Проверка УП', 'Расчёт не выполнен: %s' % exc, parent=self.owner)
            return
        self.result = self.build(sims, rep, check, used)
        r = self.result
        J.event('Расчёт автомата', total_ms=rep['totalMs'], errors=r['errors'], S1=self.slot_name('S1'), S2=self.slot_name('S2'))
        self.show()
        self.owner.status.set('Автомат: время цикла %s, ошибок %d, предупреждений %d. Двойной щелчок по карточке — подробности.' % (
            U.fmt_time(rep['totalMs']), r['errors'], r['warnings']))

    def used_subs(self):
        """Подпрограммы, которые реально вызываются (с вложенными)."""
        seen, queue = [], [n for p in self.slots.values() for n in called_subs(p['text'])]
        while queue:
            no = queue.pop(0)
            if no in seen:
                continue
            seen.append(no)
            if no in self.subs:
                queue.extend(called_subs(self.subs[no]['text']))
        return seen

    def build(self, sims, rep, check, used):
        """Результат в виде «установов» — те же карточки и окно подробностей, что у фрезерных."""
        self.files, self.paths = {}, {}
        for side, prog in self.slots.items():
            self.files[prog['path']] = prog['text']
            self.paths[prog['name']] = prog['path']
        for no in used:
            if no in self.subs:
                key = 'lib:O' + no
                self.files[key] = self.subs[no]['text'].replace('\r\n', '\n')
                self.paths['O' + no] = key
        name_of = {side: self.slots[side]['name'] for side in self.slots}
        waits = {}
        for b in rep['barriers']:
            for n, w in b['waits'].items():
                waits[n] = waits.get(n, 0) + w
        cross = []
        for f in check['crossFindings']:
            cross.append(dict(severity=f['severity'], certain=f['certain'], code=f['code'], message=f['message'],
                              file=name_of.get((f.get('file') or {}).get('name'), None) if f.get('file') else None, line=None))
        cards = []
        errors = warnings = 0
        for sim, finish in zip(sims, rep['finishMs']):
            side = sim.name
            prog = self.slots[side]
            issues = []
            for per in check['perFile']:
                fname = per['file']['name']
                if fname != side and not (fname.startswith('O') and fname[1:] in self.subs and fname[1:] in called_subs_deep(prog['text'], self.subs)):
                    continue
                shown = prog['name'] if fname == side else fname
                for f in per['findings']:
                    issues.append(dict(severity=f['severity'], certain=f['certain'], code=f['code'], message=f['message'],
                                       file=shown, line=f.get('line')))
            for w in sim.warnings:
                issues.append(dict(severity='warning', certain=True, code='Расчёт', message=w, file=prog['name'], line=None))
            issues += [dict(c) for c in cross]
            issues.sort(key=lambda i: (i['severity'] != 'error', not i['certain'], i['line'] or 0))
            own = sum(e['segMs'] for e in sim.events) + sim.tail_ms
            wait = waits.get(side, 0)
            blocks = []
            lines = prog['text'].split('\n')
            for b in sim.block_log:
                fname = prog['name']
                ln = b['lineNo']
                if not (0 < ln <= len(lines) and lines[ln - 1].strip() == b['raw'].strip()):
                    for no in used:
                        sub_lines = self.subs.get(no, {}).get('text', '').replace('\r\n', '\n').split('\n')
                        if 0 < ln <= len(sub_lines) and sub_lines[ln - 1].strip() == b['raw'].strip():
                            fname = 'O' + no
                            break
                blocks.append(dict(file=fname, line=ln, raw=b['raw'].strip(), ms=b['ms'], note=b['note']))
            cut = sim.cutting_ms
            cards.append(dict(side=side, role=dict((s, r) for s, _, r in SIDES)[side], no=prog['no'] or '?', title=prog['title'],
                              file=prog['name'], ms=finish, own=own, wait=wait, issues=issues, blocks=blocks,
                              cat=dict(cut=cut, move=max(0.0, own - cut), wait=wait), incomplete=sim.incomplete,
                              tools=tool_list(prog['text']), alt_ms=None, block_skip=True, stops=[], span={}))
            errors += sum(1 for i in issues if i['severity'] == 'error' and i not in cross)
            warnings += sum(1 for i in issues if i['severity'] != 'error' and i not in cross)
        errors += sum(1 for i in cross if i['severity'] == 'error')
        warnings += sum(1 for i in cross if i['severity'] != 'error')
        return dict(rep=rep, cards=cards, errors=errors, warnings=warnings, cross=cross, used=used,
                    missing=[n for n in used if n not in self.subs])

    # ------------------------------------------------------------ вид
    def show(self):
        for w in self.body.winfo_children():
            w.destroy()
        r = self.result
        top = ttk.Frame(self.body, style='Card.TFrame', padding=(18, 12))
        top.pack(fill='x')
        left = ttk.Frame(top, style='Paper.TFrame')
        left.pack(side='left', fill='y')
        ttk.Label(left, text='ОБЩЕЕ ВРЕМЯ ЦИКЛА', style='Muted.TLabel', background=U.PAPER).pack(anchor='w')
        if r:
            bad = any(c['incomplete'] for c in r['cards'])
            ttk.Label(left, text=U.fmt_time(r['rep']['totalMs']), style='Big.TLabel', background=U.PAPER,
                      foreground=U.ERROR if bad else U.NAVY).pack(anchor='w')
            ttk.Label(left, text='%.2f с · ускоренный %g%% · барьеров !L: %d%s' % (
                r['rep']['totalMs'] / 1000, self.params.get('rapid_override_pct', 50), len(r['rep']['barriers']),
                ' · время НЕ достоверно (см. подробности)' if bad else ''), style='Muted.TLabel', background=U.PAPER).pack(anchor='w')
        else:
            ttk.Label(left, text='—', style='Big.TLabel', background=U.PAPER).pack(anchor='w')
            ttk.Label(left, text='Перетащите две программы: главный шпиндель и контршпиндель.', style='Muted.TLabel',
                      background=U.PAPER).pack(anchor='w')
        right = ttk.Frame(top, style='Paper.TFrame')
        right.pack(side='right', fill='both', expand=True, padx=(30, 0))
        if r:
            ok = not r['errors']
            ttk.Label(right, text='%s Ошибок: %d · предупреждений: %d' % ('✔' if ok else '✖', r['errors'], r['warnings']),
                      background=U.PAPER, foreground=U.OK if ok else U.ERROR, font=(U.UI_FONT, 11, 'bold')).pack(anchor='e')
            subs = ', '.join('O%s%s' % (n, '' if n in self.subs else ' (нет!)') for n in r['used'])
            ttk.Label(right, text='Подпрограммы: %s' % (subs or 'не вызываются'), style='Muted.TLabel', background=U.PAPER,
                      wraplength=560, justify='right').pack(anchor='e', pady=(2, 0))
            for i in [c for c in r['cross'] if c['severity'] == 'error'][:3]:
                ttk.Label(right, text='✖ ' + i['message'], background=U.PAPER, foreground=U.ERROR, wraplength=560,
                          justify='right').pack(anchor='e', pady=(2, 0))
        row = ttk.Frame(self.body)
        row.pack(fill='both', expand=True, pady=(10, 0))
        row.columnconfigure(0, weight=1, uniform='side')
        row.columnconfigure(1, weight=1, uniform='side')
        row.rowconfigure(0, weight=1)
        cards = {c['side']: c for c in (r['cards'] if r else [])}
        for k, (side, _, role) in enumerate(SIDES):
            if side in cards:
                w = self.card(row, cards[side])
            else:
                w = self.drop_card(row, side, role)
            w.grid(row=0, column=k, sticky='nsew', padx=(0, 12) if k == 0 else 0)

    def drop_card(self, parent, side, role):
        c = tk.Canvas(parent, background=U.PAPER, highlightthickness=0)

        def draw(event=None):
            c.delete('all')
            w, h = c.winfo_width(), c.winfo_height()
            if w < 50:
                return
            c.create_rectangle(10, 10, w - 10, h - 10, outline='#C9BE9F', dash=(6, 5), width=2)
            cx, cy = w // 2, h // 2
            U.draw_icon(c, 'nc', cx, cy - 60, 52, U.BLUE, U.PAPER)
            c.create_text(cx, cy + 6, text='%s · %s' % (side, role), font=(U.UI_FONT, 14, 'bold'), fill=U.NAVY)
            c.create_text(cx, cy + 32, anchor='n', width=max(200, w - 80), justify='center', fill=U.MUTED, font=(U.UI_FONT, 10),
                          text='Перетащите сюда программы автомата — обе сразу или по одной.\nГлавный и контршпиндель '
                               'определятся сами. Не больше двух программ; подпрограммы (M99) — сколько угодно.')
        c.bind('<Configure>', draw)
        c.bind('<Double-1>', lambda e: self.add_files())
        return c

    def card(self, parent, s):
        card = ttk.Frame(parent, style='Card.TFrame', padding=(16, 12))
        errors = sum(1 for i in s['issues'] if i['severity'] == 'error')
        warns = sum(1 for i in s['issues'] if i['severity'] != 'error' and i['certain'])
        hints = sum(1 for i in s['issues'] if i['severity'] != 'error' and not i['certain'])
        ttk.Label(card, text='%s · %s' % (s['side'], s['role'].upper()), background=U.PAPER, foreground=U.GOLD_PRESS,
                  font=(U.UI_FONT, 9, 'bold')).pack(anchor='w')
        row = ttk.Frame(card, style='Paper.TFrame')
        row.pack(fill='x')
        ttk.Label(row, text='O' + s['no'], font=(U.UI_FONT, 13, 'bold'), background=U.PAPER, foreground=U.NAVY).pack(side='left')
        ttk.Label(row, text=s['file'], style='Muted.TLabel', background=U.PAPER).pack(side='right')
        ttk.Label(card, text=s['title'] or '—', background=U.PAPER, wraplength=520).pack(anchor='w', pady=(2, 6))
        line = ttk.Frame(card, style='Paper.TFrame')
        line.pack(fill='x')
        ttk.Label(line, text=U.fmt_time(s['ms']), font=(U.UI_FONT, 24, 'bold'), background=U.PAPER,
                  foreground=U.ERROR if s['incomplete'] else U.NAVY).pack(side='left')
        ttk.Label(line, text='конец системы, мин:с', style='Muted.TLabel', background=U.PAPER).pack(side='left', padx=10, pady=(10, 0))
        bar = tk.Canvas(card, height=8, background=U.PAPER, highlightthickness=0)
        bar.pack(fill='x', pady=(6, 4))
        bar.bind('<Configure>', lambda e, c=bar: (c.delete('all'), MD.MillTab.draw_bar(c, s['cat'], e.width, AUTO_CATS)))
        ttk.Label(card, text='своя работа %s · резание %s · ожидание !L %s · инструментов %d' % (
            U.fmt_time(s['own']), U.fmt_time(s['cat']['cut']), U.fmt_time(s['wait']), len(s['tools'])),
            style='Muted.TLabel', background=U.PAPER).pack(anchor='w')
        if errors:
            text, color = '✖ Ошибок: %d%s' % (errors, (' · ▲ %d' % warns) if warns else ''), U.ERROR
        elif warns:
            text, color = '▲ Предупреждений: %d' % warns, U.WARN
        else:
            text, color = '✔ Ошибок не найдено', U.OK
        if hints:
            text += ' · ? %d' % hints
        ttk.Label(card, text=text, background=U.PAPER, foreground=color, font=(U.UI_FONT, 10, 'bold')).pack(anchor='w', pady=(8, 0))
        for i in [i for i in s['issues'] if i['severity'] == 'error' or i['certain']][:4]:
            ttk.Label(card, text='%s стр. %s: %s' % ('✖' if i['severity'] == 'error' else '▲', i['line'] or '—', i['message']),
                      background=U.PAPER, foreground=U.MUTED, wraplength=520, justify='left').pack(anchor='w', pady=(2, 0))
        ttk.Label(card, text='Двойной щелчок — подробности', style='Muted.TLabel', background=U.PAPER,
                  font=(U.UI_FONT, 8)).pack(side='bottom', anchor='e', pady=(4, 0))
        card.bind('<Configure>', lambda e: [w.configure(wraplength=max(250, e.width - 40)) for w in card.winfo_children()
                                            if isinstance(w, ttk.Label) and str(w.cget('wraplength')) not in ('0', '')])

        def bind(widget):
            widget.bind('<Double-1>', lambda e: AutoSetupWindow(self, s))
            for ch in widget.winfo_children():
                bind(ch)
        bind(card)
        return card

    # ------------------------------------------------------------ библиотека подпрограмм
    def library(self):
        w = U.dialog(self.owner, 'Подпрограммы автомата', 820, 560)
        body = ttk.Frame(w, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Библиотека постоянная: подпрограммы сохраняются между запусками. O5000–O5002 встроены. '
                  'Новые подпрограммы можно просто перетащить в окно вместе с программами.',
                  style='Muted.TLabel', wraplength=760).pack(anchor='w', pady=(0, 8))
        panes = ttk.Panedwindow(body, orient='horizontal')
        panes.pack(fill='both', expand=True)
        frame = ttk.Frame(panes)
        panes.add(frame, weight=2)
        table = ttk.Treeview(frame, columns=('num', 'src', 'lines'), show='headings')
        for c, t, wd in (('num', 'Номер', 70), ('src', 'Источник', 200), ('lines', 'Строк', 60)):
            table.heading(c, text=t)
            table.column(c, width=wd, anchor='w' if c == 'src' else 'center', stretch=c == 'src')
        U.table_scroll(table)
        view = D.CodeEditor(panes)
        panes.add(view, weight=3)

        def refresh():
            table.delete(*table.get_children())
            for k, no in enumerate(sorted(self.subs, key=lambda n: int(n) if n.isdigit() else 0)):
                s = self.subs[no]
                table.insert('', 'end', iid=no, tags=('stripe',) if k % 2 else (),
                             values=('O' + no, s['source'] + (' · ' + Path(s['file']).name if s['file'] else ''), s['text'].count('\n') + 1))
        table.bind('<<TreeviewSelect>>', lambda e: view.set(self.subs[table.selection()[0]]['text'] if table.selection() else ''))

        def add():
            paths = filedialog.askopenfilenames(parent=w, title='Подпрограммы', filetypes=MD.FILE_TYPES, initialdir=self.last_dir)
            bad = []
            for p in paths:
                text = D.read_nc(p).replace('\r\n', '\n')
                no = E.detect_sub_number(text, Path(p).name)
                if no is None:
                    bad.append(Path(p).name)
                else:
                    self.subs[no] = dict(text=text, file=p, source='добавлена')
            D.save_library(self.subs)
            refresh()
            if bad:
                messagebox.showwarning('Подпрограммы', 'Не удалось определить номер (нужна строка «O5000»):\n' + '\n'.join(bad), parent=w)

        def remove():
            sel = table.selection()
            if sel and messagebox.askyesno('Подпрограммы', 'Удалить из библиотеки: %s?' % ', '.join('O' + n for n in sel), parent=w):
                for n in sel:
                    self.subs.pop(n, None)
                D.save_library(self.subs)
                refresh()

        def builtin():
            self.subs.update(D.builtin_subs())
            D.save_library(self.subs)
            refresh()
        bar = ttk.Frame(w, padding=(16, 0, 16, 16))
        bar.pack(fill='x')
        ttk.Button(bar, text='Добавить файлы…', command=add).pack(side='left')
        ttk.Button(bar, text='Удалить', command=remove).pack(side='left', padx=8)
        ttk.Button(bar, text='Вернуть встроенные', command=builtin).pack(side='left')

        def close():
            w._close()
            self.calculate()
        ttk.Button(bar, text='Готово', style='Accent.TButton', command=close).pack(side='right')
        w.protocol('WM_DELETE_WINDOW', close)
        refresh()

    # ------------------------------------------------------------ параметры
    def edit_params(self):
        p = copy.deepcopy(self.params)
        w = U.dialog(self.owner, 'Параметры станка · автомат', 640, 560)
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
        ttk.Label(body, text='Оси, M-коды по отдельности и особые G-коды — в файле параметров:\n%s' % D.params_path(),
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
            D.save_params(p)
            J.event('Параметры станка сохранены', path=str(D.params_path()))
            w._close()
            self.calculate()

        def reset():
            if messagebox.askyesno('Параметры станка', 'Вернуть параметры по умолчанию?', parent=w):
                self.params = E.default_params()
                D.save_params(self.params)
                w._close()
                self.calculate()
        ttk.Button(bar, text='Сохранить', style='Accent.TButton', command=apply).pack(side='right')
        ttk.Button(bar, text='Отмена', command=w._close).pack(side='right', padx=8)
        ttk.Button(bar, text='По умолчанию', command=reset).pack(side='left')


def called_subs_deep(text, subs):
    seen, queue = set(), called_subs(text)
    while queue:
        no = queue.pop(0)
        if no in seen:
            continue
        seen.add(no)
        if no in subs:
            queue.extend(called_subs(subs[no]['text']))
    return seen


def tool_list(text):
    """Инструменты программы автомата: T0101(КОММЕНТАРИЙ) в порядке появления."""
    tools, seen = [], {}
    lines = (text or '').split('\n')
    for k, raw in enumerate(lines):
        code = E.strip_comment(raw)
        for m in re.finditer(r'T(\d{3,4})', code):
            t = m.group(1)
            if int(t) == 0:
                continue
            note = re.search(r'\(([^)]*)\)', raw)
            if t not in seen:
                seen[t] = dict(T=t, name=note.group(1).strip() if note else '', line=k + 1, uses=0, S=set())
                tools.append(seen[t])
            seen[t]['uses'] += 1
            if not seen[t]['name'] and note:
                seen[t]['name'] = note.group(1).strip()
    return tools


class AutoSetupWindow(MD.SetupWindow):
    """Подробности системы автомата: те же вкладки, что у фрезерных, сводка — с барьерами !L."""

    def summary_tab(self):
        s = self.setup
        r = self.tab.result
        page = ttk.Frame(self.book, padding=14)
        self.book.add(page, text='Сводка')
        ttk.Label(page, text='КОНЕЦ СИСТЕМЫ %s' % s['side'], style='Muted.TLabel').pack(anchor='w')
        ttk.Label(page, text=U.fmt_time(s['ms']), style='Big.TLabel', foreground=U.ERROR if s['incomplete'] else U.NAVY).pack(anchor='w')
        bar = tk.Canvas(page, height=10, background=U.BG, highlightthickness=0)
        bar.pack(fill='x', pady=(4, 10))
        bar.bind('<Configure>', lambda e: (bar.delete('all'), MD.MillTab.draw_bar(bar, s['cat'], e.width, AUTO_CATS)))
        frame = ttk.Frame(page)
        frame.pack(fill='x')
        table = ttk.Treeview(frame, columns=('sys', 'finish', 'own', 'cut', 'wait'), show='headings', height=3)
        for c, t, w in (('sys', 'Система', 90), ('finish', 'Конец, мин:с', 110), ('own', 'Своя работа', 110),
                        ('cut', 'Резание', 100), ('wait', 'Ожидание !L', 110)):
            table.heading(c, text=t)
            table.column(c, width=w, anchor='center')
        U.table_scroll(table)
        for c in r['cards']:
            table.insert('', 'end', values=(c['side'], U.fmt_time(c['ms']), '%.1f с' % (c['own'] / 1000),
                                            '%.1f с' % (c['cat']['cut'] / 1000), '%.1f с' % (c['wait'] / 1000)))
        ttk.Label(page, text='Синхронизация систем (барьеры !L)', style='Heading.TLabel').pack(anchor='w', pady=(14, 4))
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        bt = ttk.Treeview(frame, columns=('label', 'time', 'who'), show='headings', height=6)
        for c, t, w in (('label', 'Метка', 80), ('time', 'Момент, с', 110), ('who', 'Кто ждёт и сколько', 300)):
            bt.heading(c, text=t)
            bt.column(c, width=w, anchor='w' if c == 'who' else 'center', stretch=c == 'who')
        U.table_scroll(bt)
        for k, b in enumerate(r['rep']['barriers']):
            who = ', '.join('%s ждёт %.2f с' % (n, w / 1000) for n, w in b['waits'].items() if w > 1)
            bt.insert('', 'end', tags=('stripe',) if k % 2 else (),
                      values=('!' + b['label'], '%.2f' % (b['barrierTime'] / 1000), who or 'одновременно'))
        notes = list(r['rep']['warnings'])
        if r['missing']:
            notes.append('Не загружены подпрограммы: %s — время без них не достоверно.' % ', '.join('O' + n for n in r['missing']))
        if notes:
            ttk.Label(page, text='\n'.join('• ' + n for n in notes), wraplength=560, justify='left').pack(anchor='w', pady=(10, 0))

    def tools_tab(self):
        page = ttk.Frame(self.book, padding=14)
        self.book.add(page, text='Инструменты · %d' % len(self.setup['tools']))
        ttk.Label(page, text='В порядке первого вызова. Двойной щелчок — к строке.', style='Muted.TLabel').pack(anchor='w', pady=(0, 8))
        frame = ttk.Frame(page)
        frame.pack(fill='both', expand=True)
        table = ttk.Treeview(frame, columns=('n', 't', 'name', 'line', 'uses'), show='headings')
        for c, t, w in (('n', '№', 40), ('t', 'T', 70), ('name', 'Инструмент', 300), ('line', 'Стр.', 60), ('uses', 'Вызовов', 70)):
            table.heading(c, text=t)
            table.column(c, width=w, anchor='w' if c == 'name' else 'center', stretch=c == 'name')
        U.table_scroll(table)
        rows = {}
        for k, t in enumerate(self.setup['tools']):
            iid = table.insert('', 'end', tags=('stripe',) if k % 2 else (),
                               values=(k + 1, 'T' + t['T'], t['name'] or '—', t['line'], t['uses']))
            rows[iid] = (self.setup['file'], t['line'])
        table.bind('<Double-1>', lambda e: self.jump(table, rows, e))


def build_tab(window, book):
    tab = AutoTab(book, window)
    book.add(tab, text='Автомат · Diamond')
    return tab
