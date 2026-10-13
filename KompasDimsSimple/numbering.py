"""Номер листа внутри документа ТП (ячейка сверху справа на листах-продолжениях).

Документ начинается с главного листа (свой номер выводит оформление) или с
листа другого типа. Номера граф определены по ТП пользователя 13.10.2026:
CDW-записи 0x4000+0 (МК/МК ВО — продолжение) и 0x4000+1813 (КЭ ЧПУ —
инструмент/эскиз).
"""
from datetime import datetime
import json
import kompas_dims as K
import transfer as X
import sheet_names as N
import tooling as V
import debug_log as J

# Оформления листов-продолжений и графа номера листа в документе.
PAGE_CELL = {22: 0, 24: 0, 5: 1813, 19: 1813}
# ОК ТК — продолжение: графа номера пока неизвестна (в присланном ТП не заполнена).
CONTINUATION = set(PAGE_CELL) | {20}


def doc_type(name):
    return name.split(' — ')[0].strip()


def plan(descriptions):
    """[(index, style, name)] -> строки плана с номером листа в документе."""
    rows = []
    doc = 0
    current = None
    page = 0
    for index, style, name in descriptions:
        kind = doc_type(name)
        unknown = name == 'Название не определено'
        if unknown or style not in CONTINUATION or kind != current:
            doc += 1
            page = 1
            current = None if unknown else kind
        else:
            page += 1
        cell = PAGE_CELL.get(style)
        if unknown:
            action = 'лист не распознан — пропущен'
            cell = None
        elif style not in CONTINUATION:
            action = 'главный лист — номер выводит оформление'
            cell = None
        elif cell is None:
            action = 'графа номера этого оформления неизвестна — впишите вручную'
        else:
            action = 'записать'
        rows.append(dict(index=index, style=style, name=name, doc=doc, page=page, cell=cell, action=action))
    return rows


def read(path):
    module, app = K.connect()
    doc = X.open_doc(module, app, path)
    desc = N.describe(doc, path, X.sheet_at)
    rows = plan(desc)
    for row in rows:
        row['old'] = None
        if row['cell'] is None:
            continue
        sh = X.sheet_at(doc.LayoutSheets, row['index'])
        row['old'] = X.read_cell(sh.Stamp, row['cell'], module)
        if row['old']['text'].strip() == str(row['page']):
            row['action'] = 'уже верно'
    J.event('План нумерации листов', path=path, rows=rows)
    return dict(path=path, count=int(doc.LayoutSheets.Count), rows=rows)


def sample_fonts(rows):
    """Шрифт уже заполненной графы номера того же оформления."""
    fonts = {}
    for row in rows:
        old = row.get('old')
        if old and old['text'].strip() and old['font']:
            fonts.setdefault((row['style'], row['cell']), old['font'])
    return fonts


def write(path, data):
    from sketch import context
    module, mod5, k5, app, doc, doc5 = context(path)
    if int(doc.LayoutSheets.Count) != data['count']:
        raise ValueError('Состав листов изменился. Перечитайте ТП.')
    todo = [r for r in data['rows'] if r['action'] == 'записать']
    for row in todo:
        sh = X.sheet_at(doc.LayoutSheets, row['index'])
        if X.read_cell(sh.Stamp, row['cell'], module) != row['old']:
            raise ValueError('Лист %d изменился после просмотра. Перечитайте ТП.' % (row['index'] + 1))
    fonts = sample_fonts(data['rows'])
    backup = X.backup_folder() / ('numbering_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    backup.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    touched = []
    unchecked = []
    try:
        for row in todo:
            V.C.require_active(app, path)
            index, cid, text = row['index'], row['cell'], str(row['page'])
            font = row['old']['font'] or fonts.get((row['style'], cid), {})
            touched.append(row)
            X.write_one(doc5, k5, index, cid, text, font)
            sh = X.sheet_at(doc.LayoutSheets, index)
            actual = X.read_cell(sh.Stamp, cid, module)
            J.event('Обратное чтение номера листа', sheet=index + 1, column=cid, actual=actual)
            if actual['text'].strip() != text:
                raise RuntimeError('Лист %d, графа %d: ожидалось %r, прочитано %r.' % (index + 1, cid, text, actual['text']))
            ids, complete = V.column_scan(sh.Stamp)
            if cid not in ids:
                if complete:
                    raise RuntimeError('Лист %d: графы %d нет в оформлении листа — номер не будет виден.' % (index + 1, cid))
                unchecked.append(index + 1)
        V.refresh_document(module, app, doc, path)
    except Exception as exc:
        errors = []
        for row in reversed(touched):
            try:
                X.write_one(doc5, k5, row['index'], row['cell'], row['old']['text'], row['old']['font'])
                back = X.read_cell(X.sheet_at(doc.LayoutSheets, row['index']).Stamp, row['cell'], module)
                if back['text'].strip() != row['old']['text'].strip():
                    raise RuntimeError('прочитано %r' % back['text'])
            except Exception as err:
                errors.append('Лист %d: %s' % (row['index'] + 1, err))
                J.failure('Ошибка восстановления номера листа', err, sheet=row['index'] + 1)
        status = 'Прежние номера восстановлены.' if not errors else 'Восстановление не подтверждено. Закройте ТП без сохранения.'
        raise RuntimeError('Нумерация остановлена. %s\nРезервная запись: %s\n%s%s' % (
            status, backup, exc, '\n\n' + '\n'.join(errors) if errors else '')) from exc
    J.event('Номера листов записаны', path=path, written=[r['index'] + 1 for r in todo], unchecked=unchecked)
    note = ''
    if unchecked:
        note = 'КОМПАС не выдал полный перечень граф листов %s — проверьте, что номер виден.' % ', '.join(map(str, unchecked))
    return len(todo), note
