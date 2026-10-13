"""Шероховатость и геометрические допуски. Надписи и ТТ не читаются."""
import re
import kompas_dims as K
import debug_log as J

ROUGH_SIGNS = {0: '@171~', 1: '@172~', 2: '@364~'}


def record(view, kind, text, obj=None):
    d = K.Dim()
    d.view = view
    d.kind = d.src_kind = kind
    d.raw_text = text
    d.src = K.SRC_DRAWING
    d.manual = True
    d.x, d.y = K.get(obj, 'X0'), K.get(obj, 'Y0')
    return d


def rough_record(view, rp, obj=None, general=False):
    sign = int(rp.SignType)
    if sign not in ROUGH_SIGNS:
        raise ValueError('Неизвестный тип знака шероховатости: %s' % sign)
    text = K.txt_str(rp.Text if general else rp.RoughParamText)
    result = ROUGH_SIGNS[sign] + text
    if general:
        if rp.AddSign:
            result += ' (' + ROUGH_SIGNS[0] + ')'
    else:
        for prop, label in (('ProcessText', ''), ('BaseLengthText', 'Базовая длина: '), ('TrendText', 'Направление: ')):
            val = K.txt_str(getattr(rp, prop))
            if val:
                result += '; ' + label + val
        if rp.ProcessingByContour:
            result += '; по контуру'
    d = record(view, K.KIND_ROUGHNESS, result, obj)
    m = re.search(r'\d+(?:[.,]\d+)?', text)
    d.value = float(m[0].replace(',', '.')) if m else 0
    return d


def base_text(value):
    text = K.txt_str(value)
    # Ссылки на базу исходного CDW нельзя перенести в другой документ.
    if text.startswith('^(#1~'):
        match = re.match(r'\^\(#1~([^)]*)\)', text)
        if not match:
            raise ValueError('Не удалось раскрыть ссылку на базу: ' + text)
        return match[1]
    if '^(' in text:
        raise ValueError('Неизвестная ссылка в обозначении базы: ' + text)
    return text


def form_records(module, view, tp, obj=None):
    """Текст ячеек содержит родные спецкоды, включая модификаторы баз.

    Один допуск в одной строке: код рамки @80~ действует до конца строки.
    Несколько рамок в одной строке в API5 становятся вложенными.
    """
    sign = int(tp.Sign)
    table = K.get(tp, 'Table')
    texts = []
    if table is not None:
        for r in range(int(table.RowsCount)):
            cells = []
            for c in range(int(table.ColumnsCount)):
                cell = table.Cell(r, c)
                if not hasattr(cell, 'Str'):
                    cell = module.ITextLine(cell)
                cells.append(base_text(cell))
            if any(cells):
                texts.append('@80~' + ' | '.join(cells).rstrip(' |'))
    if not texts:
        # Старые версии API: безопасный вариант только без модификаторов.
        prefix = int(tp.PrefixSign)
        if prefix not in (0, 1, 2) or any(int(getattr(tp, a)) for a in ('SuffixSign', 'BaseSign1', 'BaseSign2')):
            raise ValueError('Сложный допуск: не удалось прочитать таблицу с модификаторами')
        parts = ['@%d~' % sign, {0: '', 1: 'R', 2: '@2~'}[prefix] + K.txt_str(tp.Value)]
        parts += [base_text(tp.BaseValue1), base_text(tp.BaseValue2)]
        texts = ['@80~' + ' | '.join(p for p in parts if p)]
    result = []
    for text in texts:
        d = record(view, K.KIND_FORM_TOL, text, obj)
        d.tol_sign = sign
        result.append(d)
    return result


def read(module, doc2d):
    out, warnings = [], []
    views = doc2d.ViewsAndLayersManager.Views
    for i in range(views.Count):
        view = views.View(i)
        name = K.get(view, 'Name', '') or 'Вид %d' % i
        try:
            sym = module.ISymbols2DContainer(view)
        except Exception as exc:
            J.failure('Не прочитан контейнер обозначений',exc,view=name)
            warnings.append('%s: обозначения не прочитаны: %s' % (name, exc))
            continue
        for collname, getter, kind in (('Roughs', 'Rough', K.KIND_ROUGHNESS), ('Tolerances', 'Tolerance', K.KIND_FORM_TOL)):
            try:
                coll = getattr(sym, collname)
                count = int(coll.Count)
            except Exception as exc:
                J.failure('Недоступна коллекция обозначений',exc,'WARN',view=name,collection=collname)
                warnings.append('%s: %s не прочитаны: %s' % (name, kind, exc))
                continue
            for j in range(count):
                try:
                    obj = getattr(coll, getter)(j)
                    if kind == K.KIND_ROUGHNESS:
                        out.append(rough_record(name, module.IRoughParams(obj), obj))
                    else:
                        out.extend(form_records(module, name, module.IToleranceParam(obj), obj))
                except Exception as exc:
                    J.failure('Обозначение не прочитано',exc,view=name,collection=collname,index=j)
                    d = record(name, kind, '[Не прочитано: %s №%d]' % (kind, j + 1))
                    d.export_error = d.note = str(exc)
                    out.append(d)
                    warnings.append('%s: %s: %s' % (name, d.raw_text, exc))
    drawing = module.IDrawingDocument(doc2d)
    try:
        sr = drawing.SpecRough
        if sr.IsCreated:
            out.append(rough_record('Неуказанная шероховатость', sr, general=True))
    except Exception as exc:
        J.failure('Не прочитана общая шероховатость',exc)
        warnings.append('Неуказанная шероховатость не прочитана: %s' % exc)
    return out, warnings
