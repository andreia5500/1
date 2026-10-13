# -*- coding: utf-8 -*-
# Ядро из kompas_dims_app.zip; сокращено до чтения размеров и допусков.
from __future__ import print_function
import argparse
import codecs
import math
import os
import re
import sys
import tolerances as T
import debug_log as J
KOMPAS_API7_GUID = '{69AC2981-37C0-4379-84FD-5DD2F3C0A520}'
__version__ = '2026-09-16б · шероховатость и допуски формы/расположения в ОКТК'

class KompasError(Exception):
    pass
STYLE_MAIN = 1
STYLE_THIN = 2
STYLE_AXIS = 3
STYLE_DASH = 4
EPS = 1e-06

def connect():
    try:
        import pythoncom
        from win32com.client import Dispatch, gencache
    except ImportError:
        raise KompasError('Не установлен pywin32.\n\nОткрой командную строку и выполни:\n    py -m pip install pywin32')
    module = gencache.EnsureModule(KOMPAS_API7_GUID, 0, 1, 0)
    if module is None:
        raise KompasError('Не удалось получить библиотеку типов API7.\n\nПроверь:\n  1. КОМПАС-3D установлен и хотя бы раз запускался;\n  2. разрядность Python совпадает с разрядностью КОМПАСа;\n  3. попробуй удалить кэш  %LOCALAPPDATA%\\Temp\\gen_py')
    try:
        raw = Dispatch('KOMPAS.Application.7')
        app = module.IApplication(raw._oleobj_.QueryInterface(module.IApplication.CLSID, pythoncom.IID_IDispatch))
    except pythoncom.com_error as e:
        raise KompasError('Не удалось подключиться к КОМПАСу: ' + str(e)) from e
    app.Visible = True
    return (module, app)
DOC_DRAWING = 1
DOC_FRAGMENT = 2
DOC_2D = (DOC_DRAWING, DOC_FRAGMENT)

def doc_type(doc):
    for attr in ('DocumentType', 'documentType'):
        try:
            v = getattr(doc, attr)
            if isinstance(v, int):
                return v
        except Exception:
            continue
    return None

def _doc_name(doc):
    for attr in ('PathName', 'pathName', 'Name', 'name'):
        try:
            v = getattr(doc, attr)
            if isinstance(v, str) and v:
                return v
        except Exception:
            continue
    return '(без имени)'

def find_2d_document(app):
    doc = app.ActiveDocument
    if doc is not None and doc_type(doc) in DOC_2D:
        return doc
    others = []
    try:
        docs = app.Documents
        for i in range(docs.Count):
            try:
                d = docs.Item(i)
            except Exception:
                continue
            if d is None:
                continue
            if doc_type(d) in DOC_2D:
                return d
            others.append('%s (тип %s)' % (_doc_name(d), doc_type(d)))
    except Exception:
        pass
    if others:
        raise KompasError('Среди открытых документов нет чертежа.\n\nСейчас открыты:\n  %s\n\nОткрой чертёж (.cdw/.frw) или выбери файл кнопкой «Открыть чертёж…».' % '\n  '.join(others))
    raise KompasError('В КОМПАСе нет открытого чертежа.\nОткрой чертёж или выбери файл кнопкой.')

def get_document(module, app, path=None):
    if path:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            raise KompasError('Файл не найден:\n%s' % path)
        doc = app.Documents.Open(path, True, False)
        if doc is None:
            raise KompasError('КОМПАС не смог открыть файл:\n%s' % path)
    else:
        doc = find_2d_document(app)
    if doc_type(doc) not in DOC_2D and doc_type(doc) is not None:
        raise KompasError('Это не чертёж, а документ типа %s.\nПереключись на вкладку чертежа или выбери файл кнопкой.' % doc_type(doc))
    try:
        return module.IKompasDocument2D(doc)
    except Exception as e:
        raise KompasError('Документ не является графическим (.cdw/.frw).\n%s' % e)

def tl_str(obj):
    if obj is None:
        return ''
    try:
        return (obj.Str or '').strip()
    except Exception:
        return ''

def txt_str(obj):
    if obj is None:
        return ''
    if isinstance(obj, str):
        return obj.strip()
    try:
        return (obj.Str or '').strip()
    except Exception:
        pass
    try:
        parts = []
        for i in range(obj.Count):
            parts.append(tl_str(obj.TextLine(i)))
        return ' '.join((p for p in parts if p))
    except Exception:
        return ''

def get(obj, name, default=None):
    try:
        v = getattr(obj, name)
        return default if v is None else v
    except Exception:
        return default

class Geometry(object):

    def __init__(self):
        self.segments = []
        self.axis_y = None
        self.axis_x = None
        self.circles = []
        self.n_centre = 0
        self.axis_from_line = False
        self.axis_len = 0.0
        self.profile_ok = False
        self.profile_why = ''

    @classmethod
    def from_view(cls, module, view, use_hidden=False):
        g = cls()
        styles = {STYLE_MAIN}
        if use_hidden:
            styles.add(STYLE_DASH)
        try:
            cont = module.IDrawingContainer(view)
        except Exception:
            return g
        try:
            segs = cont.LineSegments
            for i in range(segs.Count):
                s = segs.LineSegment(i)
                if get(s, 'Style', STYLE_MAIN) not in styles:
                    continue
                g.segments.append((s.X1, s.Y1, s.X2, s.Y2))
        except Exception:
            pass
        try:
            arcs = cont.Arcs
            for i in range(arcs.Count):
                a = arcs.Arc(i)
                if get(a, 'Style', STYLE_MAIN) not in styles:
                    continue
                g.segments.extend(_arc_to_segments(a.Xc, a.Yc, a.Radius, a.Ang1, a.Ang2))
        except Exception:
            pass
        try:
            circles = cont.Circles
            for i in range(circles.Count):
                c = circles.Circle(i)
                if get(c, 'Style', STYLE_MAIN) not in styles:
                    continue
                g.circles.append((c.Xc, c.Yc, c.Radius))
                g.segments.extend(_arc_to_segments(c.Xc, c.Yc, c.Radius, 0, 360))
        except Exception:
            pass
        try:
            sym = module.ISymbols2DContainer(view)
            g.n_centre = sym.CentreMarkers.Count
        except Exception:
            g.n_centre = 0
        g.axis_y, g.axis_x, g.axis_from_line, g.axis_len = _find_axis(module, view, g.segments)
        _judge_profile(g)
        return g

    def radii_at(self, x, axis_y):
        out = []
        for x1, y1, x2, y2 in self.segments:
            lo, hi = (x1, x2) if x1 <= x2 else (x2, x1)
            if x < lo - 0.0001 or x > hi + 0.0001:
                continue
            if abs(x2 - x1) < 1e-09:
                out.append(abs(y1 - axis_y))
                out.append(abs(y2 - axis_y))
            else:
                t = (x - x1) / (x2 - x1)
                t = min(1.0, max(0.0, t))
                out.append(abs(y1 + t * (y2 - y1) - axis_y))
        return out

    def max_radius_at(self, x, axis_y):
        r = self.radii_at(x, axis_y)
        return max(r) if r else None

def _arc_to_segments(xc, yc, r, a1, a2, step_deg=5.0):
    a1 = float(a1)
    a2 = float(a2)
    sweep = a2 - a1
    while sweep <= 0:
        sweep += 360.0
    n = max(2, int(math.ceil(sweep / step_deg)))
    pts = []
    for i in range(n + 1):
        a = math.radians(a1 + sweep * i / float(n))
        pts.append((xc + r * math.cos(a), yc + r * math.sin(a)))
    return [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)]

def _find_axis(module, view, segments):
    cand_h, cand_v = ([], [])
    try:
        sym = module.ISymbols2DContainer(view)
        ax = sym.AxisLines
        for i in range(ax.Count):
            a = ax.AxisLine(i)
            x1, y1 = (get(a, 'X1'), get(a, 'Y1'))
            x2, y2 = (get(a, 'X2'), get(a, 'Y2'))
            if None in (x1, y1, x2, y2):
                continue
            if abs(y2 - y1) < 1e-06:
                cand_h.append((abs(x2 - x1), y1))
            elif abs(x2 - x1) < 1e-06:
                cand_v.append((abs(y2 - y1), x1))
    except Exception:
        pass
    if not cand_h and (not cand_v):
        try:
            cont = module.IDrawingContainer(view)
            segs = cont.LineSegments
            for i in range(segs.Count):
                s = segs.LineSegment(i)
                if get(s, 'Style', 0) != STYLE_AXIS:
                    continue
                if abs(s.Y2 - s.Y1) < 1e-06:
                    cand_h.append((abs(s.X2 - s.X1), s.Y1))
                elif abs(s.X2 - s.X1) < 1e-06:
                    cand_v.append((abs(s.Y2 - s.Y1), s.X1))
        except Exception:
            pass
    axis_y = max(cand_h)[1] if cand_h else None
    axis_x = max(cand_v)[1] if cand_v else None
    axis_from_line = bool(cand_h)
    axis_len = max(cand_h)[0] if cand_h else 0.0
    if axis_y is None and segments:
        ys = []
        for x1, y1, x2, y2 in segments:
            ys.extend([y1, y2])
        axis_y = (min(ys) + max(ys)) / 2.0
    return (axis_y, axis_x, axis_from_line, axis_len)

def _judge_profile(g):
    if g.axis_y is None:
        g.profile_ok = False
        g.profile_why = 'ось не найдена'
        return
    if g.n_centre:
        g.profile_ok = False
        g.profile_why = 'вид с торца (обозначение центра)'
        return
    groups = {}
    for xc, yc, r in g.circles:
        key = (round(xc, 2), round(yc, 2))
        groups.setdefault(key, []).append(r)
    if any((len(v) >= 2 for v in groups.values())):
        g.profile_ok = False
        g.profile_why = 'вид с торца (концентрические окружности)'
        return
    if g.segments:
        xs = [v for s in g.segments for v in (s[0], s[2])]
        ys = [v for s in g.segments for v in (s[1], s[3])]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if g.circles and h > 1e-06 and (0.6 <= w / h <= 1.7):
            g.profile_ok = False
            g.profile_why = 'габарит близок к квадрату, есть окружности'
            return
    if not g.axis_from_line:
        g.profile_ok = False
        g.profile_why = 'ось только по симметрии контура'
        return
    g.profile_ok = True
    g.profile_why = 'профильный вид, ось %.0f мм' % g.axis_len
KIND_OUTER = 'нар. диаметр'
KIND_INNER = 'вн. диаметр'
KIND_LINEAR = 'линейный'
KIND_RADIUS = 'радиус'
KIND_CHAMFER = 'фаска'
KIND_ANGLE = 'угловой'
KIND_THREAD = 'резьба'
KIND_ROUGHNESS = 'шероховатость'
KIND_FORM_TOL = 'допуск формы/расположения'
INDEX_MID_START = '$m'
INDEX_MID_END = ';$'
INDEX_MID_STACK_END = '$'

def _maybe_index_dev(dev):
    if not dev:
        return dev
    if dev.startswith('±'):
        return dev
    if ';' in dev:
        return INDEX_MID_START + dev + INDEX_MID_STACK_END
    if dev.startswith(('-', '−')):
        return INDEX_MID_START + ';' + dev + INDEX_MID_STACK_END
    return INDEX_MID_START + dev + INDEX_MID_END
SRC_DRAWING = 'чертёж'
SRC_DEFAULT = 'неуказ.'
RE_FIT = re.compile('^\\s*([A-Za-z]{1,2})\\s*(\\d{1,2})\\s*$')
RE_DIA = re.compile('[\\u2300\\u00d8\\u00f8]|%%c|@')
RE_THREAD = re.compile('^\\s*M\\s*\\d', re.I)
RE_THREAD_NUM = re.compile('^\\s*M\\s*(\\d+(?:[.,]\\d+)?)', re.I)
RE_LEADING_NUM = re.compile('^\\s*(\\d+(?:[.,]\\d+)?)')
RE_HOLE_COUNT = re.compile('(\\d+)\\s*отв', re.I)
RE_MINMAX = re.compile('\\b(min|max)\\b', re.I)
RE_EMBEDDED_CHAMFER_ANGLE = re.compile('@\\d+~\\s*(\\d+(?:[.,]\\d+)?)\\s*@\\d+~')
RE_SPECIAL_CONTROL = re.compile('(?<![А-ЯЁа-яё0-9])ОК(?![А-ЯЁа-яё0-9])')

def _strip_special_control(text):
    if not text or 'ОК' not in text:
        return (text, False)
    cleaned = RE_SPECIAL_CONTROL.sub('', text)
    cleaned = re.sub('\\s+', ' ', cleaned).strip()
    return (cleaned, cleaned != text)

def _value_from_text(text):
    if not text:
        return None
    m = RE_THREAD_NUM.match(text)
    if m:
        return float(m.group(1).replace(',', '.'))
    m = RE_LEADING_NUM.match(text)
    if m:
        return float(m.group(1).replace(',', '.'))
    return None

class Dim(object):
    __slots__ = ('view', 'view_label', 'src_kind', 'kind', 'value', 'hi', 'lo', 'fit', 'src', 'x', 'y', 'anchors', 'note', 'raw_text', 'auto', 'reason', 'manual', 'manual_tol', 'short_side', 'count', 'limit', 'chamfer_angle', 'tol_sign', 'groove', 'instrument', 'instrument_manual', 'export_error')

    def __init__(self):
        self.view = ''
        self.view_label = ''
        self.src_kind = ''
        self.kind = KIND_LINEAR
        self.value = 0.0
        self.hi = None
        self.lo = None
        self.fit = ''
        self.src = SRC_DEFAULT
        self.x = None
        self.y = None
        self.anchors = None
        self.note = ''
        self.raw_text = ''
        self.auto = True
        self.reason = ''
        self.short_side = None
        self.manual = False
        self.manual_tol = False
        self.count = None
        self.limit = None
        self.chamfer_angle = None
        self.tol_sign = None
        self.groove = False
        self.instrument = ""
        self.instrument_manual = False
        self.export_error = ""

    def sign_prefix(self):
        if self.kind in (KIND_OUTER, KIND_INNER):
            return 'Ø'
        if self.kind == KIND_RADIUS:
            return 'R'
        return ''

    def column_text(self, comma=True):
        if self.note.startswith('допуск в тексте:'):
            return self.raw_text
        if self.kind in (KIND_ROUGHNESS, KIND_FORM_TOL, "требование", "надпись") :
            return self.raw_text
        if self.kind == KIND_THREAD and self.raw_text:
            base = self.raw_text.replace(' ', '')
            dev = ''
            parts = [base]
            if dev:
                parts.append(dev)
            return ' '.join(parts)
        if self.kind in (KIND_RADIUS, KIND_CHAMFER) or self.limit:
            val = T.fmt_num(self.value, comma=comma)
            base = self.sign_prefix() + val
            if self.chamfer_angle is not None:
                base = '%sх%s°' % (base, T.fmt_num(self.chamfer_angle, comma=comma))
            if (self.src == SRC_DRAWING or self.manual_tol) and not self.limit:
                base += _maybe_index_dev(T.fmt_dev(self.hi, self.lo, comma=comma))
            parts = [base]
            if self.limit:
                parts.append(self.limit)
            if self.count:
                parts.append('%d отв.' % self.count)
            return ' '.join(parts)
        val = T.fmt_num(self.value, comma=comma)
        if self.kind == KIND_ANGLE:
            dev = T.fmt_angle_pair(self.hi, self.lo)
            base = val + '°'
        else:
            dev = T.fmt_dev(self.hi, self.lo, comma=comma)
            base = self.sign_prefix() + val
        text = base
        if self.fit:
            text += self.fit
        if dev:
            text += _maybe_index_dev(dev)
        parts = [text]
        if self.count:
            parts.append('%d отв.' % self.count)
        return ' '.join(parts)

def read_dimension(module, obj, src_kind, view_name):
    try:
        dt = module.IDimensionText(obj)
    except Exception as exc:
        J.failure('Не прочитан интерфейс размера',exc,view=view_name,kind=src_kind)
        return None
    d = Dim()
    d.view = view_name
    d.src_kind = src_kind
    d.auto = bool(get(dt, 'AutoNominalValue', True))
    sign = int(get(dt, 'Sign', 0) or 0)
    prefix = tl_str(get(dt, 'Prefix'))
    suffix = tl_str(get(dt, 'Suffix'))
    nom_text = tl_str(get(dt, 'NominalText'))
    under = txt_str(get(dt, 'TextUnder'))
    d.raw_text = ' '.join((p for p in (prefix, nom_text, suffix, under) if p))
    d.raw_text, had_special_control = _strip_special_control(d.raw_text)
    if had_special_control:
        d.note = (d.note + ' ' if d.note else '') + 'особый контроль (ОК) — буквы убраны из записи'
    m_cnt = RE_HOLE_COUNT.search(suffix) or RE_HOLE_COUNT.search(under)
    if m_cnt:
        d.count = int(m_cnt.group(1))
    m_lim = RE_MINMAX.search(d.raw_text)
    if m_lim:
        d.limit = m_lim.group(1).lower()
    raw_nominal = float(get(dt, 'NominalValue', 0.0) or 0.0)
    forced = _value_from_text(nom_text) if nom_text else None
    if forced is not None:
        d.value = forced
    elif not d.auto:
        d.value = raw_nominal
        d.note = 'ручной текст размера, число не распознано: %r' % nom_text
    else:
        d.value = raw_nominal
    fit = (get(dt, 'Tolerance', '') or '').strip()
    fit_on = bool(get(dt, 'ToleranceOn', False))
    if fit_on and fit:
        d.fit = fit
    dev_on = bool(get(dt, 'DeviationOn', False))
    hi = get(dt, 'HighDeviationValue')
    lo = get(dt, 'LowDeviationValue')
    hi_txt = tl_str(get(dt, 'HighDeviation'))
    lo_txt = tl_str(get(dt, 'LowDeviation'))
    if dev_on or d.fit:
        if hi is not None or lo is not None:
            d.hi = float(hi or 0.0)
            d.lo = float(lo or 0.0)
        if d.hi in (None, 0.0) and d.lo in (None, 0.0):
            d.hi = _num(hi_txt, d.hi)
            d.lo = _num(lo_txt, d.lo)
    has_tol = bool(d.fit) or d.hi not in (None, 0.0) or d.lo not in (None, 0.0)
    if not has_tol and (not d.auto):
        m = re.search('[±+\\-]\\s*\\d+[.,]\\d+', nom_text + ' ' + suffix + ' ' + under)
        if m:
            has_tol = True
            d.note = 'допуск в тексте: %s' % d.raw_text
    d.src = SRC_DRAWING if has_tol else SRC_DEFAULT
    is_dia = sign == 1 or bool(RE_DIA.search(prefix + nom_text)) or src_kind in ('diam',)
    if sign == 4 or RE_THREAD.match(prefix) or RE_THREAD.match(nom_text):
        d.kind = KIND_THREAD
    elif src_kind == 'angle':
        d.kind = KIND_ANGLE
    elif src_kind == 'rad':
        d.kind = KIND_RADIUS
    elif is_dia:
        d.kind = KIND_OUTER
    else:
        d.kind = KIND_LINEAR
    if d.kind == KIND_LINEAR:
        m_ea = RE_EMBEDDED_CHAMFER_ANGLE.search(suffix) or RE_EMBEDDED_CHAMFER_ANGLE.search(under)
        if m_ea:
            d.kind = KIND_CHAMFER
            d.chamfer_angle = float(m_ea.group(1).replace(',', '.'))
    x1, y1 = (get(obj, 'X1'), get(obj, 'Y1'))
    x2, y2 = (get(obj, 'X2'), get(obj, 'Y2'))
    xc, yc = (get(obj, 'Xc'), get(obj, 'Yc'))
    if None not in (x1, y1, x2, y2):
        d.anchors = (x1, y1, x2, y2)
    if x1 is not None and x2 is not None:
        d.x = (x1 + x2) / 2.0
        d.y = (y1 + y2) / 2.0 if y1 is not None and y2 is not None else None
    elif xc is not None:
        d.x, d.y = (xc, yc)
    if d.kind == KIND_ANGLE and None not in (x1, y1, x2, y2, xc, yc):
        s1 = math.hypot(x1 - xc, y1 - yc)
        s2 = math.hypot(x2 - xc, y2 - yc)
        d.short_side = min(s1, s2)
        d.note = 'короткая сторона %.1f мм' % d.short_side
    return d

def _num(s, default=None):
    if not s:
        return default
    s = s.replace(',', '.').replace('−', '-').replace('±', '+')
    m = re.search('[-+]?\\d+(?:\\.\\d+)?', s)
    return float(m.group(0)) if m else default

def collect(module, doc2d, use_hidden=False, warnings=None):
    dims = []
    geoms = {}
    warnings=warnings if warnings is not None else []
    views = doc2d.ViewsAndLayersManager.Views
    for i in range(views.Count):
        view = views.View(i)
        name = get(view, 'Name', '') or 'Вид %d' % i
        try:
            sym = module.ISymbols2DContainer(view)
        except Exception as exc:
            warnings.append('%s: не прочитан контейнер размеров.'%name)
            J.failure('Пропущены размеры вида',exc,view=name)
            continue
        geoms[name] = Geometry.from_view(module, view, use_hidden)
        for coll_name, item_name, src_kind in (('LineDimensions', 'LineDimension', 'line'), ('BreakLineDimensions', 'BreakLineDimension', 'line'), ('DiametralDimensions', 'DiametralDimension', 'diam'), ('RadialDimensions', 'RadialDimension', 'rad'), ('BreakRadialDimensions', 'BreakRadialDimension', 'rad'), ('AngleDimensions', 'AngleDimension', 'angle'), ('ArcDimensions', 'ArcDimension', 'arc'), ('HeightDimensions', 'HeightDimension', 'line')):
            try:
                coll = getattr(sym, coll_name)
                n = coll.Count
            except Exception as exc:
                warnings.append('%s: недоступна коллекция %s.'%(name,coll_name))
                J.failure('Коллекция размеров недоступна',exc,'WARN',view=name,collection=coll_name)
                continue
            for k in range(n):
                try:
                    obj = getattr(coll, item_name)(k)
                except Exception:
                    try:
                        obj = coll.Item(k)
                    except Exception as exc:
                        warnings.append('%s: не прочитан объект %s[%d].'%(name,coll_name,k))
                        J.failure('Объект размера пропущен',exc,view=name,collection=coll_name,index=k)
                        continue
                try:
                    d = read_dimension(module, obj, src_kind, name)
                    if d is not None and not math.isfinite(d.value):raise ValueError('Номинал размера не является конечным числом.')
                except Exception as exc:
                    warnings.append('%s: не прочитано значение %s[%d].'%(name,coll_name,k))
                    J.failure('Значение размера пропущено',exc,view=name,collection=coll_name,index=k)
                    continue
                if d is None:warnings.append('%s: не прочитан интерфейс %s[%d].'%(name,coll_name,k))
                if d is not None and abs(d.value) > EPS:
                    dims.append(d)
                    J.event('Прочитан размер',view=name,collection=coll_name,index=k,
                            dimension={field:getattr(d,field) for field in d.__slots__})
    J.event('Чтение размеров завершено',count=len(dims),warnings=warnings)
    return (dims, geoms)

def classify_diameters(dims, geoms, model_diams=None):
    for d in dims:
        if d.manual or d.kind not in (KIND_OUTER, KIND_INNER):
            continue
        m = RE_FIT.match(d.fit) if d.fit and (d.src == SRC_DRAWING or d.manual_tol) else None
        if m:
            letters = m.group(1)
            d.kind = KIND_INNER if letters[0].isupper() else KIND_OUTER
            d.reason = 'по квалитету %s' % d.fit
            continue
        if model_diams:
            by_model = _model_lookup(model_diams, d.value)
            if by_model:
                d.kind = KIND_INNER if by_model == 'отверстие' else KIND_OUTER
                d.reason = 'по 3D-модели (%s)' % by_model
                continue
        g = geoms.get(d.view)
        if g and getattr(g, 'profile_ok', False) and _outer_at_anchors(d, g):
            d.kind = KIND_OUTER
            d.reason = 'наружный контур у точек привязки'
            continue
        d.kind = KIND_OUTER
        why = getattr(g, 'profile_why', '') if g else 'вид не прочитан'
        if model_diams:
            why = 'в модели нет такого Ø; ' + (why or '')
        d.reason = 'проверить — %s' % (why or 'геометрия не применима')

def diameter_uncertain(d):
    return (d.kind in (KIND_OUTER, KIND_INNER) and not d.manual
            and d.reason.startswith('проверить'))


def _outer_at_anchors(d, g):
    # Confirm only a diameter across a horizontal axial profile. Other views
    # remain unresolved; a larger nearby outline never proves a hole.
    if d.anchors is None or g.axis_y is None:
        return False
    x1, y1, x2, y2 = d.anchors
    radius = abs(d.value) / 2
    tol = 0.01
    if abs(x1-x2) > tol or abs((y1+y2)/2-g.axis_y) > tol:
        return False
    if any(abs(abs(y-g.axis_y)-radius) > tol for y in (y1,y2)):
        return False
    for offset in (-0.02, 0.02):
        x = (x1+x2)/2 + offset
        ys = []
        for a,b,c,e in g.segments:
            if abs(c-a) < 1e-9 or not min(a,c) < x < max(a,c):
                continue
            ys.append(b+(e-b)*(x-a)/(c-a)-g.axis_y)
        if ys and abs(min(ys)+radius) <= tol and abs(max(ys)-radius) <= tol:
            return True
    return False


def _model_lookup(model_diams, value, tol=0.05):
    if not model_diams or not value:
        return ''
    best, best_diff = ('', tol)
    for dia, kind in model_diams.items():
        diff = abs(dia - abs(float(value)))
        if diff <= best_diff:
            best, best_diff = (kind, diff)
    return '' if best in ('?', '') else best

def detect_chamfers(dims, chamfer_max=3.0, pair_max_dist=8.0):
    return

def assign_tolerances(dims, cls='m', linear_mode='gost'):
    for d in dims:
        if d.src == SRC_DRAWING or d.manual_tol or d.limit:
            continue
        d.note = ''
        if diameter_uncertain(d):
            d.fit = ''; d.hi = d.lo = None
            d.note = 'Уточните: вал или отверстие'
            continue
        if d.kind == KIND_OUTER:
            d.fit = 'h14'
            d.hi, d.lo = T.h14_shaft(d.value)
        elif d.kind == KIND_INNER:
            d.fit = 'H14'
            d.hi, d.lo = T.H14_hole(d.value)
        elif d.kind == KIND_CHAMFER:
            t = T.gost_chamfer(d.value, cls)
            if t is not None:
                d.hi, d.lo = (+t, -t)
                d.note = (d.note + ' ' if d.note else '') + 'ГОСТ 30893.1-%s, фаска' % cls
        elif d.kind == KIND_RADIUS:
            t = T.gost_chamfer(d.value, cls)
            if t is not None:
                d.hi, d.lo = (+t, -t)
                d.note = (d.note + ' ' if d.note else '') + 'ГОСТ 30893.1-%s, радиус' % cls
        elif d.kind == KIND_ANGLE:
            side = d.short_side
            if not side or side <= 0:
                d.hi = d.lo = None
                d.note = 'Угловой допуск: задайте вручную (не прочитана короткая сторона)'
                continue
            t = T.gost_angular(side, cls)
            if t is not None:
                d.hi, d.lo = (+t, -t)
                d.note = (d.note + ' ' if d.note else '') + 'ГОСТ 30893.1-%s, угол' % cls
        elif d.kind == KIND_THREAD:
            d.note = (d.note + ' ' if d.note else '') + 'резьба — допуск задать вручную'
        elif linear_mode == 'it14':
            d.hi, d.lo = T.js14(d.value)
            d.note = (d.note + ' ' if d.note else '') + '±IT14/2'
        else:
            t = T.gost_linear(d.value, cls)
            if t is None:
                d.note = (d.note + ' ' if d.note else '') + 'ГОСТ 30893.1 не нормирует — задать вручную'
            else:
                d.hi, d.lo = (+t, -t)
                d.note = (d.note + ' ' if d.note else '') + 'ГОСТ 30893.1-%s' % cls

def _side_from_note(note):
    m = re.search('короткая сторона ([\\d.]+)', note or '')
    return float(m.group(1)) if m else None
_DEV_EPS = 1e-09

def dedup(dims, per_view=False):

    def _is_vynosnoy(view_name):
        return bool(view_name) and view_name.startswith('Выносной элемент')
    seen, out = (set(), [])
    for d in dims:
        if d.kind in (KIND_ROUGHNESS, KIND_FORM_TOL):
            key = (d.kind, d.raw_text, d.view)
        else:
            key = (d.kind, round(d.value, 4), d.fit, round(d.hi or 0, 4), round(d.lo or 0, 4), d.count, d.limit, round(d.chamfer_angle, 2) if d.chamfer_angle is not None else None)
            if _is_vynosnoy(d.view):
                key = (d.view,) + key
        if per_view:
            key = (d.view,) + key
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out
_VIEW_MAIN_ORDER = {'Главный вид': 0, 'Вид справа': 1, 'Вид слева': 2, 'Вид сверху': 3, 'Вид снизу': 4, 'Вид сзади': 5}
_VIEW_GROUP_ORDER = {'Разрез': 0, 'Сечение': 1, 'Выносной элемент': 2}
_RE_VIEW_GROUP = re.compile('^(Разрез|Сечение|Выносной элемент)\\b\\s*(.*)$')
RE_GOST_CLASS = re.compile('30893\\.?1[^0-9a-zA-Zа-яёА-ЯЁ]{0,10}([fmcvFMCV])\\b')
RE_IT14 = re.compile('(?:\\u00b1|\\+\\-|\\+/-)?\\s*IT\\s*14\\s*/\\s*2', re.I)
RE_H14 = re.compile('\\bH\\s*14\\b')
RE_h14 = re.compile('\\bh\\s*14\\b')
DEFAULT_TT_FALLBACK = ['29...35,5 HRC.', 'Общие допуски по ГОСТ 30893.1: H14, h14, ± IT14/2', 'ГОСТ 30893.2 - K', '*Размеры для справок.', '**Размеры обеспечиваются инструментом.', '***Размеры по чертежу НМРТ.302615.G001.', 'Острые кромки притупить фаской 0,3 45.', 'Неуказанные радиуса R0,3 max.', 'Покрытие Ц9.хр ГОСТ 9.306-85.', 'Деталь после обработки продуть сжатым воздухом для удаления стружки. Заусенцев и вмятин на детали не допускается.']
RE_FOOTNOTE_LINE = re.compile('^(\\*+)\\s*(.+)$')
RE_TOL_BASE_LETTER = re.compile('\\^\\(#1~([^)]+)\\)')
TOL_SIGN_NAMES = {17: 'плоскостность (предположительно - см. SIGN_TO_DIALOG в fill_oktk_auto.py, сверьте глазами при первом использовании)', 19: 'симметричность (предположительно - см. SIGN_TO_DIALOG в fill_oktk_auto.py, сверьте глазами при первом использовании)', 22: 'круглость', 24: 'параллельность', 25: 'перпендикулярность', 26: 'соосность (концентричность)', 27: 'позиционный допуск', 28: 'радиальное биение', 29: 'полное биение', 20: 'профиль поверхности (не проверено)', 21: 'профиль линии (не проверено)', 23: 'цилиндричность (не проверено)'}
ROUGHNESS_SIGN_CODE = '@171~'
_ROUGH_VALUE_RE = re.compile('(\\d+(?:[.,]\\d+)?)')
TOL_FRAME_CODE = '@80~'


def read_view_layout(doc2d):
    out = []
    views = doc2d.ViewsAndLayersManager.Views
    for i in range(views.Count):
        view = views.View(i)
        name = get(view, 'Name', '') or 'Вид %d' % i
        x = get(view, 'X', None)
        y = get(view, 'Y', None)
        out.append((name, x, y))
    return out

def classify_view_roles(view_list, axis_tol=5.0):
    roles = {}
    main = None
    for name, x, y in view_list:
        if name.startswith(('Разрез', 'Сечение', 'Выносной элемент')):
            roles[name] = name
        elif name.startswith(('Слева', 'Справа', 'Сверху', 'Снизу', 'Сзади', 'Вид слева', 'Вид справа', 'Вид сверху', 'Вид снизу', 'Вид сзади')):
            direction = re.search(r'(слева|справа|сверху|снизу|сзади)', name, re.I).group(1).lower()
            roles[name] = 'Вид ' + direction
        elif name.startswith('Системный вид'):
            roles[name] = name
        elif not name.startswith('Проекционный'):
            if main is None and x is not None and (y is not None):
                main = (name, x, y)
                roles[name] = 'Главный вид'
            else:
                roles[name] = name
        else:
            roles[name] = None
    if main is not None:
        _, mx, my = main
        nearest = {}
        pending = []
        for name, x, y in view_list:
            if roles.get(name) is not None:
                continue
            if x is None or y is None:
                roles[name] = name
                continue
            dx, dy = (x - mx, y - my)
            if abs(dy) <= axis_tol and abs(dx) > axis_tol:
                label = 'Вид слева' if dx > 0 else 'Вид справа'
                dist = abs(dx)
            elif abs(dx) <= axis_tol and abs(dy) > axis_tol:
                label = 'Вид сверху' if dy < 0 else 'Вид снизу'
                dist = abs(dy)
            else:
                roles[name] = name
                continue
            pending.append((name, label, dist))
            if label not in nearest or dist < nearest[label][1]:
                nearest[label] = (name, dist)
        by_label = {}
        for name, label, dist in pending:
            by_label.setdefault(label, []).append((name, dist))
        rear_name = {}
        for label in ('Вид слева', 'Вид справа'):
            cands = by_label.get(label)
            if cands and len(cands) == 2:
                cands_sorted = sorted(cands, key=lambda p: p[1])
                rear_name[label] = cands_sorted[1][0]
        for name, label, dist in pending:
            if nearest[label][0] == name:
                roles[name] = label
            else:
                roles[name] = name
    for name, x, y in view_list:
        if roles.get(name) is None:
            roles[name] = name
    return roles

def apply_view_roles(dims, module, doc2d):
    try:
        view_list = read_view_layout(doc2d)
    except Exception:
        return dims
    roles = classify_view_roles(view_list)
    for d in dims:
        label = roles.get(d.view)
        if label:
            d.view_label = label
    return dims

def view_sort_key(label):
    label = label or ''
    if label in _VIEW_MAIN_ORDER:
        return (0, _VIEW_MAIN_ORDER[label], '')
    m = _RE_VIEW_GROUP.match(label)
    if m:
        kind, rest = m.groups()
        return (1, _VIEW_GROUP_ORDER.get(kind, 9), rest)
    return (2, 0, label)
