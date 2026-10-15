"""Проверка технологии и врезаний для автомата (система главного шпинделя).

Модель заготовки — тело вращения: для каждого сечения Z хранится наружный
радиус R(z) и радиус отверстия B(z). Траектория (nc_engine.Simulator.path)
проходится по порядку: рабочие ходы снимают материал (точка вершины
резца; для отрезных/канавочных — с шириной пластины, для сверл — радиусом
сверла), а ускоренные ходы проверяются на попадание в материал.

Ограничения модели (чтобы не выдавать ложных тревог):
 * только плоскость G18 (точение/сверление по оси); фрезерные и
   радиальные переходы (G19, C-ось) не меняют заготовку и не проверяются;
 * радиус при вершине и форма резца не учитываются (запас 0,15 мм);
 * переходы до первой известной точки (после G28) не рисуются и не проверяются.
"""
import math
import re

DZ = 0.05
MARGIN = 0.15
DRILL_WORDS = ('SVERL', 'СВЕРЛ', 'DRILL', 'CENTR', 'ЦЕНТР', 'ZENK', 'ЗЕНК', 'RAZV', 'РАЗВ', 'SCD', 'DCN', 'FCP', 'HCP')
BORE_WORDS = ('RAST', 'РАСТ', 'BOR', 'РАСТОЧ', 'INNER', 'ВНУТР')
GROOVE_WORDS = ('RESEC', 'РЕЗЕЦ ОТР', 'OTR', 'ОТР', 'KANAV', 'КАНАВ', 'GROOV', 'PROTO4', 'ПРОТОЧ')


def bar_diameter(text, default=None):
    m = re.search(r'(?:KRUG|КРУГ|PRUTOK|ПРУТОК|ZAGOTOVKA|ЗАГОТОВКА)[^)\n]*?D\s*(\d+(?:\.\d+)?)', text or '', re.I)
    if m:
        return float(m.group(1))
    m = re.search(r'#\d+\s*=\s*(\d+(?:\.\d*)?)\s*\(\s*(?:DIAMETR|ДИАМЕТР)\s*ZAGOTOVKI', text or '', re.I)
    return float(m.group(1)) if m else default


def tool_kind(name):
    up = (name or '').upper()
    if any(w in up for w in DRILL_WORDS):
        return 'drill'
    if any(w in up for w in GROOVE_WORDS):
        return 'groove'
    return 'turn'


def tool_size(name, kind):
    up = (name or '').upper()
    if kind == 'drill':
        m = re.search(r'D\s*(\d+(?:\.\d+)?)', up) or re.search(r'(\d+(?:\.\d+)?)', up)
        if m:
            d = float(m.group(1))
            if d > 60:          # «DR185» — диаметр в десятых мм
                d /= 10
            return d / 2
        return 0.5
    if kind == 'groove':
        m = re.search(r'(?:H|B|W)\s*=\s*(\d+(?:\.\d+)?)', up) or re.search(r'(?:SHIR|ШИР)[A-ZА-Я]*\s*(\d+(?:\.\d+)?)', up)
        return float(m.group(1)) if m else None
    return 0.0


class Stock:
    def __init__(self, radius, z_face, z_end):
        self.z0 = z_face
        self.n = max(2, int((z_end - z_face) / DZ) + 2)
        self.R = [radius] * self.n
        self.B = [0.0] * self.n
        self.touched = [False] * self.n     # поверхность прошёл рабочий ход после черновой
        self.radius = radius

    def index(self, z):
        i = int(round((z - self.z0) / DZ))
        return i if 0 <= i < self.n else None

    def z_of(self, i):
        return self.z0 + i * DZ

    def cut_outer(self, z, r, width=0.0):
        r = max(0.0, r)
        lo, hi = (z - width / 2, z + width / 2) if width else (z, z)
        i0, i1 = self.index(max(lo, self.z0)), self.index(min(hi, self.z_of(self.n - 1)))
        if i0 is None or i1 is None:
            return 0.0
        removed = 0.0
        for i in range(i0, i1 + 1):
            if r <= self.R[i] + 0.01:
                self.touched[i] = True
            if r < self.R[i]:
                removed = max(removed, self.R[i] - max(r, self.B[i]))
                self.R[i] = max(r, 0.0)
        return removed

    def cut_bore(self, z_tip, r, z_from):
        """Сверло радиуса r от z_from до вершины z_tip."""
        lo, hi = sorted((z_from, z_tip))
        i0, i1 = self.index(max(lo, self.z0)), self.index(min(hi, self.z_of(self.n - 1)))
        if i0 is None or i1 is None:
            return 0.0
        removed = 0.0
        for i in range(i0, i1 + 1):
            if self.B[i] < r and self.R[i] > self.B[i]:
                removed = max(removed, r - self.B[i])
                self.B[i] = min(r, self.R[i])
        return removed

    def solid(self, z, r, m=MARGIN):
        """Глубина нахождения точки в материале (0 — снаружи)."""
        i = self.index(z)
        if i is None or z < self.z0 + m:
            return 0.0
        R, B = self.R[i], self.B[i]
        if R - B < 2 * m:
            return 0.0
        if r < m:          # на оси: материал есть, если нет отверстия
            return min(R, m) if B < m / 2 else 0.0
        if B + m <= r <= R - m:
            return min(r - B, R - r)
        return 0.0

    def max_r(self, z0, z1):
        lo, hi = sorted((z0, z1))
        vals = [self.R[i] for i in range(self.n) if lo <= self.z_of(i) <= hi and self.R[i] > self.B[i] + 1e-6]
        return max(vals) if vals else 0.0


def samples(p0, p1):
    (x0, z0), (x1, z1) = p0, p1
    r0, r1 = abs(x0) / 2, abs(x1) / 2
    n = max(1, int(math.ceil(max(abs(z1 - z0), abs(r1 - r0)) / (DZ / 2))))
    n = min(n, 20000)
    for k in range(n + 1):
        t = k / n
        yield z0 + (z1 - z0) * t, r0 + (r1 - r0) * t, x0 + (x1 - x0) * t


def profile_rmax(profile, z):
    """Наибольший радиус профиля в сечении z (внутренний контур - расточка)."""
    best = None
    for (xa, za), (xb, zb) in zip(profile, profile[1:]):
        lo, hi = sorted((za, zb))
        if lo - 1e-9 <= z <= hi + 1e-9:
            if abs(zb - za) < 1e-9:
                r = max(abs(xa), abs(xb)) / 2
            else:
                t = (z - za) / (zb - za)
                r = abs(xa + (xb - xa) * t) / 2
            best = r if best is None else max(best, r)
    return best


def profile_r(profile, z):
    """Наименьший радиус профиля в сечении z (для контура с припуском)."""
    best = None
    for (xa, za), (xb, zb) in zip(profile, profile[1:]):
        lo, hi = sorted((za, zb))
        if lo - 1e-9 <= z <= hi + 1e-9:
            if abs(zb - za) < 1e-9:
                r = min(abs(xa), abs(xb)) / 2
            else:
                t = (z - za) / (zb - za)
                r = abs(xa + (xb - xa) * t) / 2
            best = r if best is None else min(best, r)
    return best


def analyze(sim, text, names=None, bar_d=None):
    """sim — Simulator главного шпинделя после run(). names — {T: комментарий}.
    -> dict(issues=[...], stock=Stock|None, bar=диаметр, face=z торца)."""
    names = names or {}
    issues = []

    def add(sev, code, msg, seg=None, line=None, prog=None, certain=True, at=None):
        issues.append(dict(severity=sev, code=code, message=msg, line=line if line is not None else (seg or {}).get('line'),
                           prog=prog or (seg or {}).get('prog'), certain=certain, at=at))

    path = [s for s in sim.path if s['plane'] == 18 and not s['info'].get('caxis')]
    by_line = tool_names(text)
    first_main = next((k for k, s in enumerate(path) if s['prog'] == 'MAIN' and s['kind'] in ('feed', 'groove', 'drill', 'cycle')), None)
    if first_main is not None:
        path = path[first_main:]
    bar_d = bar_d or bar_diameter(text)
    if not bar_d:
        xs = [abs(x) for s in path if s['kind'] in ('feed', 'groove') for x, _ in s['pts']]
        bar_d = max(xs) if xs else None
    if not bar_d or not path:
        return dict(issues=issues, stock=None, bar=bar_d, face=None)
    radius = bar_d / 2
    z_face = None
    for s in path:
        if s['kind'] in ('feed', 'groove', 'cycle') and tool_kind(names.get(_t(s.get('tool')), '')) != 'drill' and \
                any(abs(a[0] - b[0]) > 0.5 for a, b in zip(s['pts'], s['pts'][1:])):
            zs = [z for z, r, _ in (pt for a, b in zip(s['pts'], s['pts'][1:]) for pt in samples(a, b)) if r < radius - 0.01]
            if zs:
                z_face = min(zs)
                break
    if z_face is None:
        return dict(issues=issues, stock=None, bar=bar_d, face=None)
    z_end = max(z for s in path for _, z in s['pts']) + 10
    stock = Stock(radius, z_face, z_end)
    thread_cycles = {(c['prog'], c['line']): c for c in sim.cycles if c['kind'] == 'G76'}
    profiles = [c for c in sim.cycles if c['kind'] in ('G71', 'G73')]
    checked_threads = set()
    rapid_hits = set()
    feed_warned = set()

    for c in sim.cycles:
        if c['kind'] in ('G71', 'G73') and c.get('profile'):
            check_cycle_start(c, add, bar_d)
        if c['kind'] == 'G75':
            name = names.get(_t(c.get('tool')), '')
            width = tool_size(name, 'groove') if tool_kind(name) == 'groove' else None
            if width and c['step'] > width + 1e-6:     # только если ширина пластины явно указана в названии (H=3. / B=3.)
                add('warning', 'G75 Q', 'G75: шаг по Z Q%.3f больше ширины пластины %.3g мм (%s) - между врезаниями останутся '
                    'гребешки.' % (c['step'], width, name), line=c['line'], prog=c['prog'])

    for s in path:
        tool = _t(s.get('tool'))
        name = name_at(by_line, tool, s['line']) if s['prog'] == 'MAIN' else names.get(tool, '')
        name = name or names.get(tool, '')
        kind = tool_kind(name)
        if s['kind'] == 'rapid' and s['info'].get('cycle'):
            continue
        if s['kind'] == 'rapid':
            for a, b in zip(s['pts'], s['pts'][1:]):
                for z, r, x in samples(a, b):
                    depth = stock.solid(z, r if kind != 'drill' else min(r, MARGIN / 2) if r < MARGIN else r)
                    if kind == 'drill' and r < MARGIN:
                        depth = stock.solid(z, 0.0)
                    if depth > 0:
                        key = (s['prog'], s['line'])
                        if key not in rapid_hits:
                            rapid_hits.add(key)
                            deep = depth >= 1.0
                            add('error' if deep else 'warning', 'G0 в материал',
                                'Ускоренный ход G0 проходит через материал заготовки (X%.3f Z%.3f, глубина %.2f мм) инструментом '
                                '%s%s - %s' % (x, z, depth, 'T' + tool if tool else '?', (' (%s)' % name) if name else '',
                                               'врезание/авария. Проверьте точку подвода и предыдущие переходы.' if deep else
                                               'неглубоко: возможно, это неточность модели (положение торца до подрезки, точка R). '
                                               'Проверьте точку подвода.'),
                                s, at=(x, z), certain=deep)
                        break
                else:
                    continue
                break
            # раз инструмент прошёл (на станке он при этом снял металл) — убираем материал по пути,
            # иначе следующие переходы дают ложные «врезания» в уже несуществующий металл
            for a, b in zip(s['pts'], s['pts'][1:]):
                if kind == 'drill' and abs(a[0]) < 0.3 and abs(b[0]) < 0.3:
                    stock.cut_bore(max(a[1], b[1]), tool_size(name, 'drill'), min(a[1], b[1]))
                elif (s['prog'], s['line']) in rapid_hits:
                    for z, r, _ in samples(a, b):
                        stock.cut_outer(z, r)
            continue
        if s['kind'] == 'thread':
            key = (s['prog'], s['line'])
            if key in thread_cycles and key not in checked_threads:
                checked_threads.add(key)
                check_thread(thread_cycles[key], stock, add)
            continue
        if s['kind'] == 'cycle' and not s['info'].get('profile'):
            continue
        if s['kind'] == 'cycle':
            U, W = s['info'].get('U', 0) or 0, s['info'].get('W', 0) or 0
            x_start = abs(s['pts'][0][0])
            inner_cycle = x_start < sum(abs(x) for x, _ in s['pts'][1:]) / max(1, len(s['pts']) - 1)
            prof = [(abs(x) - abs(U) if inner_cycle else abs(x) + U, z + W) for x, z in s['pts'][1:]]
            zs = [z for _, z in prof]
            for i in range(stock.n):
                z = stock.z_of(i)
                if min(zs) - 1e-9 <= z <= max(zs) + 1e-9:
                    if inner_cycle:
                        r = profile_rmax(prof, z)
                        if r is not None and r > stock.B[i]:
                            stock.B[i] = min(r, stock.R[i])
                        continue
                    r = profile_r(prof, z)
                    if r is not None and r < stock.R[i]:
                        stock.R[i] = max(r, stock.B[i])
                        stock.touched[i] = False
            continue
        # рабочие ходы: feed, groove, drill
        for a, b in zip(s['pts'], s['pts'][1:]):
            axial = abs(a[0]) < 0.3 and abs(b[0]) < 0.3
            if s['kind'] == 'drill' or (kind == 'drill' and axial):
                rd = tool_size(name, 'drill') if kind == 'drill' else 0.5
                if 'CENTR' in name.upper() or 'ЦЕНТР' in name.upper():
                    tip = max(a[1], b[1])
                    for i in range(stock.n):
                        z = stock.z_of(i)
                        if z <= tip + DZ / 2:
                            rr = max(min(rd, tip - z), MARGIN)
                            if stock.B[i] < rr <= stock.R[i]:
                                stock.B[i] = rr
                else:
                    stock.cut_bore(max(a[1], b[1]), rd, min(a[1], b[1]))
                continue
            width = (tool_size(name, 'groove') or 2.0) if (kind == 'groove' or s['kind'] == 'groove') else 0.0
            removed = 0.0
            inner = any(w in name.upper() for w in BORE_WORDS)
            if not inner:
                # внутренний инструмент: есть отверстие, резец у его стенки, а снаружи ещё толстый слой материала
                # (проходной резец так стоять не может - корпус был бы в металле)
                for z, r, _ in samples(a, b):
                    i = stock.index(z)
                    if i is None or r < MARGIN:
                        continue
                    if stock.B[i] > MARGIN and r >= stock.B[i] - 0.05 and stock.R[i] - r > 3.0:
                        inner = True
                    break
            for z, r, _ in samples(a, b):
                if inner:      # расточной/внутренний инструмент: растёт отверстие
                    i = stock.index(z)
                    if i is not None and r > stock.B[i]:
                        removed = max(removed, min(r, stock.R[i]) - stock.B[i])
                        stock.B[i] = min(r, stock.R[i])
                else:
                    removed = max(removed, stock.cut_outer(z, r, width))
            fpr = s['info'].get('fpr', True)
            feed = s['info'].get('feed') or 0
            limit = {'drill': 0.3, 'groove': 0.25}.get(kind, 0.6)
            if removed > 0.05 and fpr and feed > limit and (s['prog'], s['line']) not in feed_warned:
                feed_warned.add((s['prog'], s['line']))
                add('warning', 'F в материале', 'Подача F%s мм/об при резании (снимается %.2f мм) инструментом T%s %s - для %s это много, '
                    'проверьте режим.' % (_num(feed), removed, tool, name, {'drill': 'сверла', 'groove': 'отрезного/канавочного резца'}.get(kind, 'проходного резца')),
                    s, certain=False)

    # припуск, оставленный черновыми циклами и не снятый чистовыми переходами
    for c in profiles:
        U, W = c.get('U') or 0, c.get('W') or 0
        if c['kind'] == 'G71' and abs(U) < 1e-9 and abs(W) < 1e-9:
            continue
        x0 = abs(c['start'][0])
        prof = [(abs(x), z) for x, z in c['profile']]
        if x0 < sum(x for x, _ in prof) / len(prof):     # внутренний контур - припуск не проверяем
            continue
        bad = []
        for i in range(stock.n):
            z = stock.z_of(i)
            r = profile_r(prof, z)
            if r is None or r * 2 >= abs(x0) - 0.01 or stock.R[i] <= stock.B[i] + 1e-6:
                continue
            if stock.R[i] - r > 0.05 and not stock.touched[i]:
                bad.append((z, stock.R[i], r))
        for group in _groups(bad):
            z0, z1 = group[0][0], group[-1][0]
            if z1 - z0 < 0.3:
                continue
            worst = max(group, key=lambda g: g[1] - g[2])
            add('warning', 'Припуск', '%s (стр. %d): на Z%.2f…%.2f после черновой остаётся Ø%.3f (контур Ø%.3f + припуск '
                '%.3f), и больше этот участок не обрабатывается - чистового прохода (G70 или контура чистовым резцом) нет. '
                'Если Ø%.3f - чертёжный размер, он не выдержан; если контур специально занижен на припуск - всё верно.' % (
                    c['kind'], c['line'], z0, z1, worst[1] * 2, worst[2] * 2, (worst[1] - worst[2]) * 2, worst[2] * 2),
                line=c['line'], prog=c['prog'], at=(worst[1] * 2, worst[0]), certain=False)
    return dict(issues=issues, stock=stock, bar=bar_d, face=z_face)


def tool_names(text):
    """[(строка, T, название)] — каждое упоминание T с комментарием (на той же или следующей строке)."""
    out = []
    lines = (text or '').split('\n')
    for k, raw in enumerate(lines):
        code = re.sub(r'\([^)]*\)', '', raw)
        for m in re.finditer(r'T(\d{3,4})', code):
            note = re.search(r'\(([^)]*)\)', raw)
            if not note and k + 1 < len(lines) and re.fullmatch(r'\s*\([^)]*\)\s*', lines[k + 1]):
                note = re.search(r'\(([^)]*)\)', lines[k + 1])
            if note and int(m.group(1)):
                out.append((k + 1, m.group(1), note.group(1).strip()))
    return out


def name_at(by_line, tool, line):
    """Название инструмента, действовавшее в строке line (последнее упоминание T с комментарием до неё)."""
    best = ''
    for ln, t, name in by_line:
        if t == tool and (line is None or ln <= line):
            best = name
    return best


def check_cycle_start(c, add, bar_d):
    x0, z0 = c['start']
    x0 = abs(x0)
    prof = [(abs(x), z) for x, z in c['profile']]
    body = [p for p in prof if abs(p[0] - x0) > 1e-6 or abs(p[1] - z0) > 1e-6]
    if not body:
        return
    xs = [p[0] for p in prof[:-1]] or [p[0] for p in prof]
    outer = sum(xs) / len(xs) < x0
    inside = [x for x in xs if x > x0 + 0.01 and x < bar_d - 0.05]
    if outer and inside:
        add('error', c['kind'] + ' старт', '%s: точка начала цикла X%.3f ниже контура (до Ø%.3f) - станок выдаст аварию '
            'или резец врежется. Начало цикла должно быть снаружи контура.' % (c['kind'], x0, max(inside)), line=c['line'], prog=c['prog'])
    if c['kind'] == 'G71':
        seq = [p[0] for p in prof[:-1]]
        if seq:
            rises = any(b < a - 1e-6 for a, b in zip(seq, seq[1:])) if outer else any(b > a + 1e-6 for a, b in zip(seq, seq[1:]))
            if rises:
                add('warning', 'G71 карман', 'G71: диаметр контура не монотонный (есть карман/поднутрение) - цикл типа I его '
                    'не обработает, нужен тип II или отдельный переход.', line=c['line'], prog=c['prog'], certain=False)


def check_thread(c, stock, add):
    x0, z0 = c['start']
    X, Z, h, lead, rpm = c['X'], c['Z'], c['height'], c['lead'], c['rpm']
    if not h or not lead:
        return
    x0, X = abs(x0), abs(X)
    if X >= x0:            # внутренняя резьба (резец идёт от оси наружу) — наружные проверки не применимы
        return
    major = X + 2 * h
    minor_r, major_r = X / 2, major / 2
    line, prog = c['line'], c['prog']
    crest = stock.max_r(z0, Z)
    if crest > major_r + 0.025:
        add('warning', 'G76 Ø', 'G76: резьба нарезается по Ø%.3f, а её расчётный наружный диаметр Ø%.3f (X%.3f + 2×P%.3f) - '
            'вершины резьбы останутся завышенными на %.3f. Проверьте чистовой проход по Ø резьбы.' % (
                crest * 2, major, X, h, (crest - major_r) * 2), line=line, prog=prog)
    top = max(crest, major_r)
    if x0 / 2 < top + 0.1:
        below_major = x0 / 2 < major_r - 0.01
        add('error' if below_major else 'warning', 'G76 отвод', 'G76: точка начала X%.3f не выше вершин резьбы Ø%.3f - после каждого прохода резец '
            'отводится только до X%.3f и ускоренно возвращается по Z, задевая вершины резьбы. Начало цикла - минимум '
            'на 0,5-1 мм по диаметру выше.' % (x0, top * 2, x0), line=line, prog=prog, certain=below_major or None)
    if not c.get('chamfer'):
        # конец резьбы за канавкой под выход: впереди по ходу была зона Ø ≤ внутреннего (канавка),
        # а в точке конца снова материал - на последних проходах резец режет стенку канавки
        i = stock.index(Z)
        step = 1 if Z > z0 else -1
        if i is not None and stock.R[i] > minor_r + 0.05 and stock.R[i] > stock.B[i]:
            k = i
            while 0 <= k < stock.n and stock.R[k] > minor_r + 0.05 and (stock.z_of(k) - z0) * step > 0:
                k -= step
            in_relief = 0 <= k < stock.n and (stock.z_of(k) - z0) * step > 0 and stock.R[k] <= minor_r + 0.05
            if in_relief:     # за канавкой (ближе к началу) должна быть сама резьба, иначе это просто подход
                j = k
                while 0 <= j < stock.n and stock.R[j] <= minor_r + 0.05 and (stock.z_of(j) - z0) * step > 0:
                    j -= step
                body = 0
                while 0 <= j < stock.n and stock.R[j] > minor_r + 0.05 and (stock.z_of(j) - z0) * step > 0:
                    body += 1
                    j -= step
                in_relief = body * DZ >= 2 * lead
            if in_relief:
                relief_end = stock.z_of(k)
                add('warning', 'G76 конец', 'G76: конец резьбы Z%.3f заходит за канавку под выход резьбы (Ø ≤ %.3f заканчивается на '
                    'Z%.2f) - на последних проходах резец подрезает стенку канавки до Ø%.3f, на %.2f мм по радиусу. '
                    'Если это сбег резьбы на скосе канавки - так и задумано; если стенка - посадочный бурт, конец резьбы '
                    'нужен не дальше Z%.2f.' % (Z, X, relief_end, stock.R[i] * 2, stock.R[i] - minor_r, relief_end),
                    line=line, prog=prog, at=(X, Z), certain=False)
    if rpm:
        need = lead * rpm / 1800 * 3.605
        start_mat = None
        step = 1 if Z > z0 else -1
        z = z0
        while (z - Z) * step < 0:
            i = stock.index(z)
            if i is not None and stock.R[i] > minor_r + 0.02 and z >= stock.z0:
                start_mat = z
                break
            z += step * DZ
        if start_mat is not None and abs(start_mat - z0) < need:
            add('warning', 'G76 разгон', 'G76: до материала %.2f мм от начала Z%.3f, а для разгона подачи при S%d и шаге %s нужно '
                '≈%.2f мм - первые витки получатся с неполным шагом. Отведите начало цикла дальше.' % (
                    abs(start_mat - z0), z0, rpm, _num(lead), need), line=line, prog=prog, certain=False)


def _groups(points):
    out, cur = [], []
    for p in points:
        if cur and p[0] - cur[-1][0] > DZ * 1.5:
            out.append(cur)
            cur = []
        cur.append(p)
    if cur:
        out.append(cur)
    return out


def _t(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s.isdigit() and int(s) else None


def _num(v):
    return ('%.4f' % v).rstrip('0').rstrip('.')
