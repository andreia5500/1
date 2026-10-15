"""Имитация фрезерных станков: HAAS VF-2/VF-3 (стойка Haas) и IronMac IMV 10.55 (HNC-8).

Один интерпретатор G-кода, различия станков — в профиле (default_params) и
в правилах проверки. Источники правил:
  * HAAS — «Руководство оператора фрезерного станка» 96-0117 ред. K (2005):
    подпрограммы M97 (метка N в той же программе) и M98 (отдельная программа O),
    G04 P с точкой — секунды, без точки — мс; циклы G73/G83 (Q, I/J/K),
    G84 F — подача (в G95 — шаг), повторы — L; G154 P1–P99.
  * HNC-8 — Programming Manual (EN) и «Руководство по параметрам» (RU):
    подпрограммы O… в том же файле, M98 P L / M99, M98/M99 — отдельным кадром,
    перед M99 подпрограммы — G80; G04 X — секунды, P — мс (дробная часть P
    отбрасывается); в G84 F — шаг резьбы при любом G94/G95; G108/G109 —
    режим шпинделя (позиционный/скоростной); G54.1 P1–P60; параметр 010083
    «совместимость циклов» (0 HNC8 … 3 FANUC), 010085/010086 — отвод G73/G83.
Программы IMV пользователя написаны в стиле FANUC (Q > 0, K — число повторов),
поэтому по умолчанию для IMV выбран режим циклов FANUC.

Время — в миллисекундах.
"""
import copy
import math
import re

from nc_engine import strip_comment, tokenize_line, move_time_ms

MACHINES = ('haas', 'imv')
TITLES = {'haas': 'HAAS VF-2 / VF-3', 'imv': 'IronMac IMV 10.55 · HNC-8'}

HAAS_MODELS = {'VF-2': {'X': 762, 'Y': 406, 'Z': 508}, 'VF-3': {'X': 1016, 'Y': 508, 'Z': 635}}


def default_params(machine):
    if machine == 'haas':
        return dict(
            machine='haas', model='VF-2',
            rapid_override_pct=50,
            rapid={'X': 25400, 'Y': 25400, 'Z': 25400, 'A': 18000},   # мм/мин, A — град/мин
            accel_ms=150, feed_accel_ms=30, max_feed=16500, max_rpm=8100,
            spindle_ramp_s=1.5, tool_change_s=4.2, tap_reverse_s=0.15, tap_retract_factor=1.0,
            peck_retract=1.27, peck_clear=1.27,   # настройка 22 «Delta Z стандартных циклов» = 0.050"
            orient_s=1.0, mode_switch_s=0.0,
            travel=dict(HAAS_MODELS['VF-2']),
            part_zero={'X': -381.0, 'Y': -203.0, 'Z': -400.0},
            block_skip=True, optional_stop=False, cycle_mode='haas',
            m_times={'8': 0.2, '9': 0.1, '88': 2.0, '89': 1.0, '19': 1.0, '10': 0.4, '11': 0.4, '83': 0.2, '84': 0.1},
            m_default_s=0.3, sub_nesting=4,
        )
    return dict(
        machine='imv', model='IMV 10.55',
        rapid_override_pct=50,
        rapid={'X': 36000, 'Y': 36000, 'Z': 30000, 'A': 18000},
        accel_ms=120, feed_accel_ms=30, max_feed=10000, max_rpm=10000,
        spindle_ramp_s=1.5, tool_change_s=3.0, tap_reverse_s=0.15, tap_retract_factor=1.0,
        peck_retract=0.1, peck_clear=0.1,   # параметры 010085 / 010086, по умолчанию 0.1 мм
        orient_s=1.0, mode_switch_s=0.3,     # G108/G109 — переключение режима шпинделя
        travel={'X': 1000, 'Y': 550, 'Z': 550},
        part_zero={'X': -500.0, 'Y': -275.0, 'Z': -400.0},
        block_skip=True, optional_stop=False, cycle_mode='fanuc',
        m_times={'8': 0.2, '9': 0.1, '7': 0.2, '19': 1.0, '20': 0.2, '45': 0.3, '64': 0.0},
        m_default_s=0.3, sub_nesting=8,
    )


# ---------------------------------------------------------------- коды станков

def _codes(spec):
    out = set()
    for part in spec.split():
        if '-' in part and '.' not in part:
            a, b = part.split('-')
            out.update(float(i) for i in range(int(a), int(b) + 1))
        else:
            out.add(float(part))
    return out


G_CODES = {
    # Список G-кодов руководства оператора HAAS 96-0117
    'haas': _codes('0-4 9 10 12 13 17-21 28 29 31 35-37 40-44 47 49-61 64 65 68-74 76 77 80-95 98-103 107 '
                   '110-129 136 141 143 150 153 154 155 161-166 169 174 184 187 188'),
    # Список G-кодов фрезерной HNC-8 (Programming Manual, табл. G-кодов) + G54.1
    'imv': _codes('0-4 5.1 7 7.1 8 9 10 11 12 13 15 16 17 18 19 20 21 24 25 28 29 30 40 41 41.4 42 43 43.4 43.5 44 '
                  '49 50 51 52 53 53.1 53.2 53.3 53.4 54-59 54.1 60 61 64 65 68 68.1 68.2 68.3 68.4 69 73 74 76 80-95 '
                  '98 99 101 102 103 103.1 104 106 108 109 110 115 140 141 145 146 147 181-186 188 189'),
}
M_CODES = {
    'haas': _codes('0-6 8-13 16-19 21-28 30 31 33-36 39 41 42 50-59 61-69 75-84 86 88 89 95-99 109'),
    'imv': _codes('0-9 19-25 30 64 92 93 98 99'),
}
CYCLES = {73, 74, 76, 77, 81, 82, 83, 84, 85, 86, 87, 88, 89}
POCKETS = {12, 13, 150, 181, 182, 183, 184, 185, 186, 188, 189, 47, 1025}
AXES = ('X', 'Y', 'Z', 'A')
ARG_VARS = dict(A=1, B=2, C=3, I=4, J=5, K=6, D=7, E=8, F=9, H=11, M=13, Q=17, R=18, S=19, T=20, U=21,
                V=22, W=23, X=24, Y=25, Z=26)

# Стандартные шаги резьбы: метрические и дюймовые (25.4 / ниток на дюйм)
PITCHES = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.75, 0.8, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5,
           4.0, 4.5, 5.0, 5.5, 6.0] + [25.4 / n for n in (4, 4.5, 5, 6, 7, 8, 9, 10, 11, 11.5, 12, 13, 14, 16, 18,
                                                          19, 20, 24, 27, 28, 32, 36, 40, 44, 48, 56, 64, 72, 80)]


def standard_pitch(p):
    return any(abs(p - s) <= max(0.004, s * 0.004) for s in PITCHES)


# ---------------------------------------------------------------- выражения

_TOK = re.compile(r'\s*(?:(\d+\.?\d*|\.\d+)|([A-Z]+)|(#)|(\[|\]|\+|-|\*|/|,))')
FUNCS = {
    'SIN': lambda a: math.sin(math.radians(a)), 'COS': lambda a: math.cos(math.radians(a)),
    'TAN': lambda a: math.tan(math.radians(a)), 'ASIN': lambda a: math.degrees(math.asin(a)),
    'ACOS': lambda a: math.degrees(math.acos(a)), 'ATAN': lambda a: math.degrees(math.atan(a)),
    'SQRT': math.sqrt, 'ABS': abs, 'ROUND': lambda a: float(math.floor(abs(a) + 0.5)) * (1 if a >= 0 else -1),
    'FIX': lambda a: float(math.trunc(a)), 'FUP': lambda a: float(math.ceil(a) if a >= 0 else math.floor(a)),
    'LN': math.log, 'EXP': math.exp,
}
WORD_OPS = {'EQ', 'NE', 'GT', 'GE', 'LT', 'LE', 'AND', 'OR', 'XOR', 'MOD'}


def evaluate(expr, get):
    """Выражение макро (FANUC/Haas/HNC-8): [ ], # переменные, функции, EQ/NE…, AND/OR, MOD."""
    s = str(expr or '').upper().strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        pass
    toks = []
    i = 0
    while i < len(s):
        m = _TOK.match(s, i)
        if not m or m.end() == i:
            i += 1
            continue
        i = m.end()
        if m.group(1):
            toks.append(('n', float(m.group(1))))
        elif m.group(2):
            word = m.group(2)
            # слитно записанные операторы: «#1GE#3» уже разделены, «1.EQ» тоже
            toks.append(('w', word))
        elif m.group(3):
            toks.append(('#', '#'))
        else:
            toks.append(('o', m.group(4)))
    pos = [0]

    def peek(k=0):
        j = pos[0] + k
        return toks[j] if j < len(toks) else (None, None)

    def take():
        t = peek()
        pos[0] += 1
        return t

    def primary():
        kind, val = peek()
        if kind == 'o' and val == '[':
            take()
            v = comp()
            if peek() == ('o', ']'):
                take()
            return v
        if kind == 'o' and val in '-+':
            take()
            v = primary()
            return -v if val == '-' else v
        if kind == 'n':
            take()
            return val
        if kind == '#':
            take()
            if peek() == ('o', '['):
                n = primary()
            else:
                k2, v2 = take()
                n = v2 if k2 == 'n' else 0
            v = get(int(n))
            return 0.0 if v is None else v
        if kind == 'w' and val in FUNCS:
            take()
            a = primary()
            if val == 'ATAN' and peek() == ('o', '/') and peek(1) == ('o', '['):
                take()
                b = primary()
                return math.degrees(math.atan2(a, b))
            try:
                return float(FUNCS[val](a))
            except (ValueError, ZeroDivisionError, OverflowError):
                return 0.0
        take()
        return 0.0

    def mul():
        v = primary()
        while True:
            kind, val = peek()
            if (kind == 'o' and val in '*/') or (kind == 'w' and val in ('AND', 'MOD')):
                take()
                r = primary()
                if val == '*':
                    v *= r
                elif val == '/':
                    v = v / r if r else 0.0
                elif val == 'AND':
                    v = float(int(v) & int(r))
                else:
                    v = math.fmod(v, r) if r else 0.0
            else:
                return v

    def add():
        v = mul()
        while True:
            kind, val = peek()
            if (kind == 'o' and val in '+-') or (kind == 'w' and val in ('OR', 'XOR')):
                take()
                r = mul()
                if val == '+':
                    v += r
                elif val == '-':
                    v -= r
                elif val == 'OR':
                    v = float(int(v) | int(r))
                else:
                    v = float(int(v) ^ int(r))
            else:
                return v

    def comp():
        v = add()
        kind, val = peek()
        if kind == 'w' and val in ('EQ', 'NE', 'GT', 'GE', 'LT', 'LE'):
            take()
            r = add()
            eps = 1e-9
            return float({'EQ': abs(v - r) < eps, 'NE': abs(v - r) >= eps, 'GT': v > r + eps, 'GE': v >= r - eps,
                          'LT': v < r - eps, 'LE': v <= r + eps}[val])
        return v

    try:
        return comp()
    except (RecursionError, OverflowError):
        return 0.0


# ---------------------------------------------------------------- разбор файлов

def _num_key(n):
    return str(int(n)) if str(n).isdigit() else str(n)


def parse_blocks(text):
    """Кадры с номерами строк. Пустые и комментарии пропускаются, '%' — тоже."""
    out = []
    for idx, raw in enumerate(re.split(r'\r?\n', text or '')):
        line = raw.replace('\x1a', '')
        comment = ' '.join(re.findall(r'\(([^)]*)\)', line)).strip()
        clean = strip_comment(line)
        skip = False
        if clean.startswith('/'):
            skip = True
            clean = re.sub(r'^/\d?\s*', '', clean)
        if not clean or clean == '%':
            continue
        head = None
        m = re.match(r'^(?:O|%)(\d+)\b', clean, re.I) if not skip else None
        if m:
            head = _num_key(m.group(1))
        label = None
        rest = clean
        m = re.match(r'^N(\d+)\s*(.*)$', rest, re.I | re.S)
        if m:
            label, rest = _num_key(m.group(1)), m.group(2)
        out.append(dict(line=idx + 1, raw=raw.rstrip(), text=clean, skip=skip, head=head, label=label,
                        comment=comment, tokens=[] if head else tokenize_line(rest)))
    return out


def _words(block):
    return [t for t in block['tokens'] if t['type'] == 'word']


def _has_m(block, codes):
    for w in _words(block):
        if w['letter'] == 'M':
            try:
                if float(w['valueExpr']) in codes:
                    return True
            except ValueError:
                pass
    return False


def split_programs(file_name, text):
    """Файл -> программы: [dict(no, title, file, blocks, kind)]. Новая программа — строка O…/%…."""
    blocks = parse_blocks(text)
    stem = re.sub(r'\D', '', file_name.rsplit('.', 1)[0]) or file_name
    progs = []
    cur = None
    for b in blocks:
        if b['head'] is not None:
            cur = dict(no=b['head'], title=b['comment'], file=file_name, blocks=[], head_line=b['line'])
            progs.append(cur)
            continue
        if cur is None:
            cur = dict(no=_num_key(stem) if stem.isdigit() else stem, title='', file=file_name, blocks=[], head_line=None)
            progs.append(cur)
        cur['blocks'].append(b)
    for p in progs:
        has_end = any(_has_m(b, {30.0, 2.0}) for b in p['blocks'])
        has_ret = any(_has_m(b, {99.0}) for b in p['blocks'])
        p['kind'] = 'main' if has_end else ('sub' if has_ret else 'main')
        p['labels'] = {}
        for i, b in enumerate(p['blocks']):
            if b['label'] is not None:
                p['labels'].setdefault(b['label'], i)
        p['loops'] = _loop_pairs(p['blocks'])
    return progs


def _loop_pairs(blocks):
    pairs, stack = {}, []
    for i, b in enumerate(blocks):
        for t in b['tokens']:
            if t['type'] == 'while':
                stack.append((t['doNum'], i))
            elif t['type'] == 'end':
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][0] == t['endNum']:
                        _, w = stack.pop(k)
                        pairs[w] = i
                        pairs[i] = w
                        break
    return pairs


def load_files(files, machine='haas'):
    """files: [(имя, текст)] -> (все программы, реестр, замечания о файлах).

    Реестр: номер -> программа для программ, видимых из любого файла (на HAAS —
    все O…, на HNC-8 — первая программа файла); подпрограммы HNC-8 внутри файла
    видны только этому файлу (registry['@файл'][номер]).
    """
    programs, registry, notes = [], {}, []
    for name, text in files:
        local = registry.setdefault('@' + name, {})
        for k, p in enumerate(split_programs(name, text)):
            programs.append(p)
            if p['no'] in local:
                notes.append(issue('error', 'O' + p['no'], 'Номер O%s дважды в файле %s — станок вызовет первый блок.' %
                                   (p['no'], name), name, p['no'], p['head_line']))
                continue
            local[p['no']] = p
            if machine == 'imv' and k > 0:
                continue
            if p['no'] in registry:
                other = registry[p['no']]
                notes.append(issue('error', 'O' + p['no'], 'Номер O%s повторяется: %s и %s. Станок загрузит только одну '
                                   'из программ (или откажется загружать файл).' % (p['no'], other['file'], p['file']),
                                   p['file'], p['no'], p['head_line']))
                continue
            registry[p['no']] = p
    return programs, registry, notes


def find_program(registry, no, file):
    """Подпрограмма для вызова из файла file: сначала тот же файл, затем общие. (программа, из чужого файла?)"""
    local = registry.get('@' + file, {})
    if no in local:
        return local[no], False
    if no in registry:
        return registry[no], False
    for key, progs in registry.items():
        if key.startswith('@') and no in progs:
            return progs[no], True
    return None, False


def issue(severity, code, message, file=None, prog=None, line=None, certain=True):
    return dict(severity=severity, code=code, message=message, file=file, prog=prog, line=line, certain=certain)


# ---------------------------------------------------------------- имитация

class Stop(Exception):
    pass


class MillSim:
    MAX_BLOCKS = 400000
    MAX_LOOP = 100000

    def __init__(self, params, registry, main):
        self.p = params
        self.machine = params['machine']
        self.registry = registry
        self.main = main
        self.t = 0.0
        self.cat = dict(cut=0.0, rapid=0.0, tool=0.0, spindle=0.0, dwell=0.0, aux=0.0)
        self.issues = []
        self.blocks = []
        self.tools = []
        self.tool_row = None
        self.executed = set()
        self.notes = set()
        self.incomplete = False
        self.stops = []
        # станок в нуле, программа в абсолютных, мм, G17, G94
        self.mach = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'A': 0.0}
        self.vars = {}
        self.frames = []
        self.st = dict(motion=0, absolute=True, plane=17, feed_mode=94, inch=False, F=0.0, S=0.0, spindle=0,
                       coolant=False, T=None, next_T=None, H=None, D=None, comp=40, lencomp=False, cycle=None,
                       ret=98, cyc={}, init_z=None, rot=None, scale=None, g52={'X': 0.0, 'Y': 0.0, 'Z': 0.0},
                       wcs='G54', spindle_ready=0.0, last_dir=None, need_g43=False, cut_since_tool=False,
                       coolant_warned=False, spindle_mode='speed', S_running=0.0, comp_new=False)
        self.prog = dict(self.work_of_mach())
        self.cur = None
        self.span = {a: [math.inf, -math.inf] for a in AXES}
        self.path = []          # для прорисовки: dict(kind, pts=[(x, y, z) от нуля детали], line, file, tool)

    # -------------------------------------------------- журнал
    def add(self, ms, cat, note=None):
        if ms <= 0:
            return
        self.t += ms
        self.cat[cat] += ms
        if self.cur is not None:
            self.cur['ms'] += ms
            if note:
                self.cur['notes'].append(note)
        if self.tool_row is not None:
            self.tool_row['ms'] += ms
            if cat == 'cut':
                self.tool_row['cut_ms'] += ms

    def flag(self, severity, code, message, certain=True, block=None, prog=None):
        b = block or (self.cur and self.cur['block'])
        pr = prog or (self.cur and self.cur['prog'])
        key = (code, message, pr and pr['file'], b and b['line'])
        if key in self.notes:
            return
        self.notes.add(key)
        self.issues.append(issue(severity, code, message, pr and pr['file'], pr and pr['no'], b and b['line'], certain))

    def note_once(self, code, message, certain=False):
        key = ('once', code)
        if key in self.notes:
            return
        self.notes.add(key)
        self.flag('warning', code, message, certain)

    # -------------------------------------------------- переменные
    def get_var(self, n):
        if 1 <= n <= 33 and self.frames and self.frames[-1].get('locals') is not None:
            return self.frames[-1]['locals'].get(n)
        if n == 0:
            return None
        if n in self.vars:
            return self.vars[n]
        if n >= 1000 and n not in (3000,):
            self.note_once('#%d' % n, 'Системная переменная #%d — её значение на станке неизвестно, при расчёте принято 0. '
                           'Если от неё зависят ветви программы (гравировка номера, счётчики), время может немного отличаться.' % n)
        return None

    def set_var(self, n, v):
        if 1 <= n <= 33 and self.frames and self.frames[-1].get('locals') is not None:
            self.frames[-1]['locals'][n] = v
        elif n == 3000:
            self.flag('error', '#3000', 'Программная авария #3000 = %g — станок остановится.' % v)
            raise Stop()
        else:
            self.vars[n] = v

    def ev(self, expr):
        return evaluate(expr, self.get_var)

    # -------------------------------------------------- координаты
    def offset(self, a):
        return self.p['part_zero'].get(a, 0.0) + (self.st['g52'].get(a, 0.0) if a != 'A' else 0.0)

    def work_of_mach(self):
        w = {a: self.mach[a] - self.offset(a) for a in AXES}
        rot = self.st['rot'] if hasattr(self, 'st') else None
        if rot:
            cx, cy, ang = rot
            c, s = math.cos(-ang), math.sin(-ang)
            dx, dy = w['X'] - cx, w['Y'] - cy
            w['X'], w['Y'] = cx + dx * c - dy * s, cy + dx * s + dy * c
        return w

    def to_mach(self, prog):
        x, y, z = prog['X'], prog['Y'], prog['Z']
        if self.st['scale']:
            cx, cy, cz, k = self.st['scale']
            x, y, z = cx + (x - cx) * k, cy + (y - cy) * k, cz + (z - cz) * k
        if self.st['rot']:
            cx, cy, ang = self.st['rot']
            c, s = math.cos(ang), math.sin(ang)
            dx, dy = x - cx, y - cy
            x, y = cx + dx * c - dy * s, cy + dx * s + dy * c
        return {'X': x + self.offset('X'), 'Y': y + self.offset('Y'), 'Z': z + self.offset('Z'), 'A': prog['A']}

    def target(self, vals):
        t = dict(self.prog)
        for a in AXES:
            if a in vals:
                t[a] = (t[a] + vals[a]) if not self.st['absolute'] else vals[a]
        return t

    def check_travel(self, mach, certain=False):
        for a in ('X', 'Y', 'Z'):
            lim = self.p['travel'].get(a)
            if lim is None:
                continue
            v = mach[a]
            if v > 0.5 or v < -lim - 0.5:
                if certain:
                    self.flag('error', 'Ход ' + a, 'Выход за ход по оси %s: машинная координата %.1f мм, допустимо 0…−%g. '
                              'Станок выдаст аварию программного концевого выключателя.' % (a, v, lim))
                else:
                    self.flag('warning', 'Ход ' + a, 'Возможный выход за ход по оси %s (машинная %.1f при нуле детали %s=%.0f из '
                              'параметров). Проверьте реальную привязку.' % (a, v, a, self.p['part_zero'][a]), certain=False)

    def note_span(self, prog):
        for a in AXES:
            v = prog[a]
            self.span[a][0] = min(self.span[a][0], v)
            self.span[a][1] = max(self.span[a][1], v)

    # -------------------------------------------------- траектория
    def work_pt(self, m):
        pz = self.p['part_zero']
        return (m['X'] - pz['X'], m['Y'] - pz['Y'], m['Z'] - pz['Z'])

    def record(self, kind, machs):
        if len(machs) < 2:
            return
        if kind == 'rapid' and any(m['Z'] > -1.0 for m in machs):   # подъём в точку смены / G53 Z0 — не рисуем
            return
        b = self.cur['block'] if self.cur else None
        pr = self.cur['prog'] if self.cur else None
        self.path.append(dict(kind=kind, pts=[self.work_pt(m) for m in machs], line=b and b['line'], file=pr and pr['file'],
                              tool=str(self.st['T']) if self.st['T'] is not None else None))

    # -------------------------------------------------- движение
    def rapid_to(self, mach, note='G0'):
        ovr = max(1.0, float(self.p['rapid_override_pct'])) / 100.0
        worst = 0.0
        for a in AXES:
            d = abs(mach[a] - self.mach[a])
            if d > 1e-9:
                rate = self.p['rapid'].get(a, 10000) * ovr
                worst = max(worst, move_time_ms(d, rate, self.p['accel_ms']))
        self.record('rapid', [dict(self.mach), dict(mach)])
        self.mach = dict(mach)
        self.st['last_dir'] = None
        self.add(worst, 'rapid', note)
        return worst

    def wait_spindle(self):
        if self.st['spindle'] == 0:
            return
        wait = self.st['spindle_ready'] - self.t
        if wait > 1:
            self.add(wait, 'spindle', 'ожидание разгона шпинделя %.2f с' % (wait / 1000))

    def feed_rate(self, what='подача'):
        f = self.st['F']
        if f <= 0:
            self.flag('error', 'F', 'Рабочее перемещение без подачи F — станок выдаст аварию «нулевая подача».')
            return 0.0
        if self.st['feed_mode'] == 95:
            if self.st['S'] <= 0 or self.st['spindle'] == 0:
                return 0.0
            f = f * self.st['S']
        if f > self.p['max_feed']:
            self.flag('warning', 'F', 'Подача %.0f мм/мин больше максимальной %g — станок ограничит её.' % (f, self.p['max_feed']))
            f = self.p['max_feed']
        return f

    def check_cut(self):
        st = self.st
        if st['spindle'] == 0:
            self.flag('error', 'Шпиндель', 'Рабочее перемещение при остановленном шпинделе (нет M3/M4 после смены инструмента или M5).')
        if st['need_g43']:
            self.flag('error', 'G43', 'После смены инструмента T%s нет G43 H… — резание без коррекции на длину.' % st['T'])
            st['need_g43'] = False
        if not st['coolant'] and not st['coolant_warned']:
            st['coolant_warned'] = True
            self.flag('warning', 'СОЖ', 'Резание инструментом T%s без включённой СОЖ (M8/M88). Проверьте, что так задумано.' % st['T'],
                      certain=False)
        st['cut_since_tool'] = True

    def corner_ms(self, direction):
        last = self.st['last_dir']
        k = 1.0 if last is None else max(0.0, (1 - sum(a * b for a, b in zip(last, direction))) / 2)
        return self.p['feed_accel_ms'] * k

    def feed_to(self, prog, note='G1'):
        mach = self.to_mach(prog)
        d = [mach[a] - self.mach[a] for a in AXES]
        lin = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
        length = math.sqrt(lin ** 2 + d[3] ** 2)
        self.check_cut()
        self.wait_spindle()
        if self.st['feed_mode'] == 93:
            ms = 60000.0 / self.st['F'] if self.st['F'] > 0 else 0.0
        else:
            f = self.feed_rate()
            ms = length / f * 60000 if f > 0 and length > 0 else 0.0
        if length > 1e-9:
            u = [x / length for x in d[:3]] if lin > 1e-9 else [0, 0, 0]
            ms += self.corner_ms(u)
            self.st['last_dir'] = u
        self.record('feed', [dict(self.mach), dict(mach)])
        self.mach = mach
        self.prog = prog
        self.note_span(prog)
        self.track_feed()
        self.add(ms, 'cut', '%s L=%.2f мм' % (note, length))

    def arc_to(self, prog, cw, vals, note):
        plane = self.st['plane']
        a1, a2, a3, c1, c2 = {17: ('X', 'Y', 'Z', 'I', 'J'), 18: ('Z', 'X', 'Y', 'K', 'I'), 19: ('Y', 'Z', 'X', 'J', 'K')}[plane]
        code = 'G%d' % (2 if cw else 3)
        s1, s2 = self.prog[a1], self.prog[a2]
        e1, e2 = prog[a1], prog[a2]
        scale = self.st['scale'][3] if self.st['scale'] else 1.0
        if 'R' in vals:
            r = vals['R']
            chord = math.hypot(e1 - s1, e2 - s2)
            if chord < 1e-6:
                self.flag('error', code + ' R', 'Дуга через R с совпадающими начальной и конечной точками — полную '
                          'окружность через R задать нельзя (станок выдаст аварию).')
                return self.feed_to(prog, note)
            if chord > 2 * abs(r) + 0.01:
                self.flag('error', code + ' R', 'Радиус R%.3f меньше половины хорды %.3f — станок выдаст аварию '
                          '«неверный радиус дуги».' % (abs(r), chord / 2))
                r = math.copysign(chord / 2, r)
            radius = abs(r)
            m1, m2 = (s1 + e1) / 2, (s2 + e2) / 2
            h = math.sqrt(max(0.0, radius ** 2 - (chord / 2) ** 2))
            # центр слева от хорды для G3 с R>0, справа для G2 с R>0
            n1, n2 = -(e2 - s2) / chord, (e1 - s1) / chord
            side = (1 if not cw else -1) * (1 if r > 0 else -1)
            o1, o2 = m1 + side * h * n1, m2 + side * h * n2
        else:
            if c1 not in vals and c2 not in vals:
                self.flag('error', code, 'Дуга без центра (I/J/K) и без R — станок выдаст аварию.')
                return self.feed_to(prog, note)
            o1, o2 = s1 + vals.get(c1, 0.0), s2 + vals.get(c2, 0.0)
            radius = math.hypot(s1 - o1, s2 - o2)
            r_end = math.hypot(e1 - o1, e2 - o2)
            if abs(radius - r_end) > max(0.02, radius * 0.001):
                self.flag('error', 'Дуга', 'Начальный и конечный радиусы дуги различаются на %.3f мм (R %.3f / %.3f) — '
                          'станок выдаст аварию «ошибка центра дуги».' % (abs(radius - r_end), radius, r_end))
        ang_s = math.atan2(s2 - o2, s1 - o1)
        ang_e = math.atan2(e2 - o2, e1 - o1)
        sweep = ((ang_s - ang_e) if cw else (ang_e - ang_s)) % (2 * math.pi)
        if sweep < 1e-9 and 'R' not in vals:
            sweep = 2 * math.pi
        if self.st['comp'] != 40 and self.st.get('comp_new'):
            self.flag('error', 'G41/G42', 'Включение коррекции на радиус G41/G42 в кадре дуги — станок выдаст аварию. '
                      'Включайте коррекцию на линейном перемещении G0/G1.')
        helix = prog[a3] - self.prog[a3]
        length = math.hypot(radius * sweep * scale, helix)
        self.check_cut()
        self.wait_spindle()
        f = self.feed_rate()
        ms = length / f * 60000 if f > 0 else 0.0

        def tangent(ang):
            d = -1 if cw else 1
            v = {a1: -math.sin(ang) * d, a2: math.cos(ang) * d, a3: 0.0}
            return [v['X'], v['Y'], v['Z']]
        ms += self.corner_ms(tangent(ang_s))
        self.st['last_dir'] = tangent(ang_e)
        n = max(2, int(math.degrees(sweep) / 6) + 1)
        pts = []
        for k in range(n + 1):
            ang = ang_s + (-1 if cw else 1) * sweep * k / n
            q = dict(self.prog)
            q[a1], q[a2] = o1 + radius * math.cos(ang), o2 + radius * math.sin(ang)
            q[a3] = self.prog[a3] + helix * k / n
            pts.append(self.to_mach(q))
        pts[-1] = self.to_mach(prog)
        self.record('feed', [dict(self.mach)] + pts[1:])
        self.mach = self.to_mach(prog)
        self.prog = prog
        self.note_span(prog)
        self.track_feed()
        self.add(ms, 'cut', '%s R=%.2f дуга %.0f° L=%.2f мм' % (note, radius, math.degrees(sweep), length))

    def track_feed(self):
        row = self.tool_row
        if row is not None and self.st['F'] > 0:
            row['F'].add(round(self.st['F'], 3))

    # -------------------------------------------------- циклы
    def cycle_hole(self, g, vals, prog_xy):
        st, p = self.st, self.p
        cyc = st['cyc']
        mode = p['cycle_mode'] if self.machine == 'imv' else 'haas'
        if 'R' not in cyc or 'Z' not in cyc:
            self.flag('error', 'G%d' % g, 'В цикле G%d не заданы %s — станок выдаст аварию.' %
                      (g, ' и '.join(k for k in ('R', 'Z') if k not in cyc)))
            return
        if cyc.get('F', 0) <= 0 and st['F'] <= 0:
            self.flag('error', 'G%d F' % g, 'В цикле G%d не задана подача F.' % g)
        self.check_cut()
        b = st['init_z']
        r = cyc['R'] if cyc['abs'] else b + cyc['R']
        z = cyc['Z'] if cyc['abs'] else r + cyc['Z']
        if z > r:
            self.flag('error', 'G%d Z' % g, 'Дно отверстия Z%.3f выше плоскости R%.3f — станок выдаст аварию.' % (z, r))
            return
        if r > b + 1e-6 and st['ret'] == 98:
            self.flag('warning', 'G%d R' % g, 'Плоскость R%.3f выше исходной точки Z%.3f — отвод G98 пойдёт к R.' % (r, b), certain=False)
        # 1. позиционирование XY (+A) на ускоренном
        pos = dict(self.prog)
        pos.update(prog_xy)
        pos['Z'] = self.prog['Z']
        self.rapid_to(self.to_mach(pos), 'позиционирование')
        self.prog = pos
        # 2. к R
        pos_r = dict(pos, Z=r)
        self.rapid_to(self.to_mach(pos_r), 'к R')
        self.wait_spindle()
        depth = r - z
        f = self.feed_rate()
        if g in (84, 74):
            f = self.tap_feed(g)
        fm = 60000.0 / f if f > 0 else 0.0   # мс на мм
        rapid = lambda dist: max(0.0, self.rapid_dist(dist))
        dwell = self.cycle_dwell(cyc.get('P'), mode)
        note = 'G%d глуб. %.2f' % (g, depth)
        if g == 73 or g == 83:
            pecks = self.pecks(cyc, depth, mode)
            d = (cyc.get('K') if mode == 'hnc8' and cyc.get('K') else
                 (p['peck_retract'] if g == 73 else p['peck_clear']))
            done = 0.0
            for k, q in enumerate(pecks):
                start = max(0.0, done - d) if k else 0.0
                self.add((done + q - start) * fm, 'cut')
                done += q
                if k < len(pecks) - 1:
                    if g == 73:
                        self.add(rapid(d), 'rapid')
                    else:
                        self.add(rapid(done) + rapid(max(0.0, done - d)), 'rapid')
            note += ', проходов %d по %.2f' % (len(pecks), pecks[0] if pecks else 0)
            self.add(dwell, 'dwell')
            self.add(rapid(depth), 'rapid')
        elif g in (84, 74):
            q = cyc.get('Q') or 0.0
            pecks = self.pecks(cyc, depth, mode) if q > 0 else [depth]
            back = fm / max(0.1, p['tap_retract_factor'])
            done = 0.0
            for k, qq in enumerate(pecks):
                self.add((qq + (done if k else 0)) * fm, 'cut')
                done += qq
                self.add(p['tap_reverse_s'] * 1000, 'spindle')
                if k == len(pecks) - 1:
                    self.add(dwell, 'dwell')
                self.add(done * back, 'cut')
                self.add(p['tap_reverse_s'] * 1000, 'spindle')
            note += ', шаг %.3f, подача %.0f мм/мин' % (f / st['S'] if st['S'] else 0, f)
        elif g in (85, 89):
            self.add(depth * fm, 'cut')
            self.add(dwell if g == 89 else 0, 'dwell')
            self.add(depth * fm, 'cut')
        elif g == 86:
            self.add(depth * fm, 'cut')
            self.add(rapid(depth), 'rapid')
            self.add(p['spindle_ramp_s'] * 1000 * min(1.0, st['S'] / max(1, p['max_rpm'])), 'spindle')
        elif g in (76, 77, 87):
            self.add(depth * fm, 'cut')
            self.add(dwell, 'dwell')
            self.add(p['orient_s'] * 1000, 'spindle')
            self.add(rapid(depth), 'rapid')
        elif g == 88:
            self.add(depth * fm, 'cut')
            self.add(dwell, 'dwell')
            self.flag('warning', 'G88', 'G88 — отвод вручную: станок остановится и ждёт оператора, время ожидания не учтено.')
            self.add(rapid(depth), 'rapid')
        else:  # 81, 82
            self.add(depth * fm, 'cut')
            self.add(dwell, 'dwell')
            self.add(rapid(depth), 'rapid')
        self.st['last_dir'] = None
        bottom = self.to_mach(dict(pos, Z=z))
        self.record('drill', [self.to_mach(pos_r), bottom])
        # 3. возврат G98 / G99
        end_z = b if st['ret'] == 98 else r
        self.record('rapid', [bottom, self.to_mach(dict(pos, Z=end_z))])
        if st['ret'] == 98 and end_z > r:
            self.add(rapid(end_z - r), 'rapid')
        final = dict(pos, Z=end_z)
        self.mach = self.to_mach(final)
        self.prog = final
        self.note_span(dict(pos, Z=z))
        self.track_feed()
        if self.cur is not None:
            self.cur['notes'].append(note)
        if self.tool_row is not None:
            self.tool_row['holes'] += 1

    def rapid_dist(self, dist):
        ovr = max(1.0, float(self.p['rapid_override_pct'])) / 100.0
        return move_time_ms(abs(dist), self.p['rapid'].get('Z', 10000) * ovr, self.p['accel_ms'])

    def pecks(self, cyc, depth, mode):
        if depth <= 0:
            return [0.0]
        if mode == 'haas' and cyc.get('I'):
            i, j, k = abs(cyc['I']), abs(cyc.get('J') or 0), abs(cyc.get('K') or 0)
            out, left, q = [], depth, i
            while left > 1e-9 and len(out) < 10000:
                step = min(left, max(q, k or q))
                out.append(step)
                left -= step
                q = max(q - j, k) if k else max(q - j, 1e-3)
            return out
        q = abs(cyc.get('Q') or 0.0)
        if q <= 1e-9:
            self.flag('warning', 'Q', 'В цикле глубокого сверления не задан Q — сверление на всю глубину за один проход.',
                      certain=False)
            return [depth]
        n = int(math.ceil(depth / q - 1e-9))
        if n > 2000:
            self.flag('error', 'Q', 'Шаг Q%.3f даёт %d проходов — проверьте Q (возможно, пропущена точка).' % (q, n))
            n = 2000
            q = depth / n
        return [q] * (n - 1) + [depth - q * (n - 1)]

    def cycle_dwell(self, pv, mode):
        if pv is None:
            return 0.0
        val, raw = pv
        if mode == 'haas':
            return val * 1000 if '.' in raw else val
        return float(int(val))

    def tap_feed(self, g):
        st = self.st
        f = st['cyc'].get('F', st['F'])
        s = st['S']
        if st['spindle'] == 0 or s <= 0:
            return 0.0
        if self.machine == 'imv':
            lead = f if f < 20 or st['feed_mode'] == 95 else f / s
            if st['feed_mode'] == 94 and f >= 20:
                self.flag('warning', 'G84 F', 'На HNC-8 в G84 F — шаг резьбы (подача = S × F). F%.0f похоже на мм/мин — '
                          'станок примет его за шаг!' % f)
        else:
            lead = f if st['feed_mode'] == 95 else f / s
        if not standard_pitch(lead):
            self.flag('warning', 'G%d шаг' % g, 'Шаг резьбы %.4f мм (F%s при S%.0f) не совпадает со стандартным метрическим '
                      'или дюймовым — проверьте F.' % (lead, ('%g' % f), s), certain=False)
        want = 3 if g == 84 else 4
        if st['spindle'] != want:
            self.flag('warning', 'G%d M%d' % (g, want), 'G%d нарезает %s резьбу, а шпиндель включён M%d.' %
                      (g, 'правую' if g == 84 else 'левую', st['spindle']))
        return lead * s

    # -------------------------------------------------- инструмент/шпиндель
    def tool_change(self, block):
        st, p = self.st, self.p
        t = st['next_T']
        if t is None:
            self.flag('error', 'M6', 'M6 без номера инструмента T — станок выдаст аварию.')
            return
        if st['comp'] != 40:
            self.flag('warning', 'G40', 'Смена инструмента при включённой коррекции на радиус G41/G42 — отмените G40 до M6.')
        if st['cycle']:
            self.flag('warning', 'G80', 'Смена инструмента при активном цикле G%d — нужен G80.' % st['cycle'])
        if t == st['T']:
            self.flag('warning', 'M6', 'T%s уже в шпинделе — смена не выполняется.' % t, certain=False)
        home = dict(self.mach, Z=0.0)
        self.rapid_to(home, 'Z в точку смены')
        self.add(p['tool_change_s'] * 1000, 'tool', 'смена T%s' % t)
        self.close_tool()
        st['T'] = t
        st['spindle'] = 0
        st['need_g43'] = True
        st['cut_since_tool'] = False
        st['coolant_warned'] = False
        self.prog = self.work_of_mach()
        self.tool_row = dict(T=t, name=block['comment'], file=self.cur['prog']['file'], line=block['line'], H=set(), D=set(),
                             S=set(), F=set(), ms=0.0, cut_ms=0.0, holes=0, start=self.t)
        self.tools.append(self.tool_row)

    def close_tool(self):
        self.tool_row = None

    def spindle_on(self, m, s=None):
        st, p = self.st, self.p
        if s is not None:
            st['S'] = s
        if st['S'] <= 0:
            self.flag('error', 'S', 'M%d без оборотов S — шпиндель не запустится.' % m)
            return
        if st['S'] > p['max_rpm']:
            self.flag('error', 'S', 'S%.0f больше максимальных %g об/мин — станок ограничит обороты или выдаст аварию.' %
                      (st['S'], p['max_rpm']))
        old = st['S_running'] if st['spindle'] == m else 0.0
        if st['spindle'] and st['spindle'] != m:
            old = -st.get('S_running', 0.0)
        ramp = abs(min(st['S'], p['max_rpm']) - old) / max(1.0, p['max_rpm']) * p['spindle_ramp_s'] * 1000
        st['spindle_ready'] = max(st['spindle_ready'], self.t) + ramp
        st['spindle'] = m
        st['S_running'] = min(st['S'], p['max_rpm'])
        if self.tool_row is not None:
            self.tool_row['S'].add(round(st['S']))

    # -------------------------------------------------- выполнение
    def run(self):
        main = self.main
        self.frames.append(dict(prog=main, ip=0, locals=None, ret=None, loops={}))
        steps = 0
        try:
            while self.frames:
                fr = self.frames[-1]
                prog = fr['prog']
                if fr['ip'] >= len(prog['blocks']):
                    if len(self.frames) == 1:
                        self.flag('warning', 'M30', 'Программа O%s закончилась без M30/M02 — станок остановится в конце файла, '
                                  'но не выполнит сброс (M30) и не посчитает деталь.' % prog['no'], block=prog['blocks'][-1] if prog['blocks'] else None, prog=prog)
                        break
                    self.flag('error', 'M99', 'Подпрограмма O%s закончилась без M99.' % prog['no'], prog=prog)
                    self.frames.pop()
                    continue
                steps += 1
                if steps > self.MAX_BLOCKS:
                    self.flag('error', 'Цикл', 'Выполнено более %d кадров — вероятно, бесконечный цикл. Расчёт остановлен.' % self.MAX_BLOCKS)
                    self.incomplete = True
                    break
                block = prog['blocks'][fr['ip']]
                fr['ip'] += 1
                if block['skip'] and self.p['block_skip']:
                    continue
                self.executed.add((prog['file'], prog['no'], block['line']))
                self.cur = dict(prog=prog, block=block, ms=0.0, notes=[], start=self.t)
                result = self.exec_block(block, fr)
                if self.cur['ms'] > 0 or self.cur['notes']:
                    self.blocks.append(dict(file=prog['file'], prog=prog['no'], line=block['line'], raw=block['raw'].strip(),
                                            ms=self.cur['ms'], note='; '.join(self.cur['notes'])))
                self.cur = None
                if result == 'end':
                    break
        except Stop:
            self.incomplete = True
        self.finish()
        return self

    def finish(self):
        st = self.st
        if st['rot']:
            self.flag('warning', 'G69', 'Поворот G68 не отменён (G69) к концу программы — следующая программа начнёт '
                      'с повёрнутой системой.', prog=self.main, block=None)
        if st['scale']:
            self.flag('warning', 'G50', 'Масштабирование G51 не отменено (G50) к концу программы.', prog=self.main)
        if any(abs(v) > 1e-9 for v in st['g52'].values()):
            self.flag('warning', 'G52', 'Локальное смещение G52 не сброшено (G52 X0 Y0) к концу программы.', prog=self.main)
        for a in ('X', 'Y', 'Z'):
            lo, hi = self.span[a]
            lim = self.p['travel'].get(a)
            if lim and hi > lo and hi - lo > lim:
                self.flag('error', 'Ход ' + a, 'Размах перемещений по %s — %.1f мм больше хода станка %g мм.' % (a, hi - lo, lim),
                          prog=self.main)
        self.close_tool()

    def words(self, block):
        vals, gs, ms = {}, [], []
        raw = {}
        inch = 25.4 if self.st['inch'] else 1.0
        for t in block['tokens']:
            if t['type'] != 'word':
                continue
            letter = t['letter']
            v = self.ev(t['valueExpr'])
            if letter == 'G':
                gs.append(round(v, 1))
            elif letter == 'M':
                ms.append(int(round(v)))
            else:
                if letter in 'XYZIJKRQ':
                    v *= inch
                vals[letter] = v
                raw[letter] = t['valueExpr']
        return vals, gs, ms, raw

    def exec_block(self, block, fr):
        st, prog = self.st, fr['prog']
        toks = block['tokens']
        # IF / THEN / GOTO / WHILE / END / присваивания
        i = 0
        while i < len(toks):
            t = toks[i]
            if t['type'] == 'if':
                cond = self.ev(t['cond'])
                nxt = toks[i + 1] if i + 1 < len(toks) else None
                if nxt and nxt['type'] == 'goto':
                    if cond:
                        return self.goto(fr, nxt['target'])
                    return None
                if nxt and nxt['type'] == 'then':
                    if not cond:
                        return None
                    toks = toks[i + 2:]
                    i = 0
                    continue
                return None
            if t['type'] == 'goto':
                return self.goto(fr, t['target'])
            if t['type'] == 'while':
                ip = fr['ip'] - 1
                if self.ev(t['cond']):
                    fr['loops'][ip] = fr['loops'].get(ip, 0) + 1
                    if fr['loops'][ip] > self.MAX_LOOP:
                        self.flag('error', 'WHILE', 'Цикл WHILE выполнен более %d раз — вероятно, бесконечный.' % self.MAX_LOOP)
                        raise Stop()
                else:
                    end = prog['loops'].get(ip)
                    if end is None:
                        self.flag('error', 'WHILE', 'WHILE без парного END.')
                        raise Stop()
                    fr['loops'][ip] = 0
                    fr['ip'] = end + 1
                return None
            if t['type'] == 'end':
                start = prog['loops'].get(fr['ip'] - 1)
                if start is None:
                    self.flag('error', 'END', 'END без парного WHILE.')
                    return None
                fr['ip'] = start
                return None
            if t['type'] == 'assign':
                self.set_var(int(t['varNum'] or 0), self.ev(t['expr']))
            i += 1
        block_words = [t for t in toks if t['type'] == 'word']
        if not block_words:
            return None
        sub = dict(block, tokens=block_words)
        vals, gs, ms, raw = self.words(sub)
        return self.exec_words(block, fr, vals, gs, ms, raw)

    def goto(self, fr, target):
        prog = fr['prog']
        key = _num_key(target)
        if key not in prog['labels']:
            self.flag('error', 'GOTO', 'Переход GOTO%s: метки N%s нет в программе — станок выдаст аварию.' % (target, key))
            raise Stop()
        fr['ip'] = prog['labels'][key]
        return None

    def call(self, fr, prog, ip, count, local=None, kind='M98'):
        depth = sum(1 for f in self.frames if f.get('ret') is not None)
        if depth >= self.p['sub_nesting']:
            self.flag('error', kind, 'Вложенность подпрограмм больше %d уровней — станок выдаст аварию.' % self.p['sub_nesting'])
            raise Stop()
        if count <= 0:
            return
        self.frames.append(dict(prog=prog, ip=ip, start=ip, locals=local, ret=fr, loops={}, count=count, kind=kind))

    def exec_words(self, block, fr, vals, gs, ms, raw):
        st, p, prog = self.st, self.p, fr['prog']
        machine = self.machine
        if 65 in gs:
            return self.macro_call(fr, vals)
        # --- коды, которых нет у станка
        for g in gs:
            if g not in G_CODES[machine]:
                other = 'imv' if machine == 'haas' else 'haas'
                hint = ' (это код %s)' % ('HAAS' if other == 'haas' else 'HNC-8') if g in G_CODES[other] else ''
                self.flag('error', 'G%g' % g, 'G%g нет в списке G-кодов %s%s — станок выдаст аварию «неверный G-код».' %
                          (g, 'HAAS' if machine == 'haas' else 'HNC-8', hint))
        for m in ms:
            if m not in M_CODES[machine]:
                if machine == 'imv':
                    self.flag('warning', 'M%d' % m, 'M%d не входит в стандартные M-коды HNC-8 — задаётся станкостроителем (PLC). '
                              'Убедитесь, что на IMV он есть.' % m, certain=False)
                else:
                    self.flag('error', 'M%d' % m, 'M%d нет в списке M-кодов HAAS — станок выдаст аварию.' % m)
        if 'T' in vals:
            st['next_T'] = int(vals['T'])
        if 'S' in vals:
            st['S'] = vals['S']
            if st['spindle']:
                self.spindle_on(st['spindle'])
        if 'F' in vals:
            st['F'] = vals['F'] * (25.4 if st['inch'] else 1.0)
        # --- модальные G
        cycle_g = None
        nonmodal = None
        for g in gs:
            gi = int(g)
            if g in (0, 1, 2, 3):
                st['motion'] = gi
                st['cycle'] = None
            elif gi in (17, 18, 19):
                st['plane'] = gi
            elif gi == 90:
                st['absolute'] = True
            elif gi == 91:
                st['absolute'] = False
            elif gi in (93, 94, 95):
                st['feed_mode'] = gi
            elif gi == 20:
                st['inch'] = True
            elif gi == 21:
                st['inch'] = False
            elif gi in (98, 99):
                st['ret'] = gi
            elif gi == 80:
                st['cycle'] = None
            elif gi in CYCLES:
                cycle_g = gi
            elif gi in (40, 41, 42):
                if gi != 40 and 'D' not in vals and st['D'] in (None, 0):
                    self.flag('error', 'G%d D' % gi, 'G%d без номера корректора D — станок выдаст аварию или не применит коррекцию.' % gi)
                st['comp_new'] = gi != 40 and st['comp'] == 40
                st['comp'] = gi
            elif gi in (43, 44):
                st['lencomp'] = True
                st['need_g43'] = False
                h = int(vals.get('H', st['H'] or 0))
                st['H'] = h
                if h == 0:
                    self.flag('error', 'G43 H', 'G43 без H (или H0) — коррекция на длину не применится.')
                elif st['T'] is not None and h != st['T']:
                    self.flag('warning', 'G43 H', 'G43 H%d при инструменте T%s — номер корректора не совпадает с инструментом '
                              '(скопированный блок?).' % (h, st['T']))
                if self.tool_row is not None:
                    self.tool_row['H'].add(h)
            elif gi == 49:
                st['lencomp'] = False
            elif g in (54, 55, 56, 57, 58, 59, 54.1) or gi == 154 or 110 <= gi <= 129:
                st['wcs'] = ('G%g' % g) + (' P%d' % vals['P'] if 'P' in vals and g in (54.1, 154) else '')
                if g == 54.1 and 'P' in vals and not 1 <= vals['P'] <= 60:
                    self.flag('error', 'G54.1', 'G54.1 P%d вне диапазона P1–P60 HNC-8.' % vals['P'])
                if gi == 154 and 'P' in vals and not 1 <= vals['P'] <= 99:
                    self.flag('error', 'G154', 'G154 P%d вне диапазона P1–P99.' % vals['P'])
            elif gi == 68:
                if machine == 'haas':
                    cx, cy = vals.get('A', self.prog['X']), vals.get('B', self.prog['Y'])
                else:
                    cx, cy = vals.get('X', self.prog['X']), vals.get('Y', self.prog['Y'])
                st['rot'] = (cx, cy, math.radians(vals.get('R', 0.0)))
                nonmodal = 'G68'
            elif gi == 69:
                st['rot'] = None
            elif gi == 51:
                k = vals.get('P', 1.0)
                if machine == 'haas' and 'P' in vals and k > 10:
                    k = k / 1000.0
                st['scale'] = (vals.get('X', 0.0), vals.get('Y', 0.0), vals.get('Z', 0.0), k)
                nonmodal = 'G51'
            elif gi == 50:
                st['scale'] = None
            elif gi in (4, 9, 10, 11, 28, 29, 30, 31, 35, 36, 37, 52, 53, 65, 92, 70, 71, 72) or g in POCKETS:
                nonmodal = g
            elif g in (108, 109):
                st['spindle_mode'] = 'position' if g == 108 else 'speed'
                self.add(p['mode_switch_s'] * 1000, 'spindle', 'G%d режим шпинделя' % g)
        # --- M до движения
        for m in ms:
            if m in (3, 4):
                if machine == 'imv' and st['spindle_mode'] == 'position':
                    st['spindle_mode'] = 'speed'
                self.spindle_on(m)
            elif m == 6:
                if len([w for w in vals if w not in ('T',)]) or any(g for g in gs):
                    if machine == 'imv':
                        self.flag('warning', 'M6', 'HNC-8: M06 нужно писать отдельным кадром (можно с T).', certain=False)
                self.tool_change(block)
            elif m == 19:
                self.add(p['orient_s'] * 1000, 'spindle', 'M19 ориентация')
            elif m in (8, 88, 7):
                st['coolant'] = True
        if any(m in (98, 97, 99) for m in ms) and machine == 'imv':
            extra = [w for w in vals if w not in ('P', 'L')] + ['G%g' % g for g in gs] + ['M%d' % m for m in ms if m not in (98, 99)]
            if extra:
                self.flag('warning', 'M98/M99', 'HNC-8: M98/M99 должны стоять отдельным кадром (в кадре ещё %s).' % ', '.join(extra))
        # --- непрерывные (нормальные) команды
        if nonmodal == 4:
            self.dwell(vals, raw)
        elif nonmodal in (28, 30):
            self.home(vals, nonmodal)
        elif nonmodal == 53:
            mach = dict(self.mach)
            for a in AXES:
                if a in vals:
                    mach[a] = vals[a]
            self.check_travel(mach, certain=True)
            self.rapid_to(mach, 'G53')
            self.prog = self.work_of_mach()
        elif nonmodal == 52:
            for a in ('X', 'Y', 'Z'):
                if a in vals:
                    st['g52'][a] = vals[a]
            self.prog = self.work_of_mach()
        elif nonmodal == 92:
            for a in AXES:
                if a in vals:
                    st['g52'][a] = st['g52'].get(a, 0.0) + self.prog[a] - vals[a]
            self.prog = self.work_of_mach()
        elif nonmodal in (70, 71, 72) and machine == 'haas':
            self.bolt_pattern(int(nonmodal), vals)
        elif nonmodal in (12, 13) and machine == 'haas':
            self.circ_pocket(vals)
        elif nonmodal in POCKETS:
            self.flag('warning', 'G%g' % nonmodal, 'Цикл G%g не моделируется — его время в расчёт не вошло.' % nonmodal)
            self.incomplete = True
        elif nonmodal == 65:
            return self.macro_call(fr, vals)
        elif nonmodal in (31, 35, 36, 37):
            self.flag('warning', 'G%g' % nonmodal, 'Измерительный цикл G%g — время измерения учтено приблизительно.' % nonmodal,
                      certain=False)
            self.add(3000, 'aux', 'измерение')
        # --- циклы
        axes_given = {a: vals[a] for a in AXES if a in vals}
        if cycle_g is not None:
            if st['cycle'] is None:
                st['init_z'] = self.prog['Z']
            st['cycle'] = cycle_g
            st['cyc'] = dict(st['cyc']) if st['cyc'] else {}
            if not st['cyc'] or st['cyc'].get('g') != cycle_g:
                st['cyc'].pop('Q', None)
                st['cyc'].pop('I', None)
                st['cyc'].pop('J', None)
            st['cyc']['g'] = cycle_g
        if st['cycle'] is not None and nonmodal not in (28, 30, 53, 52, 92, 4) and (cycle_g is not None or axes_given or
                                                                                   any(k in vals for k in ('R', 'Q', 'P', 'F'))):
            cyc = st['cyc']
            cyc['abs'] = st['absolute']
            for k in ('R', 'Z', 'Q', 'I', 'J', 'K'):
                if k in vals:
                    cyc[k] = vals[k]
            if 'P' in vals:
                cyc['P'] = (vals['P'], raw.get('P', ''))
            if 'F' in vals:
                cyc['F'] = vals['F']
            mode = p['cycle_mode'] if machine == 'imv' else 'haas'
            reps = 1
            if 'L' in vals:
                reps = int(vals['L'])
            elif mode == 'fanuc' and 'K' in vals:
                reps = int(vals['K'])
            if mode == 'fanuc':
                cyc.pop('K', None)
            if (cycle_g is not None or axes_given) and reps != 1 and st['absolute'] and reps > 1:
                self.flag('warning', 'G%d повтор' % st['cycle'], 'Повтор %s%d в абсолютных координатах (G90): одно и то же '
                          'отверстие будет обработано %d раза.' % ('K' if 'K' in vals and 'L' not in vals else 'L', reps, reps))
            hole_axes = {a: v for a, v in axes_given.items() if a != 'Z'}
            if cycle_g is not None or hole_axes or 'Z' in axes_given:
                for k in range(reps):
                    xy = {}
                    for a in ('X', 'Y', 'A'):
                        if a in hole_axes:
                            xy[a] = hole_axes[a] if st['absolute'] else self.prog[a] + hole_axes[a]
                    self.cycle_hole(st['cycle'], vals, xy)
        elif axes_given and nonmodal not in (28, 30, 53, 52, 92, 4, 10, 11, 65, 51, 68) and nonmodal not in POCKETS:
            tgt = self.target(axes_given)
            if st['motion'] == 0:
                mach = self.to_mach(tgt)
                self.check_travel(mach)
                self.rapid_to(mach)
                self.prog = tgt
                self.note_span(tgt)
                if st['comp'] != 40 and st.get('comp_new'):
                    st['comp_new'] = False
            elif st['motion'] == 1:
                self.check_travel(self.to_mach(tgt))
                if st.get('comp_new'):
                    st['comp_new'] = False
                self.feed_to(tgt)
            else:
                self.arc_to(tgt, st['motion'] == 2, vals, 'G%d' % st['motion'])
                st['comp_new'] = False
        elif st['motion'] in (2, 3) and any(k in vals for k in ('I', 'J', 'K')) and not axes_given and st['cycle'] is None:
            self.arc_to(dict(self.prog), st['motion'] == 2, vals, 'G%d окружность' % st['motion'])
        if 'D' in vals:
            st['D'] = int(vals['D'])
            if self.tool_row is not None:
                self.tool_row['D'].add(st['D'])
        # --- M после движения
        for m in ms:
            if m == 5:
                st['spindle'] = 0
                st['S_running'] = 0.0
            elif m == 9:
                st['coolant'] = False
            elif m == 0 or (m == 1 and p['optional_stop']):
                self.stops.append(block['line'])
                self.flag('warning', 'M%02d' % m, 'M%02d — остановка программы: станок ждёт оператора (время ожидания не '
                          'учтено).' % m, certain=False)
            if m in (0, 1, 2, 3, 4, 5, 6, 19, 30, 97, 98, 99):
                continue
            self.add(p['m_times'].get(str(m), p['m_default_s']) * 1000, 'aux', 'M%d' % m)
        # --- подпрограммы и конец
        for m in ms:
            if m == 98:
                return self.sub_call(fr, vals, raw)
            if m == 97:
                return self.local_call(fr, vals)
            if m == 99:
                return self.sub_return(fr, vals)
            if m in (30, 2):
                if len(self.frames) > 1:
                    self.flag('error', 'M%d' % m, 'M%d внутри подпрограммы — программа закончится раньше времени.' % m)
                if st['comp'] != 40:
                    self.flag('warning', 'G40', 'Программа закончилась при включённой коррекции на радиус G41/G42.')
                return 'end'
        return None

    def dwell(self, vals, raw):
        machine = self.machine
        if 'X' in vals:
            sec = vals['X']
        elif 'P' in vals:
            text = raw.get('P', '')
            if machine == 'haas':
                sec = vals['P'] if '.' in text else vals['P'] / 1000.0
            else:
                sec = int(vals['P']) / 1000.0
                if '.' in text:
                    self.flag('warning', 'G04 P', 'HNC-8: в G04 P задаётся в миллисекундах, дробная часть отбрасывается — '
                              '«G04 P%s» = пауза %d мс. Если нужна пауза %s с, пишите G04 X%s.' % (text, int(vals['P']), text.rstrip('.'), text.rstrip('.')))
        else:
            sec = 0.0
        if 'P' in vals and '.' not in raw.get('P', '.') and 0 < vals['P'] < 10:
            self.flag('warning', 'G04 P', 'G04 P%s — пауза %d мс. Если нужна пауза в секундах, пишите %s.' % (
                raw['P'], vals['P'], 'P%s.' % raw['P'] if machine == 'haas' else 'X%s' % raw['P']), certain=False)
        self.st['last_dir'] = None
        self.add(sec * 1000, 'dwell', 'пауза %.3f с' % sec)

    def home(self, vals, g):
        inter = dict(self.prog)
        for a in AXES:
            if a in vals:
                inter[a] = (self.prog[a] + vals[a]) if not self.st['absolute'] else vals[a]
        mach_i = self.to_mach(inter)
        self.rapid_to(mach_i, 'G%d промежуточная' % g)
        home = dict(self.mach)
        for a in AXES:
            if a in vals:
                home[a] = 0.0
        self.rapid_to(home, 'G%d в нуль станка' % g)
        self.prog = self.work_of_mach()

    def bolt_pattern(self, g, vals):
        st = self.st
        if st['cycle'] is None:
            self.flag('error', 'G%d' % g, 'G%d без активного стандартного цикла.' % g)
            return
        cx, cy = self.prog['X'], self.prog['Y']
        i = vals.get('I', 0.0)
        j = vals.get('J', 0.0)
        n = int(vals.get('L', 1))
        pts = []
        if g == 70:
            pts = [(cx + i * math.cos(math.radians(j + 360.0 * k / n)), cy + i * math.sin(math.radians(j + 360.0 * k / n))) for k in range(n)]
        elif g == 71:
            kk = vals.get('K', 0.0)
            pts = [(cx + i * math.cos(math.radians(j + kk * k)), cy + i * math.sin(math.radians(j + kk * k))) for k in range(n)]
        else:
            pts = [(cx + i * (k + 1) * math.cos(math.radians(j)), cy + i * (k + 1) * math.sin(math.radians(j))) for k in range(n)]
        for x, y in pts:
            self.cycle_hole(st['cycle'], vals, {'X': x, 'Y': y})

    def circ_pocket(self, vals):
        i = abs(vals.get('I', 0.0))
        k = abs(vals.get('K', i))
        q = abs(vals.get('Q', 0.0)) or max(i, 1.0)
        z = abs(vals.get('Z', 0.0))
        passes = max(1, int(vals.get('L', 1)))
        r, length = i, 0.0
        while r <= k + 1e-9:
            length += 2 * math.pi * r + q
            r += q
            if q <= 0:
                break
        self.check_cut()
        f = self.feed_rate()
        ms = length * passes / f * 60000 if f > 0 else 0.0
        self.add(ms, 'cut', 'G12/G13 карман, путь %.0f мм × %d' % (length, passes))

    def macro_call(self, fr, vals):
        no = _num_key(str(int(vals.get('P', 0))))
        prog, foreign = find_program(self.registry, no, fr['prog']['file'])
        if prog is None:
            self.flag('error', 'G65', 'G65 P%s: программа O%s не найдена среди загруженных файлов.' % (no, no))
            return None
        local = {ARG_VARS[k]: v for k, v in vals.items() if k in ARG_VARS}
        self.call(fr, prog, 0, int(vals.get('L', 1)), local=local, kind='G65')
        return None

    def sub_call(self, fr, vals, raw):
        if 'P' not in vals:
            self.flag('error', 'M98', 'M98 без номера подпрограммы P.')
            return None
        no = _num_key(str(int(vals['P'])))
        count = int(vals.get('L', 1))
        prog, foreign = find_program(self.registry, no, fr['prog']['file'])
        if foreign:
            self.flag('warning', 'M98', 'M98 P%s: подпрограмма O%s найдена только внутри файла %s. Станок ищет её в текущем '
                      'файле и среди программ в памяти — загрузите её отдельным файлом или вставьте в этот.' % (no, no, prog['file']))
        if prog is None:
            hint = ''
            if self.machine == 'haas' and no in fr['prog']['labels']:
                hint = ' В этой программе есть метка N%s — вероятно, нужен M97 P%s (локальная подпрограмма).' % (no, no)
            self.flag('error', 'M98', 'M98 P%s: программа O%s не найдена среди загруженных файлов — станок выдаст аварию '
                      '«программа не найдена».%s' % (no, no, hint))
            return None
        self.call(fr, prog, 0, count)
        return None

    def local_call(self, fr, vals):
        if self.machine != 'haas':
            self.flag('error', 'M97', 'M97 (локальная подпрограмма) — код HAAS; на HNC-8 его нет. Используйте M98 P… '
                      'с подпрограммой O… в том же файле.')
            return None
        no = _num_key(str(int(vals.get('P', 0))))
        prog = fr['prog']
        if no not in prog['labels']:
            self.flag('error', 'M97', 'M97 P%s: метки N%s нет в программе O%s — станок выдаст аварию.' % (no, no, prog['no']))
            return None
        self.call(fr, prog, prog['labels'][no], int(vals.get('L', 1)), kind='M97')
        return None

    def sub_return(self, fr, vals):
        if fr.get('ret') is None:
            self.flag('warning', 'M99', 'M99 в основной программе — станок начнёт её заново (бесконечный цикл). '
                      'Расчёт остановлен на этом кадре.')
            return 'end'
        if self.machine == 'imv' and self.st['cycle'] is not None:
            self.flag('warning', 'G80', 'HNC-8: перед M99 подпрограммы нужен G80 (активен цикл G%d).' % self.st['cycle'])
        fr['count'] -= 1
        if fr['count'] > 0:
            fr['ip'] = fr['start']
            fr['loops'] = {}
            return None
        self.frames.pop()
        if 'P' in vals:
            caller = self.frames[-1]
            key = _num_key(str(int(vals['P'])))
            if key in caller['prog']['labels']:
                caller['ip'] = caller['prog']['labels'][key]
            else:
                self.flag('error', 'M99 P', 'M99 P%s: метки N%s нет в вызывающей программе.' % (key, key))
        return None


# ---------------------------------------------------------------- статика

def dead_code(prog, executed):
    """Кадры основной программы после M30, до которых нет перехода (нет метки N перед ними)."""
    out = []
    after = False
    for b in prog['blocks']:
        if after:
            if b['label'] is not None:
                break
            if (prog['file'], prog['no'], b['line']) not in executed:
                out.append(b)
            continue
        if _has_m(b, {30.0, 2.0}) and not b['skip']:
            after = True
    return out


def static_checks(prog, machine):
    out = []
    if prog['head_line'] is None:
        out.append(issue('warning', 'O', 'В файле нет строки с номером программы O… — станок присвоит номер сам '
                         'или не загрузит файл.', prog['file'], prog['no'], prog['blocks'][0]['line'] if prog['blocks'] else None,
                         certain=False))
    stem = re.sub(r'\D', '', prog['file'].rsplit('.', 1)[0])
    if prog['kind'] == 'main' and stem and prog['head_line'] is not None and stem.isdigit() and _num_key(stem) != prog['no']:
        out.append(issue('warning', 'O', 'Имя файла %s, а внутри — O%s. На станке программа будет под номером O%s.' %
                         (prog['file'], prog['no'], prog['no']), prog['file'], prog['no'], prog['head_line'], certain=False))
    return out


# ---------------------------------------------------------------- расчёт

def group_issues(issues):
    """Одинаковые замечания в одном файле — одной строкой со списком строк."""
    out, seen = [], {}
    for i in issues:
        key = (i['severity'], i['code'], i['message'], i['file'])
        if key in seen and i['line']:
            seen[key]['more'].append(i['line'])
            continue
        i = dict(i, more=[])
        seen[key] = i
        out.append(i)
    for i in out:
        if i['more']:
            lines = sorted(set(i['more']) - {i['line']})
            if lines:
                i['message'] += ' Ещё в строках: %s%s.' % (', '.join(map(str, lines[:15])), ' …' if len(lines) > 15 else '')
    return out


def summarize(sim, prog):
    tools = []
    for row in sim.tools:
        tools.append(dict(T=row['T'], name=row['name'], file=row['file'], line=row['line'], H=sorted(row['H']),
                          D=sorted(row['D']), S=sorted(row['S']), F=sorted(row['F']), ms=row['ms'], cut_ms=row['cut_ms'],
                          holes=row['holes']))
    return tools


def analyze(files, params):
    """files: [(имя, текст)]. Возвращает dict(setups=[...], subs=[...], issues=[...])."""
    machine = params['machine']
    programs, registry, notes = load_files(files, machine)
    mains = [p for p in programs if p['kind'] == 'main' and p['blocks']]
    called = set()
    setups = []
    for prog in mains:
        sim = MillSim(params, registry, prog).run()
        alt_ms = None
        used = {(f, n) for f, n, _ in sim.executed} | {(prog['file'], prog['no'])}
        if any(b['skip'] for p in programs if (p['file'], p['no']) in used or p['file'] == prog['file'] for b in p['blocks']):
            other = dict(params, block_skip=not params['block_skip'])
            alt_ms = MillSim(other, registry, prog).run().t
        for key in sim.executed:
            called.add((key[0], key[1]))
        issues = static_checks(prog, machine) + sim.issues + [i for i in notes if i['file'] == prog['file']]
        seen_low = set()
        for seg in sim.path:
            if seg['kind'] != 'rapid':
                continue
            (x0, y0, z0), (x1, y1, z1) = seg['pts'][0], seg['pts'][-1]
            if max(z0, z1) < -0.5 and math.hypot(x1 - x0, y1 - y0) > 1.0 and (seg['file'], seg['line']) not in seen_low:
                seen_low.add((seg['file'], seg['line']))
                issues.append(issue('warning', 'G0 ниже Z0', 'Ускоренное перемещение по XY на Z%.2f - ниже верха детали (Z0). '
                                    'Если здесь не выбранный карман/паз - инструмент врежется в деталь.' % max(z0, z1),
                                    seg['file'], prog['no'], seg['line'], certain=False))
        dead = dead_code(prog, sim.executed)
        if dead:
            first, last = dead[0], dead[-1]
            issues.append(issue('warning', 'После M30', 'Кадры после M30 не выполняются: строки %d–%d (%d кадров), '
                                'первый — «%s». Если это нужный переход/подпрограмма, оформите её как O… или N… с вызовом.' %
                                (first['line'], last['line'], len(dead), first['raw'].strip()[:60]),
                                prog['file'], prog['no'], first['line']))
        issues = group_issues(issues)
        issues.sort(key=lambda i: (i['severity'] != 'error', not i['certain'], i['file'] or '', i['line'] or 0))
        setups.append(dict(no=prog['no'], title=prog['title'], file=prog['file'], ms=sim.t, cat=dict(sim.cat),
                           tools=summarize(sim, prog), blocks=sim.blocks, issues=issues, alt_ms=alt_ms,
                           block_skip=params['block_skip'], incomplete=sim.incomplete, stops=sim.stops,
                           span={a: tuple(v) for a, v in sim.span.items() if v[0] <= v[1]}, path=sim.path))
    subs = []
    for p in programs:
        if p['kind'] == 'sub':
            used = (p['file'], p['no']) in called
            subs.append(dict(no=p['no'], file=p['file'], title=p['title'], used=used, lines=len(p['blocks']),
                             own=any(m['file'] == p['file'] for m in mains)))
            notes.extend(static_checks(p, machine))
    for p in programs:
        if p['kind'] == 'sub' and (p['file'], p['no']) not in called and not any(m['file'] == p['file'] for m in mains):
            notes.append(issue('warning', 'O' + p['no'], 'Подпрограмма O%s (%s) не вызывается ни одной из загруженных программ.' %
                               (p['no'], p['file']), p['file'], p['no'], p['head_line'], certain=False))
    return dict(setups=setups, subs=subs, issues=notes, programs=programs, registry=registry,
                total_ms=sum(s['ms'] for s in setups))


def merge_params(base, saved):
    out = copy.deepcopy(base)
    for k, v in (saved or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        elif k in out:
            out[k] = v
    return out
