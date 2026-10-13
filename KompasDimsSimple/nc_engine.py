"""Время цикла и проверка УП для Diamond CSB II/III (Mitsubishi, L-система).

Перенос на Python движка вкладки «Проверка» из DiamondCAM/Post (включая
исправления 1.7.0). Логика и числа совпадают с JS-версией один в один —
сверено на реальных программах O6017/O6018 (см. test_nc_engine.py).
Время — в миллисекундах.
"""
import copy
import math
import re

INF = float('inf')


# ---------------------------------------------------------------- помощники JS

def js_parse_int(value):
    """parseInt(value, 10): ведущие цифры со знаком, иначе None (NaN)."""
    m = re.match(r'\s*([+-]?\d+)', str(value))
    return int(m.group(1)) if m else None


def js_key(value):
    """String(parseInt(value, 10)) — ключ метки/подпрограммы."""
    n = js_parse_int(value)
    return 'NaN' if n is None else str(n)


def js_round(x):
    return math.floor(x + 0.5)


def js_num(x):
    """Число в тексте сообщения так, как его выводит JS."""
    if isinstance(x, float):
        if math.isnan(x):
            return 'NaN'
        if math.isinf(x):
            return 'Infinity' if x > 0 else '-Infinity'
        if x == int(x) and abs(x) < 1e21:
            return str(int(x))
        return repr(x)
    return str(x)


def js_div(a, b):
    if b == 0:
        if a == 0 or math.isnan(a):
            return math.nan
        return math.copysign(INF, a) * (1 if math.copysign(1, b) > 0 else -1)
    return a / b


def fixed(x, n):
    return ('%.' + str(n) + 'f') % x


# ---------------------------------------------------------------- разбор УП

def strip_comment(line):
    line = re.sub(r'\([^)]*\)', ' ', line)
    # незакрытая "(" — комментарий до конца строки
    i = line.find('(')
    if i >= 0:
        line = line[:i]
    i = line.find(';')
    if i >= 0:
        line = line[:i]
    return line.strip()


def tokenize_line(line):
    tokens = []
    n = len(line)
    pos = [0]

    def ch(k):
        return line[k] if 0 <= k < n else ''

    def read_balanced(open_c, close_c):
        depth = 0
        start = pos[0]
        while True:
            c = ch(pos[0])
            if c == open_c:
                depth += 1
            elif c == close_c:
                depth -= 1
            pos[0] += 1
            if not (depth > 0 and pos[0] <= n):
                break
        return line[start + 1:pos[0] - 1]

    def read_value_token():
        while ch(pos[0]) == ' ':
            pos[0] += 1
        sign = ''
        if ch(pos[0]) in ('-', '+') and ch(pos[0]):
            sign = ch(pos[0])
            pos[0] += 1
        c = ch(pos[0])
        if c == '#':
            s = pos[0]
            pos[0] += 1
            while pos[0] < n and line[pos[0]].isdigit():
                pos[0] += 1
            return sign + line[s:pos[0]]
        if c == '[':
            s = pos[0]
            read_balanced('[', ']')
            return sign + line[s:pos[0]]
        if c and (c.isdigit() or c == '.'):
            s = pos[0]
            while pos[0] < n and (line[pos[0]].isdigit() or line[pos[0]] == '.'):
                pos[0] += 1
            return sign + line[s:pos[0]]
        if c and re.match(r'[A-Za-z]', c):
            s = pos[0]
            pos[0] += 1
            while pos[0] < n and line[pos[0]].isdigit():
                pos[0] += 1
            return sign + line[s:pos[0]]
        pos[0] += 1
        return sign

    while pos[0] < n:
        c = line[pos[0]]
        if c in (' ', '\t'):
            pos[0] += 1
            continue
        if c == '!':
            pos[0] += 1
            s = pos[0]
            while pos[0] < n and re.match(r'[A-Za-z0-9]', line[pos[0]]):
                pos[0] += 1
            tokens.append(dict(type='sync', label=line[s:pos[0]].upper()))
            continue
        if c == '/':
            pos[0] += 1
            continue
        # ",C1." / ",R2." — фаска/скругление угла, не ось C
        if c == ',' and re.match(r'[A-Za-z]', ch(pos[0] + 1)):
            pos[0] += 1
            letter = line[pos[0]].upper()
            pos[0] += 1
            tokens.append(dict(type='corner', letter=letter, valueExpr=read_value_token()))
            continue
        if c == '#':
            pos[0] += 1
            s = pos[0]
            while pos[0] < n and line[pos[0]].isdigit():
                pos[0] += 1
            var = line[s:pos[0]]
            while ch(pos[0]) == ' ':
                pos[0] += 1
            if ch(pos[0]) == '=':
                pos[0] += 1
                tokens.append(dict(type='assign', varNum=var, expr=line[pos[0]:].strip()))
                pos[0] = n
            continue
        if re.match(r'[A-Za-z]', c):
            s = pos[0]
            pos[0] += 1
            while pos[0] < n and re.match(r'[A-Za-z]', line[pos[0]]):
                pos[0] += 1
            word = line[s:pos[0]].upper()
            if word == 'WHILE':
                while ch(pos[0]) == ' ':
                    pos[0] += 1
                cond = read_value_token()
                while ch(pos[0]) == ' ':
                    pos[0] += 1
                if line[pos[0]:pos[0] + 2].upper() == 'DO':
                    pos[0] += 2
                    ds = pos[0]
                    while pos[0] < n and line[pos[0]].isdigit():
                        pos[0] += 1
                    tokens.append(dict(type='while', cond=cond, doNum=line[ds:pos[0]]))
                continue
            if word == 'END':
                es = pos[0]
                while pos[0] < n and line[pos[0]].isdigit():
                    pos[0] += 1
                tokens.append(dict(type='end', endNum=line[es:pos[0]]))
                continue
            if word == 'GOTO':
                gs = pos[0]
                while pos[0] < n and line[pos[0]].isdigit():
                    pos[0] += 1
                tokens.append(dict(type='goto', target=line[gs:pos[0]]))
                continue
            if word == 'IF':
                while ch(pos[0]) == ' ':
                    pos[0] += 1
                tokens.append(dict(type='if', cond=read_value_token()))
                continue
            if word == 'THEN':
                tokens.append(dict(type='then'))
                continue
            pos[0] = s + 1
            letter = word[0]
            j = pos[0]
            if ch(j) in ('-', '+') and ch(j):
                j += 1
            num_start = j
            while j < n and line[j].isdigit():
                j += 1
            after = j
            while ch(after) == ' ':
                after += 1
            if j > num_start and ch(after) == '=':
                index = line[num_start:j]
                pos[0] = after + 1
                tokens.append(dict(type='indexed', letter=letter, index=index, expr=read_value_token()))
            else:
                tokens.append(dict(type='word', letter=letter, valueExpr=read_value_token()))
            continue
        pos[0] += 1
    return tokens


def parse_program(text):
    stmts = []
    for idx, raw in enumerate(re.split(r'\r?\n', text or '')):
        # 0x1A (Ctrl+Z) — конец файла у DNC/станка, не кадр
        clean = strip_comment(raw.replace('\x1a', ''))
        if not clean or clean == '%':
            continue
        label = None
        rest = clean
        m = re.match(r'^N(\d+)\s*(.*)$', rest, re.I | re.S)
        if m:
            label, rest = m.group(1), m.group(2)
        stmts.append(dict(lineNo=idx + 1, raw=raw, nLabel=label, tokens=tokenize_line(rest) if rest else []))
    return stmts


# ---------------------------------------------------------------- выражения

def eval_expr(expr, variables):
    if expr is None or expr == '':
        return 0
    expr = str(expr)
    if re.match(r'^-?\d+\.?\d*$', expr):
        return float(expr)
    js = expr.replace('[', '(').replace(']', ')')
    for a, b in (('LE', '<='), ('GE', '>='), ('LT', '<'), ('GT', '>'), ('EQ', '=='), ('NE', '!=')):
        js = re.sub(a, b, js, flags=re.I)
    tokens = []
    i, n = 0, len(js)
    while i < n:
        c = js[i]
        if c == ' ':
            i += 1
            continue
        if c in '()+-*/':
            tokens.append(c)
            i += 1
            continue
        if c in '<>=!':
            if i + 1 < n and js[i + 1] == '=':
                tokens.append(c + '=')
                i += 2
            else:
                tokens.append(c)
                i += 1
            continue
        if c == '#':
            s = i + 1
            i += 1
            while i < n and js[i].isdigit():
                i += 1
            tokens.append(('v', js[s:i]))
            continue
        if c.isdigit() or c == '.':
            s = i
            while i < n and (js[i].isdigit() or js[i] == '.'):
                i += 1
            tokens.append(('num', _parse_float(js[s:i])))
            continue
        i += 1
    p = [0]

    def peek():
        return tokens[p[0]] if p[0] < len(tokens) else None

    def take():
        t = peek()
        p[0] += 1
        return t

    def primary():
        t = peek()
        if t == '(':
            take()
            v = comp()
            if peek() == ')':
                take()
            return v
        if t == '-':
            take()
            return -primary()
        if t == '+':
            take()
            return primary()
        if isinstance(t, tuple) and t[0] == 'num':
            take()
            return t[1]
        if isinstance(t, tuple) and t[0] == 'v':
            take()
            v = variables.get(t[1])
            return v if v is not None else 0
        if t is not None:
            take()
        return 0

    def mul():
        v = primary()
        while peek() in ('*', '/'):
            op = take()
            r = primary()
            v = v * r if op == '*' else js_div(v, r)
        return v

    def add():
        v = mul()
        while peek() in ('+', '-'):
            op = take()
            r = mul()
            v = v + r if op == '+' else v - r
        return v

    def comp():
        v = add()
        t = peek()
        if t in ('<=', '>=', '<', '>', '==', '!='):
            take()
            r = add()
            return {'<=': v <= r, '>=': v >= r, '<': v < r, '>': v > r, '==': v == r, '!=': v != r}[t] and 1 or 0
        return v

    try:
        return comp()
    except Exception:
        return 0


def _parse_float(s):
    m = re.match(r'\d*\.?\d*', s)
    try:
        return float(m.group(0)) if m.group(0) not in ('', '.') else math.nan
    except ValueError:
        return math.nan


def js_parse_float(s):
    m = re.match(r'\s*([+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?)', str(s))
    return float(m.group(1)) if m else math.nan


def truthy(v):
    return bool(v) and not (isinstance(v, float) and math.isnan(v))


# ---------------------------------------------------------------- модель движения

def move_time_ms(dist, vmax_per_min, accel_ms):
    dist = abs(dist)
    if dist <= 1e-9 or not (vmax_per_min > 0):
        return 0
    v = vmax_per_min / 60000
    if accel_ms <= 0:
        return dist / v
    d_ramp = v * accel_ms
    if dist >= d_ramp:
        return 2 * accel_ms + (dist - d_ramp) / v
    a = v / accel_ms
    return 2 * math.sqrt(dist / a)


def find_loop_pairs(stmts):
    pairs, stack = {}, []
    for idx, s in enumerate(stmts):
        for tok in s['tokens']:
            if tok['type'] == 'while':
                stack.append(dict(idx=idx, doNum=tok['doNum']))
            if tok['type'] == 'end':
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k]['doNum'] == tok['endNum']:
                        pairs[stack[k]['idx']] = idx
                        pairs[idx] = stack[k]['idx']
                        del stack[k]
                        break
    return pairs


def loop_vars_changed(stmts, frm, to, cond):
    used = {v[1:] for v in re.findall(r'#\d+', str(cond))}
    if not used:
        return False
    for k in range(frm, to + 1):
        for t in stmts[k]['tokens']:
            if t['type'] == 'assign' and t['varNum'] in used:
                return True
    return False


def default_params():
    return dict(
        diameter_programming=True,
        axes=dict(
            X=dict(rapid_rate_mm_min=30000, feed_clamp_mm_min=6000, g0_accel_ms=90, g1_accel_ms=60, home_pos=0),
            Z=dict(rapid_rate_mm_min=30000, feed_clamp_mm_min=8000, g0_accel_ms=100, g1_accel_ms=70, home_pos=0),
            Y=dict(rapid_rate_mm_min=30000, feed_clamp_mm_min=5000, g0_accel_ms=90, g1_accel_ms=60, home_pos=0),
            C=dict(rapid_rate_deg_min=60000, feed_clamp_deg_min=20000, g0_accel_ms=120, g1_accel_ms=100, home_pos=0),
        ),
        spindles={
            '1': dict(max_rpm=8000, s_code_exec_time_ms=200, accel_time_to_max_ms=2000),
            '2': dict(max_rpm=8000, s_code_exec_time_ms=200, accel_time_to_max_ms=2000),
            '3': dict(max_rpm=8000, s_code_exec_time_ms=200, accel_time_to_max_ms=1500),
        },
        spindle_start_m_codes=[3, 4, 13, 14, 103, 104, 113, 114],
        spindle_stop_m_codes=[5, 105, 205],
        model_spindle_ramp=True,
        m_codes=dict(default_exec_time_ms=150, overrides={}),
        t_code_exec_time_ms=350,
        tool_travel_model=dict(enabled=True, position_spacing_mm=42, index_axis='Y'),
        special_g_ms={'114.1': 300, '125': 50, '113': 100},
        aux_code_timing_model='overlap',
        rapid_override_pct=50,
        canned_cycle=dict(g83_retract_mode='by_d', g83_return_amount_mm=1, peck_retract_clearance_mm=1,
                          chip_break_retract_mm=1),
    )


def is_spindle_start(params, m_code):
    return m_code in (params.get('spindle_start_m_codes') or [3, 4, 13, 14, 103, 104, 113, 114])


def g_key(g):
    """Ключ special_g_ms как String(g) в JS: 114.1 -> '114.1', 125 -> '125'."""
    return js_num(float(g))


def accel_of(cfg, name, default):
    v = cfg.get(name)
    return v if v is not None else default


class Simulator:
    def __init__(self, params, sys_cfg, name):
        self.params = params
        self.sys_cfg = sys_cfg
        self.name = name
        self.vars = {}
        self.pos = {ax: 0 for ax in params['axes']}
        self.absolute = True
        self.motion = 0
        self.plane = 18
        self.feed_per_rev = True
        self.css = False
        self.feed = 0
        self.spindle_cmd = {}
        self.spindle_clamp = {}
        self.cutting_ms = 0
        self.spindle_actual = {}
        self.last_aux_spindle = None
        self.active_spindle = sys_cfg.get('mainSpindle')
        self.block_log = []
        self.events = []
        self.seg_ms = 0
        self.tail_ms = 0
        self.section_totals = {}
        self.current_section = '(начало)'
        self.warnings = []
        self.stopped = False
        self.subprograms = sys_cfg.get('subprograms') or {}
        self.current_tool_raw = None
        self.last_real_tool = None
        self.tool_cut_ms = {}
        self.tool_total_ms = {}
        self._seg_index = 0
        self._pending_g71 = None
        self._pending_g73 = None
        self._pending_g76 = None
        self._zero_feed_warned = False
        self.last_thread_passes = None
        self.incomplete = False

    # --- оси и шпиндели
    def axis_cfg(self, letter):
        return self.params['axes'].get(letter)

    @staticmethod
    def resolve_axis_alias(letter):
        return {'U': 'X', 'W': 'Z', 'V': 'Y'}.get(letter, letter)

    def phys_dist(self, axis, val):
        if axis == 'X' and self.params.get('diameter_programming'):
            return val / 2
        return val

    def spindle_max_rpm(self, k):
        if self.spindle_clamp.get(k):
            return self.spindle_clamp[k]
        s = self.params['spindles'].get(k)
        return s['max_rpm'] if s else 8000

    def eff_rapid(self, rate):
        raw = self.params.get('rapid_override_pct')
        pct = 100 if raw is None else max(0, min(100, raw))
        return rate * pct / 100

    def spindle_ramp_ms(self, spindle_id, target_rpm):
        if self.params.get('model_spindle_ramp') is False:
            return 0
        cfg = (self.params.get('spindles') or {}).get(spindle_id) or {}
        accel = cfg.get('accel_time_to_max_ms') if cfg.get('accel_time_to_max_ms') is not None else 2000
        max_rpm = self.spindle_max_rpm(spindle_id) or 1
        frm = self.spindle_actual.get(spindle_id) or 0
        to = max(0, target_rpm or 0)
        self.spindle_actual[spindle_id] = to
        return abs(to - frm) / max_rpm * accel

    def current_rpm(self, at_diameter=None):
        k = self.active_spindle
        cmd = abs(self.spindle_cmd.get(k) or 0)
        if not self.css:
            return min(cmd, self.spindle_max_rpm(k))
        d = abs(at_diameter if at_diameter is not None else (self.pos.get('X') or 0))
        if d < 1e-6:
            return self.spindle_max_rpm(k)
        rpm = (cmd * 1000) / (math.pi * d)
        return max(0, min(rpm, self.spindle_max_rpm(k)))

    def add_time(self, ms):
        self.seg_ms += ms
        self.section_totals[self.current_section] = self.section_totals.get(self.current_section, 0) + ms

    def add_cut(self, ms):
        self.cutting_ms += ms
        if self.current_tool_raw is not None:
            self.tool_cut_ms[self.current_tool_raw] = self.tool_cut_ms.get(self.current_tool_raw, 0) + ms

    def log_block(self, stmt, ms, note):
        self.block_log.append(dict(lineNo=stmt['lineNo'], raw=stmt['raw'], ms=ms, note=note or '', segIndex=self._seg_index))
        if self.current_tool_raw is not None:
            self.tool_total_ms[self.current_tool_raw] = self.tool_total_ms.get(self.current_tool_raw, 0) + ms

    def m_code_time(self, m):
        ov = self.params['m_codes']['overrides'].get(str(m))
        return ov if ov is not None else self.params['m_codes']['default_exec_time_ms']

    @staticmethod
    def tool_position_index(t_raw):
        if t_raw is None:
            return None
        n = js_parse_int(str(t_raw).rjust(4, '0')[:2])
        if n is None or n < 1 or n > 19:
            return None
        return n

    def t_code_time(self, t_value, prev_real):
        n = js_parse_int(t_value)
        if not n:
            return 0
        base = self.params['t_code_exec_time_ms']
        tm = self.params.get('tool_travel_model')
        if not tm or not tm.get('enabled') or prev_real is None:
            return base

        def back_post(raw):
            p = self.tool_position_index(raw)
            return p is not None and p <= 4 and self.active_spindle is not None and str(self.active_spindle) != '1'
        new, prev = self.tool_position_index(t_value), self.tool_position_index(prev_real)
        if new is None or prev is None or back_post(t_value) or back_post(prev_real):
            return base
        if new == prev:
            return base
        dist = abs(new - prev) * (tm.get('position_spacing_mm') or 42)
        cfg = self.axis_cfg(tm.get('index_axis') or 'Y') or {}
        rate = self.eff_rapid(cfg.get('rapid_rate_mm_min') or 30000)
        return base + js_div(dist, rate) * 60000

    # --- постоянные циклы
    def canned_drill(self, tokens, gcode, line_no):
        depth_axis = next((ax for ax in ('Z', 'X', 'Y') if any(t.get('letter') == ax and t['type'] != 'indexed' for t in tokens)), None)
        if not depth_axis:
            self.warnings.append('Каноничный цикл G%s без адреса глубины' % js_num(gcode))
            return 0

        def get(letter):
            t = next((tt for tt in tokens if tt.get('letter') == letter), None)
            return eval_expr(t.get('expr') or t.get('valueExpr'), self.vars) if t else None
        depth_val = get(depth_axis)
        r_val = get('R') or 0
        q_val = get('Q')
        f_val = get('F')
        dwell = get('P') or 0
        feed_value = f_val if f_val is not None else self.feed
        rpm = self.current_rpm()
        feed_per_min = feed_value * rpm if self.feed_per_rev else feed_value
        total = self.phys_dist(depth_axis, abs(depth_val - r_val))
        cfg = self.axis_cfg(depth_axis) or {}
        rapid = cfg.get('rapid_rate_mm_min') or cfg.get('rapid_rate_deg_min') or 15000
        accel = accel_of(cfg, 'g0_accel_ms', 100)
        feed_safe = max(feed_per_min, 1e-6)
        cc = self.params.get('canned_cycle') or {}
        clearance = cc['peck_retract_clearance_mm'] if cc.get('peck_retract_clearance_mm') is not None else 1
        chip_break = cc['chip_break_retract_mm'] if cc.get('chip_break_retract_mm') is not None else 1
        t = [0.0]
        cut = [0.0]
        dwell_handled = False

        def feed_in(mm):
            v = (mm / feed_safe) * 60 * 1000
            t[0] += v
            cut[0] += v
        if gcode in (84, 84.1, 74.1, 88):
            thread = max(feed_value * rpm, 1e-6)
            v = (total / thread) * 60 * 1000 * 2
            t[0] += v
            cut[0] += v
        elif gcode in (83, 87):
            if truthy(q_val):
                if (cc.get('g83_retract_mode') or 'by_d') == 'by_d':
                    d = cc['g83_return_amount_mm'] if cc.get('g83_return_amount_mm') is not None else 1
                    remaining = total
                    while remaining > 1e-6:
                        step = min(abs(q_val), remaining)
                        feed_in(step)
                        remaining -= step
                        if remaining > 1e-6:
                            t[0] += move_time_ms(d, self.eff_rapid(rapid), accel) * 2
                else:
                    remaining, prev_bottom, first = total, 0, True
                    while remaining > 1e-6:
                        step = min(abs(q_val), remaining)
                        if first:
                            feed_in(step)
                            first = False
                        else:
                            t[0] += move_time_ms(max(0, prev_bottom - clearance), self.eff_rapid(rapid), accel)
                            feed_in(clearance + step)
                        prev_bottom += step
                        remaining -= step
                        if remaining > 1e-6:
                            t[0] += move_time_ms(prev_bottom, self.eff_rapid(rapid), accel)
            else:
                feed_in(total)
        elif gcode == 83.1:
            if truthy(q_val):
                remaining = total
                while remaining > 1e-6:
                    step = min(abs(q_val), remaining)
                    feed_in(step)
                    remaining -= step
                    if remaining > 1e-6:
                        t[0] += move_time_ms(chip_break, self.eff_rapid(rapid), accel) * 2
            else:
                feed_in(total)
        elif gcode in (85, 89):
            feed_in(total)
            t[0] += dwell
            dwell_handled = True
            feed_in(total)
        else:
            feed_in(total)
            t[0] += dwell
            dwell_handled = True
            t[0] += move_time_ms(total, self.eff_rapid(rapid), accel)
        if not dwell_handled:
            t[0] += dwell
        if gcode in (83, 87, 83.1):
            t[0] += move_time_ms(total, self.eff_rapid(rapid), accel)
        self.add_cut(cut[0])
        self.pos[depth_axis] = r_val
        return t[0]

    def _contour(self, stmts, start, end):
        length = 0
        last_x, last_z = self.pos.get('X'), self.pos.get('Z')
        min_x = min_z = INF
        max_x = max_z = -INF
        for idx in range(start, end + 1):
            dx = dz = 0
            moved = False
            for tok in stmts[idx]['tokens']:
                if tok['type'] != 'word':
                    continue
                if tok['letter'] == 'X':
                    v = eval_expr(tok['valueExpr'], self.vars)
                    dx, last_x, moved = v - last_x, v, True
                if tok['letter'] == 'Z':
                    v = eval_expr(tok['valueExpr'], self.vars)
                    dz, last_z, moved = v - last_z, v, True
            if moved:
                length += math.hypot(self.phys_dist('X', dx), dz)
            min_x, max_x = min(min_x, last_x), max(max_x, last_x)
            min_z, max_z = min(min_z, last_z), max(max_z, last_z)
        return length, last_x, last_z, min_x, max_x, min_z, max_z

    def roughing_cycle(self, stmts, labels, P, Q, U, F, depth, facing):
        start, end = labels.get(js_key(P)), labels.get(js_key(Q))
        g_label = 'G72' if facing else 'G71'
        if start is None or end is None:
            self.warnings.append('%s: не найден профиль N%s..N%s' % (g_label, P, Q))
            return dict(timeMs=0, jumpTo=None, passes=0, contourLen=0, gLabel=g_label)
        stock_x, stock_z = self.pos.get('X'), self.pos.get('Z')
        length, last_x, last_z, min_x, max_x, min_z, max_z = self._contour(stmts, start, end)
        step = max(depth or 1, 0.05)
        U = U or 0
        if facing:
            down = max(0, (stock_z - min_z) - U)
            up = max(0, (max_z - stock_z) - U)
            stock = max(down, up)
            rpm_ref = (stock_x + max_x) / 2
        else:
            down = max(0, (stock_x - min_x) / 2 - U / 2)
            up = max(0, (max_x - stock_x) / 2 - U / 2)
            stock = max(down, up)
            ref_x = max_x if up >= down else min_x
            rpm_ref = (stock_x + ref_x) / 2 if math.isfinite(ref_x) else None
        passes = max(1, math.ceil(stock / step))
        rpm = self.current_rpm(rpm_ref)
        rough_feed = max((F or 0.2) * rpm, 1)
        t = passes * (length / rough_feed * 60 * 1000)
        self.add_cut(t)
        if facing:
            self.warnings.append('%s: приближённый расчёт по Z (депту среза вдоль торца) - в отличие от G71, не сверен на реальном примере пользователя, проверьте время этого цикла отдельно' % g_label)
        self.pos['X'], self.pos['Z'] = last_x, last_z
        return dict(timeMs=t, jumpTo=end + 1, passes=passes, contourLen=length, gLabel=g_label, start=start)

    def pattern_repeat_cycle(self, stmts, labels, P, Q, F, repeats):
        start, end = labels.get(js_key(P)), labels.get(js_key(Q))
        if start is None or end is None:
            self.warnings.append('G73: не найден профиль N%s..N%s' % (P, Q))
            return dict(timeMs=0, jumpTo=None, passes=0, contourLen=0)
        length, last_x, last_z = self._contour(stmts, start, end)[:3]
        passes = max(1, js_round(repeats or 1))
        rough_feed = max((F or 0.2) * self.current_rpm(), 1)
        t = passes * (length / rough_feed * 60 * 1000)
        self.add_cut(t)
        self.pos['X'], self.pos['Z'] = last_x, last_z
        return dict(timeMs=t, jumpTo=end + 1, passes=passes, contourLen=length, start=start)

    @staticmethod
    def thread_passes(k, first_cut, m, dmin, finish):
        """Черновые: глубина n-го = Δd·√n (не меньше Δdmin), до k-d; плюс m чистовых."""
        k = abs(k or 0)
        first = abs(first_cut or 0) or k
        rough = max(k - abs(finish or 0), 0)
        depth, n = 0, 0
        while depth < rough - 1e-9 and n < 1000:
            n += 1
            depth = min(max(first * math.sqrt(n), depth + abs(dmin or 0)), rough)
        return max(1, n + max(1, js_round(m or 1)))

    def threading_cycle(self, X, Z, P, Q, F):
        start_z, start_x = self.pos.get('Z'), self.pos.get('X')
        length = abs(Z - start_z)
        rpm = self.current_rpm()
        if rpm <= 0:
            self.warnings.append('G76: обороты шпинделя не заданы - время резьбы не может быть посчитано')
        feed = max(F * rpm, 1)
        pend = self._pending_g76 or {}
        self._pending_g76 = None
        passes = self.thread_passes(P, Q, pend.get('m'), pend.get('dmin'), pend.get('finish'))
        cfg = self.axis_cfg('Z') or {}
        rapid = cfg.get('rapid_rate_mm_min') or 24000
        accel = accel_of(cfg, 'g0_accel_ms', 100)
        xcfg = self.axis_cfg('X') or {}
        x_move = move_time_ms(self.phys_dist('X', abs((start_x or 0) - X)), self.eff_rapid(xcfg.get('rapid_rate_mm_min') or rapid),
                              accel_of(xcfg, 'g0_accel_ms', 100))
        t = 0
        for _ in range(passes):
            cut = (length / feed) * 60 * 1000
            t += cut
            self.add_cut(cut)
            t += move_time_ms(length, self.eff_rapid(rapid), accel) + 2 * x_move
        self.last_thread_passes = passes
        self.pos['Z'], self.pos['X'] = Z, X
        return t

    # --- интерпретатор
    @staticmethod
    def make_ctx(text, name):
        stmts = parse_program(text)
        labels = {}
        for idx, s in enumerate(stmts):
            if s['nLabel'] is not None:
                labels.setdefault(js_key(s['nLabel']), idx)
        return dict(stmts=stmts, labels=labels, pairs=find_loop_pairs(stmts), name=name)

    def run(self, program_text):
        ctx = self.make_ctx(program_text, 'MAIN')
        stack = []
        ip = 0
        guard = 0
        while not self.stopped:
            guard += 1
            if guard > 300000:
                self.warnings.append('Превышен лимит шагов интерпретатора (возможен бесконечный цикл) - время НЕ достоверно.')
                self.incomplete = True
                break
            stmts, labels, pairs = ctx['stmts'], ctx['labels'], ctx['pairs']
            if ip >= len(stmts):
                if stack:
                    ctx, ip = self._return(stack, ctx)
                    continue
                break
            stmt = stmts[ip]
            if stmt['nLabel'] is not None:
                self.current_section = 'N' + stmt['nLabel']
            jump = None
            move_ms = 0
            code_ms = 0
            notes = []
            toks = stmt['tokens']
            if_tok = next((t for t in toks if t['type'] == 'if'), None)
            if if_tok and any(t['type'] == 'then' for t in toks) and not truthy(eval_expr(if_tok['cond'], self.vars)):
                ip += 1
                continue
            for tok in toks:
                typ = tok['type']
                if typ == 'assign':
                    self.vars[tok['varNum']] = eval_expr(tok['expr'], self.vars)
                elif typ == 'while':
                    if not truthy(eval_expr(tok['cond'], self.vars)):
                        if pairs.get(ip) is None:
                            self.warnings.append('WHILE DO%s: нет парного END%s (стр. %d) - цикл пропущен' % (tok['doNum'], tok['doNum'], stmt['lineNo']))
                            self.stopped = True
                        else:
                            jump = pairs[ip] + 1
                elif typ == 'end':
                    jump = pairs.get(ip)
                elif typ == 'if':
                    cond = eval_expr(tok['cond'], self.vars)
                    goto = next((t for t in toks if t['type'] == 'goto'), None)
                    if goto and truthy(cond):
                        tgt = labels.get(js_key(goto['target']))
                        if tgt is None:
                            jump = ip + 1
                            self.warnings.append('IF/GOTO%s: метка не найдена (стр. %d)' % (goto['target'], stmt['lineNo']))
                        elif tgt <= ip and loop_vars_changed(stmts, tgt, ip, if_tok['cond']):
                            jump = tgt
                        elif tgt <= ip:
                            self.warnings.append('IF/GOTO%s: переход назад (стр. %d) - программа пройдена один раз, повтор на следующую деталь не моделируется' % (goto['target'], stmt['lineNo']))
                            self.stopped = True
                        else:
                            jump = tgt
                elif typ == 'goto':
                    if not any(t['type'] == 'if' for t in toks):
                        tgt = labels.get(js_key(tok['target']))
                        if tgt is None:
                            jump = ip + 1
                            self.warnings.append('GOTO%s: метка не найдена (стр. %d) - переход проигнорирован' % (tok['target'], stmt['lineNo']))
                        elif tgt <= ip:
                            self.warnings.append('GOTO%s: переход назад (стр. %d) - программа пройдена один раз, повтор на следующую деталь не моделируется' % (tok['target'], stmt['lineNo']))
                            self.stopped = True
                        else:
                            jump = tgt
                elif typ == 'sync':
                    self.events.append(dict(label=tok['label'], segMs=self.seg_ms))
                    self.seg_ms = 0
                    self._seg_index += 1
                    notes.append('СИНХРО ' + tok['label'])
            if jump is not None:
                ip = jump
                continue

            words = [t for t in toks if t['type'] == 'word']
            indexed = [t for t in toks if t['type'] == 'indexed']

            def word(letter):
                return next((w for w in words if w['letter'] == letter), None)

            def wval(letter, default=None):
                w = word(letter)
                return eval_expr(w['valueExpr'], self.vars) if w else default
            g_words = [eval_expr(w['valueExpr'], self.vars) for w in words if w['letter'] == 'G']
            m_words = [js_round(eval_expr(w['valueExpr'], self.vars)) for w in words if w['letter'] == 'M']
            has_g50 = 50 in g_words
            for g in g_words:
                if g in (0, 1, 2, 3):
                    self.motion = g
                elif g == 90:
                    self.absolute = True
                    self.warnings.append('G90 (стр. %d): на этом станке G90 в перечне G-кодов - цикл продольной обработки, а не режим координат; модель трактует его как абсолютный режим (обычно безвредно), но ЕСЛИ это вызов цикла - время посчитано неверно, сообщите разработчику' % stmt['lineNo'])
                elif g == 91:
                    self.absolute = False
                    self.warnings.append('G91 (стр. %d): в перечне G-кодов этого станка такого кода нет вовсе (относительные координаты задаются адресами U/W/V) - проверьте, не опечатка ли это' % stmt['lineNo'])
                elif g in (94, 98):
                    self.feed_per_rev = False
                elif g in (95, 99):
                    self.feed_per_rev = True
                elif g == 96:
                    self.css = True
                elif g == 97:
                    self.css = False
                elif g in (17, 18, 19):
                    self.plane = int(g)
            for it in indexed:
                if it['letter'] == 'S':
                    val = eval_expr(it['expr'], self.vars)
                    if has_g50:
                        self.spindle_clamp[it['index']] = val
                        notes.append('G50 S%s=%s' % (it['index'], js_num(val)))
                    else:
                        self.spindle_cmd[it['index']] = val
                        notes.append('S%s=%s' % (it['index'], js_num(val)))
            plain_s = word('S')
            if plain_s and not any(t['letter'] == 'S' for t in indexed):
                val = eval_expr(plain_s['valueExpr'], self.vars)
                if has_g50:
                    self.spindle_clamp[self.active_spindle] = val
                else:
                    self.spindle_cmd[self.active_spindle] = val
                notes.append('%sS=%s' % ('G50 ' if has_g50 else '', js_num(val)))
            started = next((t for t in indexed if t['letter'] == 'S' and any(is_spindle_start(self.params, m) for m in m_words)), None)
            if started and not has_g50:
                self.active_spindle = started['index']
            start_code = next((m for m in m_words if is_spindle_start(self.params, m)), None)
            if start_code is not None:
                sp = started['index'] if started else self.active_spindle
                if start_code >= 100:
                    self.last_aux_spindle = sp
                prev = self.active_spindle
                self.active_spindle = sp
                target = self.current_rpm()
                self.active_spindle = prev
                if started and not has_g50:
                    self.active_spindle = sp
                ramp = self.spindle_ramp_ms(sp, target)
                if ramp > 0:
                    code_ms += ramp
                    notes.append('разгон шп.%s до %d об/мин = %d мс' % (sp, js_round(target), js_round(ramp)))
            stop_codes = self.params.get('spindle_stop_m_codes') or [5, 105, 205]
            stop_code = next((m for m in m_words if m in stop_codes), None)
            if stop_code is not None:
                sp = self.last_aux_spindle if (stop_code >= 100 and self.last_aux_spindle is not None) else self.active_spindle
                ramp = self.spindle_ramp_ms(sp, 0)
                if ramp > 0:
                    code_ms += ramp
                    notes.append('торможение шп.%s = %d мс' % (sp, js_round(ramp)))
            f_word = word('F')
            if f_word:
                self.feed = eval_expr(f_word['valueExpr'], self.vars)

            if 4 in g_words:
                dw = next((w for w in words if w['letter'] in ('X', 'U', 'P')), None)
                dw_ms = 0
                if dw:
                    v = eval_expr(dw['valueExpr'], self.vars)
                    dw_ms = v if dw['letter'] == 'P' else v * 1000
                self.add_time(dw_ms)
                self.log_block(stmt, dw_ms, 'G04 выдержка %sс' % fixed(dw_ms / 1000, 2))
                ip += 1
                continue

            g71 = next((g for g in g_words if g in (71, 72)), None)
            g8x = next((g for g in g_words if g in (74.1, 81, 82, 83, 83.1, 84, 84.1, 85, 86, 87, 88, 89)), None)
            if g71 is not None:
                facing = g71 == 72
                if word('P'):
                    res = self.roughing_cycle(stmts, labels, word('P')['valueExpr'], word('Q')['valueExpr'] if word('Q') else None,
                                              wval('U'), wval('F', 0.2) if f_word else 0.2,
                                              (self._pending_g71 or {}).get('depth') or 1.4, facing)
                    move_ms += res['timeMs']
                    notes.append('%s черновой цикл: %d прох. x %sмм' % (res['gLabel'], res['passes'], fixed(res['contourLen'], 2)))
                    self._pending_g71 = None
                    if res['jumpTo'] is not None:
                        self.add_time(move_ms + code_ms)
                        self.log_block(stmt, move_ms + code_ms, '; '.join(notes))
                        # профиль выше кадра цикла: продолжаем со следующего кадра,
                        # а не «за профилем» (раньше это был бесконечный повтор)
                        ip = res['jumpTo'] if res['jumpTo'] > ip else ip + 1
                        continue
                else:
                    self._pending_g71 = dict(depth=wval('W' if facing else 'U'))
                    notes.append('G72 (параметры глубины реза)' if facing else 'G71 (параметры глубины реза)')
            elif 73 in g_words:
                if word('P'):
                    pend = self._pending_g73 or {}
                    res = self.pattern_repeat_cycle(stmts, labels, word('P')['valueExpr'], word('Q')['valueExpr'] if word('Q') else None,
                                                    wval('F', 0.2) if f_word else 0.2, pend.get('repeats') or 1)
                    move_ms += res['timeMs']
                    notes.append('G73 повтор образца: %d прох. x %sмм' % (res['passes'], fixed(res['contourLen'], 2)))
                    self._pending_g73 = None
                    if res['jumpTo'] is not None:
                        self.add_time(move_ms + code_ms)
                        self.log_block(stmt, move_ms + code_ms, '; '.join(notes))
                        # профиль выше кадра цикла: продолжаем со следующего кадра,
                        # а не «за профилем» (раньше это был бесконечный повтор)
                        ip = res['jumpTo'] if res['jumpTo'] > ip else ip + 1
                        continue
                else:
                    self._pending_g73 = dict(repeats=wval('R', 1))
                    notes.append('G73 (параметры повтора)')
            elif 76 in g_words:
                if word('X') or word('Z'):
                    x = wval('X', self.pos.get('X'))
                    z = wval('Z', self.pos.get('Z'))
                    before = self.pos.get('Z')
                    move_ms += self.threading_cycle(x, z, wval('P', 1), wval('Q'), wval('F', 1) if f_word else 1)
                    notes.append('G76 резьба: длина %sмм, проходов %d' % (fixed(abs(z - before), 2), self.last_thread_passes))
                else:
                    p_raw = js_round(wval('P')) if word('P') else 10000
                    self._pending_g76 = dict(m=math.floor(p_raw / 10000) or 1, dmin=wval('Q', 0), finish=wval('R', 0))
                    notes.append('G76 (параметры: чистовых %d)' % self._pending_g76['m'])
            elif g8x is not None:
                move_ms += self.canned_drill(words, g8x, stmt['lineNo'])
                notes.append('G%s цикл сверления/нарезания' % js_num(g8x))
            elif 28 in g_words:
                touched, unknown = [], False
                for w in words:
                    if w['letter'] in ('G', 'M', 'T'):
                        continue
                    al = self.resolve_axis_alias(w['letter'])
                    if al in self.params['axes']:
                        if al not in touched:
                            touched.append(al)
                    else:
                        unknown = True
                axes = touched if touched else ([] if unknown else list(self.pos))
                mx = 0
                for ax in axes:
                    cfg = self.axis_cfg(ax)
                    if not cfg:
                        continue
                    home = cfg.get('home_pos') or 0
                    rr = cfg.get('rapid_rate_mm_min') or cfg.get('rapid_rate_deg_min') or 0
                    mx = max(mx, move_time_ms(abs(self.phys_dist(ax, home - self.pos[ax])), self.eff_rapid(rr), accel_of(cfg, 'g0_accel_ms', 100)))
                    self.pos[ax] = home
                move_ms += mx
                notes.append('G28 в реф. точку (%s)' % ','.join(axes) if axes else 'G28 ориентация шпинделя')
            else:
                deltas = {}
                for w in words:
                    ax = self.resolve_axis_alias(w['letter'])
                    if ax not in self.params['axes']:
                        continue
                    val = eval_expr(w['valueExpr'], self.vars)
                    inc = ax != w['letter']
                    delta = val if inc else ((val - self.pos[ax]) if self.absolute else val)
                    deltas[ax] = deltas.get(ax, 0) + delta
                if deltas:
                    if self.motion == 0:
                        mx = 0
                        for ax, d in deltas.items():
                            cfg = self.axis_cfg(ax)
                            rr = cfg.get('rapid_rate_mm_min') or cfg.get('rapid_rate_deg_min') or 0
                            mx = max(mx, move_time_ms(self.phys_dist(ax, d), self.eff_rapid(rr), accel_of(cfg, 'g0_accel_ms', 100)))
                        move_ms += mx
                        notes.append('G00 %sмс' % fixed(mx, 1))
                    elif self.motion in (1, 2, 3):
                        if self.motion == 1:
                            length = math.hypot(self.phys_dist('X', deltas.get('X', 0)), deltas.get('Z', 0), deltas.get('Y', 0))
                            if not length:
                                length = max([abs(v) for v in deltas.values()] + [0])
                        else:
                            length = self.arc_length(words, deltas)
                        clamps = [self.axis_cfg(ax).get('feed_clamp_mm_min') or self.axis_cfg(ax).get('feed_clamp_deg_min') or INF for ax in deltas]
                        accels = [accel_of(self.axis_cfg(ax), 'g1_accel_ms', 60) for ax in deltas]
                        clamp = min(clamps) if clamps else INF
                        accel = max(accels) if accels else 60
                        mid = (self.pos['X'] + (self.pos['X'] + deltas['X'])) / 2 if 'X' in deltas else None
                        rpm = self.current_rpm(mid)
                        feed = self.feed * rpm if self.feed_per_rev else self.feed
                        vmax = min(feed, clamp)
                        if not (vmax > 0) and length > 1e-9 and not self._zero_feed_warned:
                            self._zero_feed_warned = True
                            self.warnings.append('Стр. %d: рабочая подача равна 0 (%s) - время таких перемещений не учтено' % (
                                stmt['lineNo'], 'подача на оборот без оборотов шпинделя' if self.feed_per_rev else 'F не задана'))
                        t = move_time_ms(length, vmax, accel)
                        move_ms += t
                        self.add_cut(t)
                        notes.append('G0%d len=%s feed=%s %sмс' % (int(self.motion), fixed(length, 3), fixed(vmax, 0) if math.isfinite(vmax) else js_num(vmax), fixed(t, 1)))
                    for ax, d in deltas.items():
                        if math.isfinite(d):
                            self.pos[ax] += d

            for m in m_words:
                if m in (98, 99):
                    continue
                tt = self.m_code_time(m)
                code_ms += tt
                if tt:
                    notes.append('M%d=%sмс' % (m, js_num(tt)))
            t_word = word('T')
            if t_word:
                tt = self.t_code_time(t_word['valueExpr'], self.last_real_tool)
                code_ms += tt
                if tt:
                    notes.append('T%s=%dмс' % (t_word['valueExpr'], js_round(tt)))
                self.current_tool_raw = t_word['valueExpr']
                if js_parse_int(t_word['valueExpr']):
                    self.last_real_tool = t_word['valueExpr']
            for g in g_words:
                sp = (self.params.get('special_g_ms') or {}).get(g_key(g))
                if sp:
                    code_ms += sp
                    notes.append('G%s накл.=%sмс' % (js_num(g), js_num(sp)))
            if not math.isfinite(move_ms):
                self.warnings.append('Стр. %d: время перемещения не определено (деление на 0 или пустое выражение в адресе) - кадр не учтён' % stmt['lineNo'])
                move_ms = 0
            overlap = self.params.get('aux_code_timing_model') != 'sequential'
            block_ms = max(move_ms, code_ms) if overlap else move_ms + code_ms
            self.add_time(block_ms)
            self.log_block(stmt, block_ms, '; '.join(notes))

            if 98 in m_words:
                p_tok, l_tok = word('P'), word('L')
                p_raw = str(js_round(eval_expr(p_tok['valueExpr'], self.vars))) if p_tok else None
                repeats = max(1, js_round(eval_expr(l_tok['valueExpr'], self.vars))) if l_tok else 1
                if p_raw and len(p_raw) > 4:
                    repeats = max(1, js_parse_int(p_raw[:-4]) or 1)
                    p_raw = p_raw[-4:]
                sub_no = js_key(p_raw) if p_raw is not None else None
                sub_text = self.subprograms.get(sub_no) if sub_no is not None else None
                if sub_no is None:
                    self.warnings.append('M98 без адреса P (стр. %d): номер подпрограммы не задан' % stmt['lineNo'])
                elif sub_text is None:
                    self.warnings.append('M98 P%s: подпрограмма O%s не загружена - её время НЕ учтено (добавьте файл в карточку «Подпрограммы»)' % (sub_no, sub_no))
                elif len(stack) >= 10:
                    self.warnings.append('M98 P%s: превышена вложенность подпрограмм (>10, см. аварию станка P230) - вызов пропущен' % sub_no)
                else:
                    stack.append(dict(ctx=ctx, returnIp=ip + 1, repeatsLeft=repeats, section=self.current_section))
                    ctx = self.make_ctx(sub_text, 'O' + sub_no)
                    ip = 0
                    continue
            if 99 in m_words and stack:
                ctx, ip = self._return(stack, ctx)
                continue
            if 30 in m_words or 99 in m_words or 2 in m_words:
                self.stopped = True
            ip += 1
        self.tail_ms = self.seg_ms

    def _return(self, stack, ctx):
        fr = stack.pop()
        if fr['repeatsLeft'] > 1:
            fr['repeatsLeft'] -= 1
            stack.append(fr)
            return ctx, 0
        self.current_section = fr['section']
        return fr['ctx'], fr['returnIp']

    def arc_length(self, words, deltas):
        dx = self.phys_dist('X', deltas.get('X', 0))
        dz = deltas.get('Z', 0)
        chord = math.hypot(dx, dz)
        r = next((w for w in words if w['letter'] == 'R'), None)
        if r:
            radius = abs(eval_expr(r['valueExpr'], self.vars))
            if radius <= 0 or chord > 2 * radius:
                return chord
            return radius * 2 * math.asin(min(1, chord / (2 * radius)))
        i_w = next((w for w in words if w['letter'] == 'I'), None)
        k_w = next((w for w in words if w['letter'] == 'K'), None)
        radius = math.hypot(eval_expr(i_w['valueExpr'], self.vars) if i_w else 0, eval_expr(k_w['valueExpr'], self.vars) if k_w else 0)
        if radius <= 1e-9:
            return chord
        c = max(-1, min(1, 1 - (chord * chord) / (2 * radius * radius)))
        return radius * math.acos(c)


def reconcile(sims):
    order, seen = [], set()
    for sim in sims:
        for e in sim.events:
            if e['label'] not in seen:
                seen.add(e['label'])
                order.append(e['label'])
    cursor = [0] * len(sims)
    cumulative = [0] * len(sims)
    warnings, barriers = [], []
    for label in order:
        barrier = 0
        part, arrivals = [], {}
        for si, sim in enumerate(sims):
            if cursor[si] < len(sim.events) and sim.events[cursor[si]]['label'] == label:
                arrival = cumulative[si] + sim.events[cursor[si]]['segMs']
                arrivals[sim.name] = arrival
                barrier = max(barrier, arrival)
                part.append(si)
        if part and len(part) < len(sims):
            warnings.append('Барьер %s: не во всех системах (%s)' % (label, ', '.join(sims[i].name for i in part)))
        waits = {}
        for si in part:
            waits[sims[si].name] = barrier - arrivals[sims[si].name]
            cumulative[si] = barrier
            cursor[si] += 1
        if len(part) > 1:
            barriers.append(dict(label=label, arrivals=arrivals, barrierTime=barrier, waits=waits))
    finish = []
    for si, sim in enumerate(sims):
        extra = sum(e['segMs'] for e in sim.events[cursor[si]:])
        finish.append(cumulative[si] + extra + sim.tail_ms)
    return dict(totalMs=max([0] + finish), finishMs=finish, warnings=warnings, barriers=barriers)


def detect_sub_number(text, file_name=''):
    m = re.search(r'^\s*O\s*(\d{1,4})', text or '', re.I | re.M)
    if m:
        return js_key(m.group(1))
    f = re.search(r'(\d{1,4})', file_name or '')
    return js_key(f.group(1)) if f else None


def calculate(systems, subprograms, params=None):
    """systems: [dict(name, spindle, text)] -> (sims, report)."""
    params = copy.deepcopy(params or default_params())
    sims = []
    for s in systems:
        if not (s.get('text') or '').strip():
            continue
        sim = Simulator(params, dict(mainSpindle=str(s.get('spindle') or '1'), subprograms=dict(subprograms or {})), s.get('name') or 'Система')
        try:
            sim.run(s['text'])
        except Exception as exc:  # отчёт вместо падения, как в JS
            sim.warnings.append('Ошибка выполнения: %s' % exc)
        sims.append(sim)
    return sims, reconcile(sims)


# ---------------------------------------------------------------- проверка кода

KNOWN_G_CODES = {
    0, 1, 2, 3, 2.3, 3.3, 4, 7.1, 9, 10, 11, 12.1, 13.1, 14, 15, 16, 17, 18, 19,
    20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 30.1, 30.2, 30.3, 30.4, 30.5,
    31, 31.1, 31.2, 31.3, 32, 33, 34, 35, 36, 37, 40, 41, 42, 43.1, 44.1, 46, 47.1,
    50, 50.1, 50.2, 50.3, 51.1, 51.2, 52, 53, 54, 55, 56, 57, 58, 59,
    61, 62, 63, 64, 65, 66, 66.1, 67, 68, 69,
    70, 71, 72, 73, 74, 75, 76, 76.1, 76.2, 77, 78, 79,
    80, 81, 82, 83, 83.1, 83.2, 84, 84.1, 84.2, 85, 86, 87, 88, 88.1, 89,
    90, 91, 92, 92.1, 94, 95, 96, 97, 98, 99,
    107, 112, 113, 114.1, 114.2, 115, 116, 117, 125,
}


def build_label_index(stmts):
    labels, dups = {}, {}
    for idx, s in enumerate(stmts):
        if s['nLabel'] is None:
            continue
        key = js_key(s['nLabel'])
        if key not in labels:
            labels[key] = idx
        else:
            dups.setdefault(key, [labels[key]]).append(idx)
    return labels, dups


def _safe(expr):
    try:
        return eval_expr(expr, {})
    except Exception:
        return math.nan


def _gvals(s):
    return [_safe(t['valueExpr']) for t in s['tokens'] if t['type'] == 'word' and t['letter'] == 'G']


def _has(s, letter, kinds=('word',)):
    return any(t['type'] in kinds and t.get('letter') == letter for t in s['tokens'])


def _tok(s, letter):
    return next((t for t in s['tokens'] if t['type'] == 'word' and t['letter'] == letter), None)


def validate_program(text, subprograms=None, is_subprogram=False, max_rpm=None):
    stmts = parse_program(text)
    labels, dups = build_label_index(stmts)
    findings = []

    def add(sev, stmt, code, msg, certain=True):
        findings.append(dict(severity=sev, line=stmt['lineNo'] if stmt else None, nLabel=stmt['nLabel'] if stmt else None,
                             code=code, message=msg, certain=certain is not False))

    for s in stmts:
        if s['nLabel'] is not None:
            n = int(s['nLabel'])
            if n == 0:
                add('error', s, 'P37', 'N0 недопустим: номер кадра должен быть в диапазоне 1-99999999')
            elif n > 99999999:
                add('error', s, 'P37', 'N%s: номер кадра превышает максимум 99999999' % s['nLabel'])
        for t in s['tokens']:
            if t['type'] == 'word' and t['letter'] == 'O':
                v = _safe(t['valueExpr'])
                if v == 0:
                    add('error', s, 'P37', 'O0 недопустим: номер программы должен быть в диапазоне 1-99999999')
                elif v > 99999999:
                    add('error', s, 'P37', 'O%s: номер программы превышает максимум 99999999' % t['valueExpr'])
    for s in stmts:
        uniq = []
        for v in _gvals(s):
            if v in (0, 1, 2, 3) and v not in uniq:
                uniq.append(v)
        if len(uniq) > 1:
            add('error', s, 'CONFLICT-G', 'В одном кадре одновременно указаны несовместимые коды движения: %s (взаимоисключающая группа - действует только последний)' % ', '.join('G0' + js_num(v) for v in uniq))
    for s in stmts:
        mv = [js_round(_safe(t['valueExpr'])) for t in s['tokens'] if t['type'] == 'word' and t['letter'] == 'M']
        if 98 in mv and 99 in mv:
            add('error', s, 'CONFLICT-M', 'В одном кадре одновременно M98 (вызов подпрограммы) и M99 (возврат) - вероятная опечатка')
        for a, b in ((3, 4), (13, 14), (103, 104), (113, 114), (203, 204), (213, 214)):
            if a in mv and b in mv:
                add('error', s, 'CONFLICT-M', 'В одном кадре одновременно M%d и M%d - противоположные направления вращения шпинделя одновременно невозможны' % (a, b))
    for s in stmts:
        for t in s['tokens']:
            if t['type'] == 'word' and t['letter'] == 'F' and _safe(t['valueExpr']) < 0:
                add('error', s, 'NEG-F', 'F%s: отрицательная подача недопустима' % t['valueExpr'])
            if t['type'] in ('word', 'indexed') and t.get('letter') == 'S':
                expr = t['expr'] if t['type'] == 'indexed' else t['valueExpr']
                if _safe(expr) < 0:
                    add('error', s, 'NEG-S', 'S%s: отрицательные обороты недопустимы' % expr)
    for s in stmts:
        if 4 not in _gvals(s):
            continue
        dw = next((t for t in s['tokens'] if t['type'] == 'word' and t['letter'] in ('X', 'U', 'P')), None)
        if not dw:
            continue
        v = _safe(dw['valueExpr'])
        sec = v / 1000 if dw['letter'] == 'P' else v
        if sec < 0:
            add('error', s, 'G04-RANGE', 'G04 %s%s: отрицательная выдержка недопустима' % (dw['letter'], dw['valueExpr']))
        elif sec > 99999.999:
            add('error', s, 'G04-RANGE', 'G04 %s%s: выдержка превышает максимум 99999.999с - похоже на потерянную точку/опечатку' % (dw['letter'], dw['valueExpr']))
    for s in stmts:
        if not any(v in (83, 87, 83.1) for v in _gvals(s)):
            continue
        q = _tok(s, 'Q')
        if q and _safe(q['valueExpr']) <= 0:
            add('error', s, 'PECK-Q', 'Q%s: шаг клевка должен быть положительным (0 или отрицательное значение даёт бесконечное число проходов)' % q['valueExpr'])
    for key, idxs in sorted(dups.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 10 ** 12):
        add('warning', stmts[idxs[0]], 'DUP-N', 'Номер кадра N%s встречается %d раз (строки %s) - GOTO/переход найдёт ПЕРВОЕ вхождение, как на станке; убедитесь, что это то, что задумано' % (
            key, len(idxs), ', '.join(str(stmts[i]['lineNo']) for i in idxs)))
    stack, max_depth = [], 0
    for s in stmts:
        for t in s['tokens']:
            if t['type'] == 'while':
                stack.append((s, t['doNum']))
                max_depth = max(max_depth, len(stack))
            if t['type'] == 'end':
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][1] == t['endNum']:
                        del stack[k]
                        break
                else:
                    add('error', s, 'P294', 'END%s без соответствующего WHILE...DO%s' % (t['endNum'], t['endNum']))
    for s, num in stack:
        add('error', s, 'P294', 'WHILE...DO%s без соответствующего END%s' % (num, num))
    if max_depth > 27:
        add('error', None, 'P293', 'Вложенность WHILE...DO-END достигает %d уровней (по спецификации максимум 27)' % max_depth)
    for s in stmts:
        for t in s['tokens']:
            if t['type'] == 'goto' and js_key(t['target']) not in labels:
                add('error', s, 'P231', 'GOTO%s: такого номера кадра в программе нет' % t['target'])
    if subprograms is not None:
        for s in stmts:
            if not any(t['type'] == 'word' and t['letter'] == 'M' and js_round(_safe(t['valueExpr'])) == 98 for t in s['tokens']):
                continue
            p = _tok(s, 'P')
            if not p:
                continue
            raw = js_num(js_round(_safe(p['valueExpr'])))
            if len(raw) > 4:
                raw = raw[-4:]
            sub_no = js_key(raw)
            if sub_no not in subprograms:
                add('warning', s, 'NO-SUB', 'M98 P%s: подпрограмма O%s не загружена в карточку «Подпрограммы» - её время не будет учтено' % (p['valueExpr'], sub_no))
    m_codes = {js_round(_safe(t['valueExpr'])) for s in stmts for t in s['tokens'] if t['type'] == 'word' and t['letter'] == 'M'}
    backward = any(t['type'] == 'goto' and labels.get(js_key(t['target'])) is not None and labels[js_key(t['target'])] <= idx
                   for idx, s in enumerate(stmts) for t in s['tokens'])
    if is_subprogram:
        if 99 not in m_codes and not backward:
            add('warning', None, 'P36', 'В подпрограмме не найден M99 (возврат) - на станке это ошибка P36 "Program end error"')
    elif not ({30, 2, 99} & m_codes) and not backward:
        add('warning', None, 'P36', 'В программе не найден M02/M30/M99 (конец программы) - на станке это ошибка P36 "Program end error"')
    for s in stmts:
        for t in s['tokens']:
            if t['type'] != 'word' or t['letter'] != 'G':
                continue
            v = _safe(t['valueExpr'])
            if v not in KNOWN_G_CODES:
                add('warning', s, 'G?', 'G%s: код не найден в справочном перечне G-кодов этого станка (список собран по фрагментам PDF и может быть неполон - возможна опечатка, проверьте вручную)' % t['valueExpr'], False)
            elif v in (90, 91):
                add('warning', s, 'G90/91', 'G%s: на этом станке (перечень G-кодов "лист 2") это НЕ режим абс./отн. координат - см. предупреждение при расчёте' % js_num(v), False)
    for s in stmts:
        g8 = next((v for v in _gvals(s) if v in (81, 82, 83, 83.1, 84, 84.1, 85, 86, 87, 88, 89)), None)
        if g8 is None:
            continue
        depth = _has(s, 'Z', ('word', 'indexed')) or _has(s, 'X', ('word', 'indexed'))
        if depth and not _has(s, 'R', ('word', 'indexed')):
            add('warning', s, 'CYCLE-R', 'G%s без адреса R в этом кадре - будет использовано ранее заданное модальное значение, проверьте, что это верно' % js_num(g8), False)
        if g8 in (84, 84.1, 88) and depth and not _has(s, 'S', ('word', 'indexed')):
            add('warning', s, 'TAP-S', 'G%s (нарезание метчиком) без S в этом кадре - если на станке включён параметр #8125 "Check Scode in G84", это вызовет ошибку' % js_num(g8), False)
    zero_div = re.compile(r'/\s*(-?0+(\.0+)?)(?![0-9.])')
    for s in stmts:
        for t in s['tokens']:
            expr = t['expr'] if t['type'] == 'assign' else (t['cond'] if t.get('cond') is not None else t.get('valueExpr'))
            if isinstance(expr, str) and zero_div.search(expr):
                add('warning', s, 'P283', 'Деление на 0 в выражении "%s" (эвристика по тексту выражения - проверьте вручную, могут быть ложные срабатывания)' % expr, False)
    for s in stmts:
        arc = next((v for v in _gvals(s) if v in (2, 3)), None)
        if arc is None:
            continue
        if not _has(s, 'R') and not (_has(s, 'I', ('word', 'indexed')) or _has(s, 'K', ('word', 'indexed'))):
            add('warning', s, 'ARC-R', 'G0%s: дуга без R и без I/K - радиус/центр дуги не определены в этом кадре' % js_num(arc), False)
    comp, comp_stmt = 0, None
    for s in stmts:
        for v in _gvals(s):
            if v in (41, 42):
                comp, comp_stmt = v, s
            elif v == 40:
                comp, comp_stmt = 0, None
    if comp and comp_stmt:
        add('warning', comp_stmt, 'COMP', 'G%s (коррекция на радиус) включена и не отменена G40 до конца программы' % js_num(comp), False)
    if max_rpm:
        for s in stmts:
            for t in s['tokens']:
                if t['type'] in ('word', 'indexed') and t.get('letter') == 'S':
                    expr = t['expr'] if t['type'] == 'indexed' else t['valueExpr']
                    if _safe(expr) > max_rpm:
                        add('warning', s, 'S-RANGE', 'S%s: превышает максимум шпинделя, заданный в параметрах (%s об/мин)' % (expr, js_num(max_rpm)), False)
    for s in stmts:
        for t in s['tokens']:
            if t['type'] == 'word' and t['letter'] == 'T':
                raw = str(t['valueExpr']).strip()
                if re.fullmatch(r'\d+', raw) and len(raw) == 3:
                    add('warning', s, 'T-FMT', 'T%s: нетипичное число цифр (обычно 1-2 или 4) - проверьте, не опечатка ли' % raw, False)
    for s in stmts:
        th = next((v for v in _gvals(s) if v in (32, 34)), None)
        if th is not None and not _has(s, 'F'):
            add('warning', s, 'THREAD-F', 'G%s: нарезание резьбы без адреса F (шаг резьбы) в этом кадре' % js_num(th), False)
    for s in stmts:
        g = next((v for v in _gvals(s) if v in (70, 71, 72, 73)), None)
        if g is None:
            continue
        p, q = _tok(s, 'P'), _tok(s, 'Q')
        if not p or not q:
            continue
        pi, qi = labels.get(js_key(p['valueExpr'])), labels.get(js_key(q['valueExpr']))
        if pi is None:
            add('error', s, 'CYCLE-PQ', 'G%s P%s: начало профиля N%s не найдено в программе' % (js_num(g), p['valueExpr'], p['valueExpr']))
            continue
        if qi is None:
            add('error', s, 'CYCLE-PQ', 'G%s Q%s: конец профиля N%s не найден в программе' % (js_num(g), q['valueExpr'], q['valueExpr']))
            continue
        if qi <= pi:
            add('error', s, 'CYCLE-PQ-ORDER', 'G%s P%s Q%s: конец профиля (Q) стоит раньше начала (P) или совпадает с ним - контур цикла пуст, время посчитано неверно' % (js_num(g), p['valueExpr'], q['valueExpr']))
            continue
        for idx in range(pi, qi + 1):
            inner = stmts[idx]
            if inner is s:
                continue
            nested = next((v for v in _gvals(inner) if v in (70, 71, 72, 73, 76)), None)
            if nested is not None:
                add('error', inner, 'CYCLE-NESTED', 'G%s внутри профиля G%s P%sQ%s - вложенный канонический цикл недопустим' % (js_num(nested), js_num(g), p['valueExpr'], q['valueExpr']))
                break
    for idx, s in enumerate(stmts):
        g = next((v for v in _gvals(s) if v in (71, 72)), None)
        if g is None or not (_has(s, 'P') and _has(s, 'Q')):
            continue
        found = False
        for k in range(idx - 1, max(-1, idx - 6), -1):
            prev = stmts[k]
            if g in _gvals(prev) and _has(prev, 'U') and not _has(prev, 'P'):
                found = True
                break
        if not found:
            add('warning', s, 'CYCLE-DEPTH', 'G%s P.. Q..: не найден предыдущий кадр "G%s U.. R.." с глубиной реза за проход в пределах 5 кадров - возможно, глубина берётся из параметра станка, проверьте вручную' % (js_num(g), js_num(g)), False)
    for s in stmts:
        g = next((v for v in _gvals(s) if v in (74, 75)), None)
        if g is None:
            continue
        letter = 'Q' if g == 74 else 'P'
        st = _tok(s, letter)
        if st and _safe(st['valueExpr']) <= 0:
            add('warning', s, 'CYCLE-STEP', 'G%s %s%s: шаг должен быть положительным (0 или отрицательное значение бессмысленно для цикла с ломкой стружки)' % (js_num(g), letter, st['valueExpr']), False)
    return stmts, labels, findings


def find_dead_code(stmts, labels):
    targets = {0}
    for s in stmts:
        for t in s['tokens']:
            if t['type'] == 'goto' and labels.get(js_key(t['target'])) is not None:
                targets.add(labels[js_key(t['target'])])
    dead, reachable = [], True
    for idx, s in enumerate(stmts):
        if idx in targets:
            reachable = True
        if not reachable:
            dead.append(idx)
        has_if = any(t['type'] == 'if' for t in s['tokens'])
        real_goto = any(t['type'] == 'goto' and js_key(t['target']) in labels for t in s['tokens'])
        stop = any(t['type'] == 'word' and t['letter'] == 'M' and js_round(_safe(t['valueExpr'])) in (30, 2, 99) for t in s['tokens'])
        if (real_goto and not has_if) or stop:
            reachable = False
    return dead


def _tool_station(t_raw):
    digits = re.sub(r'\D', '', str(t_raw))[:4] or '0'
    n = int(digits)
    if 101 <= n <= 404:
        return 'резец верхнего суппорта (T0101-T0606) - в диапазоне T0101-T0404', True
    if 405 <= n <= 606:
        return 'резец верхнего суппорта (T0101-T0606)', False
    if 707 <= n <= 1212:
        return 'приводной инструмент сверху (T0707-T1212)', False
    if 1313 <= n <= 1919:
        return 'инструмент на кронштейне (T1313-T1919)', False
    return None


def full_program_check(files, subprograms=None, max_rpm=None):
    """files: [dict(name, text, kind='system'|'subprogram', spindle)]."""
    subprograms = subprograms or {}
    per_file = []
    for f in files:
        stmts, labels, findings = validate_program(f['text'], subprograms, f.get('kind') == 'subprogram', max_rpm)
        dead = find_dead_code(stmts, labels)
        if dead:
            lines = [stmts[i]['lineNo'] for i in dead]
            findings.append(dict(severity='warning', line=lines[0], nLabel=None, code='DEAD', certain=False,
                                 message='Похоже на недостижимый код (%d кадр(ов), строки %s%s) - эвристика, может быть неточной' % (
                                     len(dead), ', '.join(map(str, lines[:6])), '…' if len(lines) > 6 else '')))
        per_file.append(dict(file=f, stmts=stmts, labels=labels, findings=findings))
    cross = []
    systems = [p for p in per_file if p['file'].get('kind') == 'system']
    if len(systems) > 1:
        sets = [{t['label'] for s in p['stmts'] for t in s['tokens'] if t['type'] == 'sync'} for p in systems]
        all_labels = []
        for p in systems:
            for s in p['stmts']:
                for t in s['tokens']:
                    if t['type'] == 'sync' and t['label'] not in all_labels:
                        all_labels.append(t['label'])
        for lbl in all_labels:
            present = [p for p, st in zip(systems, sets) if lbl in st]
            if present and len(present) < len(systems):
                if lbl in ('L1', 'L2', 'L3', 'L4', 'L5', 'L6') and len(present) == 1 and 'G114.1' in (present[0]['file']['text'] or ''):
                    continue
                cross.append(dict(severity='error', file=None, code='SYNC', certain=True,
                                  message='Метка !%s встречается только в: %s - в остальных системах её нет: реальная рассинхронизация барьера' % (
                                      lbl, ', '.join(p['file']['name'] for p in present))))

    def calls_of(stmts):
        out = []
        for s in stmts:
            if not any(t['type'] == 'word' and t['letter'] == 'M' and js_round(_safe(t['valueExpr'])) == 98 for t in s['tokens']):
                continue
            p = _tok(s, 'P')
            if not p:
                continue
            raw = js_num(js_round(_safe(p['valueExpr'])))
            if len(raw) > 4:
                raw = raw[-4:]
            out.append(js_key(raw))
        return out
    sub_calls = {no: calls_of(parse_program(txt)) for no, txt in subprograms.items()}
    called = set()

    def depth_from(no, seen):
        if no in seen:
            return 0, True
        seen = seen | {no}
        best, cyclic = 0, False
        for k in sub_calls.get(no, []):
            called.add(k)
            d, c = depth_from(k, seen)
            cyclic = cyclic or c
            best = max(best, d)
        return best + 1, cyclic
    for p in systems:
        for no in calls_of(p['stmts']):
            called.add(no)
            d, cyclic = depth_from(no, set())
            if cyclic:
                cross.append(dict(severity='error', file=p['file'], code='RECURSE', certain=True,
                                  message='M98 P%s из %s: рекурсивный вызов подпрограмм (A вызывает B, которая вызывает A...) - бесконечная вложенность' % (no, p['file']['name'])))
            elif d > 10:
                cross.append(dict(severity='error', file=p['file'], code='P230', certain=True,
                                  message='M98 P%s из %s: вложенность вызовов подпрограмм %d (>10, см. аварию станка P230 "Subprogram nesting over")' % (no, p['file']['name'], d)))
    for no in subprograms:
        if no not in called:
            cross.append(dict(severity='warning', file=None, code='UNUSED-SUB', certain=True,
                              message='Подпрограмма O%s загружена, но не вызывается ни из одной системы и ни из другой подпрограммы' % no))
    if len(systems) > 1:
        activity = []
        for p in systems:
            seg, cur = 0, None
            by_seg = {}
            for s in p['stmts']:
                t = _tok(s, 'T')
                if t:
                    raw = str(t['valueExpr']).strip()
                    v = js_parse_float(raw)
                    cur = None if (v == 0 or math.isnan(v)) else raw  # (parseFloat(raw) || 0) === 0
                cutting = any(v in (1, 2, 3) or (70 <= v <= 89 and v != 80) for v in _gvals(s) if not math.isnan(v))
                if cur is not None and cutting:
                    info = _tool_station(cur)
                    back = info and info[1] and p['file'].get('spindle') is not None and str(p['file'].get('spindle')) != '1'
                    if info and not back:
                        by_seg.setdefault(seg, []).append(dict(lineNo=s['lineNo'], cls=info[0], raw=cur))
                if any(t2['type'] == 'sync' for t2 in s['tokens']):
                    seg += 1
            activity.append(by_seg)
        segs = []
        for by_seg in activity:
            for k in by_seg:
                if k not in segs:
                    segs.append(k)
        for k in segs:
            involved = [(systems[i], a[k]) for i, a in enumerate(activity) if a.get(k)]
            if len(involved) > 1:
                desc = '  ×  '.join('%s: T%s (%s), стр. %d' % (p['file']['name'], items[0]['raw'], items[0]['cls'], items[0]['lineNo']) for p, items in involved)
                cross.append(dict(severity='warning', file=None, code='TOOL-CAPACITY', certain=False,
                                  message='Возможное столкновение инструментов: между соседними барьерами !L обе системы одновременно режут инструментом с каретки главного шпинделя - %s. Проверьте синхронизацию; T0101-T0404 независимого поста встречного шпинделя уже исключены автоматически (по выбранному шпинделю системы).' % desc))
    errors = sum(f['severity'] == 'error' for p in per_file for f in p['findings']) + sum(f['severity'] == 'error' for f in cross)
    warnings = sum(f['severity'] == 'warning' for p in per_file for f in p['findings']) + sum(f['severity'] == 'warning' for f in cross)
    return dict(perFile=per_file, crossFindings=cross, totalErrors=errors, totalWarnings=warnings)
