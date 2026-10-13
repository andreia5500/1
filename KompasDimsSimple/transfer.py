"""Минимальный перенос в построчную ОКТК из kompas_dims_app.zip.
Только явно выбранный лист/строки; API5 для записи, API7 для проверки.
"""
import copy
import json
import os
import re
from pathlib import Path
from datetime import datetime
import kompas_dims as K
import sheet_names as N
import debug_log as J
from api5_base import _connect5, _text_item_param

PARAM_IDS = {18: tuple(range(6125, 6138)), 20: tuple(range(6091, 6108))}


def display(s):
    framed = s.startswith('@80~')
    if framed:
        s = s[4:]
    for code, glyph in {'@1~':'°', '@2~':'Ø', '@4~':'×', '@22~':'○', '@24~':'∥',
                        '@25~':'⊥', '@26~':'◎', '@171~':'√', '@172~':'√', '@364~':'√'}.items():
        s = s.replace(code, glyph)
    s = re.sub(r'\$m([^;$]*);([^$]*)\$', lambda m: '[' + m[1] + (' / ' + m[2] if m[2] else '') + ']', s)
    return '[' + s + ']' if framed else s


def safe(s):
    return s.replace('Ø', '@2~').replace('⌀', '@2~').replace('∅', '@2~').replace('×', '@4~').replace('−', '-')


def pack(dims, limit=30):
    """Each source view gets its own heading. Never merge different views."""
    groups = {}
    for d in dims:
        groups.setdefault(d.view, []).append(d)
    dims = [d for group in sorted(groups.values(), key=lambda ds: K.view_sort_key(ds[0].view_label or ds[0].view)) for d in group]
    lines, current, last_view = [], '', None
    for d in dims:
        if last_view != d.view:
            if current:
                lines.append(current)
                current = ''
            lines.append((d.view_label or d.view or 'Вид без названия').rstrip(':') + ':')
        if d.kind == K.KIND_ANGLE and d.hi is None:
            raise ValueError('У размера %s не задан угловой допуск. Двойной щелчок по размеру — правка.' % display(d.column_text()))
        dd = copy.copy(d)
        if dd.src == K.SRC_DEFAULT and not dd.manual_tol:
            dd.fit = ''
        s = safe(dd.column_text())
        proposed = current + '; ' + s if current else s
        if current and (d.view != last_view or len(display(proposed)) > limit):
            lines.append(current)
            current = s
        else:
            current = proposed
        last_view = d.view
    if current:
        lines.append(current)
    return lines


def path_key(path):
    return os.path.normcase(os.path.abspath(path))


def open_doc(module, app, path):
    path = os.path.abspath(path)
    docs = app.Documents
    for i in range(docs.Count):
        d = docs.Item(i)
        if K.get(d, 'PathName', '') and path_key(d.PathName) == path_key(path):
            return d
    d = docs.Open(path, True, False)
    if d is None:
        raise ValueError('КОМПАС не открыл документ: ' + path)
    return d


def sheet_at(sheets, index):
    for method in ('Item', 'LayoutSheet'):
        try:
            return getattr(sheets, method)(index)
        except Exception:
            pass
    raise ValueError('Не удалось прочитать выбранный лист.')


def sheet_list(path):
    module, app = K.connect()
    doc = open_doc(module, app, path)
    sheets = doc.LayoutSheets
    # Explicit selection: style alone does not identify a control card.
    return N.describe(doc,path,sheet_at)


def read_cell(stamp, cid, module):
    t = stamp.Text(cid)
    raw = t.Str or ''
    count = int(t.Count)
    font = {}
    for i in range(count):
        line = t.TextLine(i)
        for j in range(line.Count):
            item = line.TextItem(j)
            if int(K.get(item, 'ItemType', 0)) != 0 or not K.get(item, 'Str', '').strip():
                continue
            ft = module.ITextFont(item)
            font = {name: getattr(ft, name) for name in ('FontName', 'Height', 'WidthFactor', 'Italic', 'Bold', 'Underline', 'Color')}
            break
        if font:
            break
    return {'id': cid, 'text': raw, 'font': font, 'count': count}


def read_rows(path, sheet):
    module, app = K.connect()
    doc = open_doc(module, app, path)
    sh = sheet_at(doc.LayoutSheets, sheet)
    style = int(sh.LayoutStyleNumber)
    if style not in PARAM_IDS:
        raise ValueError('Оформление %s пока не поддерживается. Эта версия предназначена для построчных карт 18/20 из присланной программы.' % style)
    rows = [read_cell(sh.Stamp, cid, module) for cid in PARAM_IDS[style]]
    if any(r['count'] > 1 for r in rows):
        raise ValueError('Вместо отдельных строк обнаружена многострочная графа. Схема этой карты отличается; перенос остановлен.')
    return rows


def check_result(result, operation):
    J.event('Результат команды',operation_name=operation,result=result)
    if result is not None and result == 0:
        raise RuntimeError('КОМПАС отказал: ' + operation)


def set_font(param, font):
    if not font:
        return
    ft = param.GetItemFont()
    def put(name, value):
        mapping = getattr(ft, '_prop_map_put_', {})
        key = next((k for k in mapping if k.casefold() == name.casefold()), name)
        setattr(ft, key, value)
    for old, new in [('FontName','fontName'), ('Height','height'), ('WidthFactor','ksu'), ('Color','color')]:
        if old in font:
            put(new, font[old])
    # SDK textflags: explicit ON/OFF, never fraction/index low bits.
    flags = int(K.get(ft, 'bitvector', 0))
    for name, on, off in [('Italic', 0x40, 0x80), ('Bold', 0x100, 0x200), ('Underline', 0x400, 0x800)]:
        if name in font:
            flags = (flags & ~(on | off)) | (on if font[name] else off)
    put('bitvector', flags)
    check_result(param.SetItemFont(ft), 'шрифт')


def write_one(doc5, kompas5, sheet, cid, text, font):
    if cid <= 0:
        raise ValueError('Некорректный номер графы.')
    param = _text_item_param(kompas5)
    param.Init()
    param.type = 0
    param.s = safe(text) if text else ' '
    J.event('Запись строки карты',sheet=sheet+1,column=cid,text=param.s,font=font)
    set_font(param, font)
    stamp = doc5.GetStampEx(sheet + 1)
    check_result(stamp.ksOpenStamp(), 'открытие основной надписи')
    try:
        check_result(stamp.ksColumnNumber(cid), 'выбор графы %s' % cid)
        check_result(stamp.ksTextLine(param), 'запись графы %s' % cid)
    finally:
        check_result(stamp.ksCloseStamp(), 'закрытие основной надписи')


def backup_folder():
    p = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'KompasDimsSimple'
    p.mkdir(parents=True, exist_ok=True)
    return p


def transfer(path, sheet, start, expected, lines):
    if not lines:
        raise ValueError('Не выбраны размеры.')
    if not 0 <= start < len(expected) or start + len(lines) > len(expected):
        raise ValueError('На выбранном листе не хватает строк. Выберите меньше размеров.')
    module, app = K.connect()
    doc = open_doc(module, app, path)
    sh = sheet_at(doc.LayoutSheets, sheet)
    if tuple(r['id'] for r in expected) != PARAM_IDS.get(int(sh.LayoutStyleNumber)):
        raise ValueError('Оформление листа изменилось. Откройте перенос заново.')
    indices = range(start, start + len(lines))
    before = [read_cell(sh.Stamp, expected[i]['id'], module) for i in indices]
    for i, rec in zip(indices, before):
        if rec != expected[i]:
            raise ValueError('Графа изменилась после просмотра. Закройте окно переноса и откройте снова.')
    _, kompas5 = _connect5()
    # Tie API5 to its own API7 application before obtaining ActiveDocument2D.
    app5 = module.IApplication(kompas5.ksGetApplication7())
    doc5view = open_doc(module, app5, path)
    doc5view.Active = True
    active = app5.ActiveDocument
    if active is None or path_key(active.PathName) != path_key(path):
        raise ValueError('Не удалось сделать выбранный ТП активным. Запись не начата.')
    sh = sheet_at(doc5view.LayoutSheets, sheet)
    for rec in before:
        if read_cell(sh.Stamp, rec['id'], module) != rec:
            raise ValueError('API5 подключён к другой версии открытого ТП. Запись не начата.')
    doc5 = kompas5.ActiveDocument2D()
    fallback_font = next((r['font'] for r in expected if r['font']), {})
    backup = backup_folder() / ('before_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    backup.write_text(json.dumps({'path': path, 'sheet': sheet+1, 'before': before, 'after': lines}, ensure_ascii=False, indent=2), encoding='utf-8')
    touched = []
    try:
        for rec, line in zip(before, lines):
            # Active document could have changed while processing previous rows.
            if path_key(app5.ActiveDocument.PathName) != path_key(path):
                raise RuntimeError('Активный документ изменился во время переноса.')
            touched.append(rec)
            write_one(doc5, kompas5, sheet, rec['id'], line, rec['font'] or fallback_font)
            actual = sh.Stamp.Text(rec['id']).Str or ''
            if actual.strip() != safe(line).strip():
                raise RuntimeError('Запись графы %s не подтверждена: ожидалось %r, прочитано %r' % (rec['id'], safe(line), actual))
    except Exception as exc:
        # Do not claim an exact rollback by reconstructing complex native text.
        raise RuntimeError('Перенос остановлен. Некоторые строки могли измениться. '
                           'Закройте ТП БЕЗ сохранения, чтобы вернуться к сохранённому файлу.\n'
                           'Резервная запись: %s\n%s' % (backup, exc)) from exc
    return len(lines)
