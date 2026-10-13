"""Просмотр и проверяемая запись блока карт, начиная с выбранного листа."""
import copy
import json
from datetime import datetime
import kompas_dims as K
import transfer as X
import layout as L
import sheet_names as N
import debug_log as J

INSTRUMENT_IDS = {18: tuple(range(6138, 6151)), 20: tuple(range(6108, 6125))}
VOLUME_IDS = {18: tuple(range(6151, 6164)), 20: tuple(range(6164, 6181))}
FORMAT_PROPS = ('Format', 'FormatHeight', 'FormatMultiplicity', 'FormatWidth', 'VerticalOrientation')


def signature(sh):
    return dict(style=int(sh.LayoutStyleNumber), library=str(sh.LayoutLibraryFileName),
                format={name: getattr(sh.Format, name) for name in FORMAT_PROPS})


def read_page(module, sh, index):
    style = int(sh.LayoutStyleNumber)
    rows = []
    for pid, iid, vid in zip(X.PARAM_IDS[style], INSTRUMENT_IDS[style], VOLUME_IDS[style]):
        p, inst = X.read_cell(sh.Stamp, pid, module), X.read_cell(sh.Stamp, iid, module)
        volume = X.read_cell(sh.Stamp, vid, module)
        if any(cell['count'] > 1 for cell in (p, inst, volume)):
            raise ValueError('Лист %d: графы отличаются от построчной карты 18/20.' % (index + 1))
        rows.append(dict(param=p, instrument=inst, volume=volume))
    return dict(index=index, signature=signature(sh), rows=rows)


def read_block(path, start_sheet):
    module, app = K.connect()
    doc = X.open_doc(module, app, path)
    sheets, pages = doc.LayoutSheets, []
    count = int(sheets.Count)
    descriptions=N.describe(doc,path,X.sheet_at)
    for index in range(start_sheet, count):
        sh = X.sheet_at(sheets, index)
        if int(sh.LayoutStyleNumber) not in X.PARAM_IDS or 'ОК ТК' not in descriptions[index][2]:
            break
        pages.append(read_page(module, sh, index))
    if not pages:
        raise ValueError('Выберите лист «ОК ТК — карта контроля». Если названия не определены, сохраните ТП в КОМПАСе и перечитайте его.')
    reference = next((p for p in reversed(pages) if p['signature']['style'] == 20), None)
    J.event('Прочитаны карты контроля',path=path,start_sheet=start_sheet+1,count=count,pages=pages)
    return dict(count=count, pages=pages,
                template=copy.deepcopy(reference) if reference and pages[-1]['index'] == count - 1 else None)


def plan(block, groups, start):
    template = block['template']
    contents = L.paginate(groups, [len(p['rows']) for p in block['pages']], start,
                          len(template['rows']) if template else None)
    result = []
    for i in range(max(len(contents), len(block['pages']))):
        new = i >= len(block['pages'])
        page = copy.deepcopy(template if new else block['pages'][i])
        page['index'] = block['pages'][0]['index'] + i
        page['new'] = new
        page['after'] = contents[i] if i < len(contents) else []
        page['after'] += [L.empty_row() for _ in range(len(page['rows']) - len(page['after']))]
        if new:
            for row in page['rows']:
                for cell in row.values():
                    cell.update(text='', count=0)
        result.append(page)
    return result


def assert_unchanged(module, doc, block):
    if int(doc.LayoutSheets.Count) != block['count']:
        raise ValueError('Число листов изменилось после просмотра. Откройте перенос заново.')
    for page in block['pages']:
        actual = read_page(module, X.sheet_at(doc.LayoutSheets, page['index']), page['index'])
        if actual != page:
            raise ValueError('Лист %d изменился после просмотра. Откройте перенос заново.' % (page['index'] + 1))


def require_active(app, path):
    active = app.ActiveDocument
    if active is None or X.path_key(active.PathName) != X.path_key(path):
        raise RuntimeError('Выбранный ТП не является активным. Перенос остановлен.')


def append_sheet(sheets, template):
    import pythoncom
    count = int(sheets.Count)
    new = sheets.Add()
    if new is None or int(sheets.Count) != count + 1:
        raise RuntimeError('КОМПАС не добавил лист-продолжение.')
    # Проверяем COM-идентичность, а не только одинаковый номер оформления.
    last = X.sheet_at(sheets, count)
    if new._oleobj_.QueryInterface(pythoncom.IID_IUnknown) != last._oleobj_.QueryInterface(pythoncom.IID_IUnknown):
        raise RuntimeError('Новый лист появился не в конце ТП. Запись не начата.')
    sig = template['signature']
    new.LayoutLibraryFileName = sig['library']
    new.LayoutStyleNumber = sig['style']
    fmt = new.Format
    for name, value in sig['format'].items():
        setattr(fmt, name, value)
    X.check_result(new.Update(), 'оформление нового листа')
    if signature(new) != sig:
        raise RuntimeError('Оформление нового листа отличается от образца.')
    return new


def write(path, block, pages):
    module, app = K.connect()
    assert_unchanged(module, X.open_doc(module, app, path), block)
    _, kompas5 = X._connect5()
    app5 = module.IApplication(kompas5.ksGetApplication7())
    doc = X.open_doc(module, app5, path)
    doc.Active = True
    require_active(app5, path)
    assert_unchanged(module, doc, block)
    doc5 = kompas5.ActiveDocument2D()
    backup = X.backup_folder() / ('cards_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    J.event('План переноса в карты контроля',path=path,active_path=app5.ActiveDocument.PathName,plan=pages,backup=str(backup))
    backup.write_text(json.dumps(dict(path=path, before=block, plan=pages), ensure_ascii=False, indent=2), encoding='utf-8')
    # Метаданные новой карты копируем только из выбранного продолжения.
    header = []
    if block['template'] and any(p['new'] for p in pages):
        ref = X.sheet_at(doc.LayoutSheets, block['template']['index'])
        header = [X.read_cell(ref.Stamp, cid, module) for cid in (2110, 1815)]
    written = 0
    try:
        for page in pages:
            require_active(app5, path)
            if page['new']:
                sh = append_sheet(doc.LayoutSheets, block['template'])
                for cell in header:
                    X.write_one(doc5, kompas5, page['index'], cell['id'], cell['text'], cell['font'])
            else:
                sh = X.sheet_at(doc.LayoutSheets, page['index'])
            fallback = {}
            for col in ('param', 'instrument'):
                fallback[col] = next((r[col]['font'] for r in page['rows'] if r[col]['font']), {})
                if not fallback[col]:
                    fallback[col] = next((r[col]['font'] for p in block['pages'] for r in p['rows'] if r[col]['font']), {})
            for before, after in zip(page['rows'], page['after']):
                if after is None:
                    continue
                for col, field in (('param', 'text'), ('instrument', 'instrument')):
                    require_active(app5, path)
                    cell, text = before[col], after[field]
                    if not page['new'] and not text and not cell['text'].strip():
                        continue
                    font = dict(cell['font'] or fallback[col])
                    font['Bold'] = after['bold'] if col == 'param' else False
                    width = L.visual_len(text)
                    if width > 30 and col == 'param':
                        font['WidthFactor'] = min(font.get('WidthFactor', 1), 30 / width)
                    X.write_one(doc5, kompas5, page['index'], cell['id'], text, font)
                    actual = X.read_cell(sh.Stamp, cell['id'], module)
                    J.event('Обратное чтение строки карты',sheet=page['index']+1,column=cell['id'],actual=actual)
                    if actual['text'].strip() != X.safe(text).strip():
                        raise RuntimeError('Лист %d, графа %d: запись не подтверждена: ожидалось %r, прочитано %r.'
                                           % (page['index'] + 1, cell['id'], X.safe(text), actual['text']))
                    if text and actual['font'] and actual['font']['Bold'] != font['Bold']:
                        raise RuntimeError('Лист %d: жирность шрифта не подтверждена.' % (page['index'] + 1))
                # Пустой разделитель действительно пуст во всех трёх графах.
                # Проценты содержательных строк не назначаем и не меняем.
                volume = before.get('volume')
                if volume and (after['bold'] or not (after['text'] or after['instrument'])) and volume['text'].strip():
                    require_active(app5, path)
                    X.write_one(doc5, kompas5, page['index'], volume['id'], '', volume['font'])
                    if X.read_cell(sh.Stamp, volume['id'], module)['text'].strip():
                        raise RuntimeError('Не удалось очистить объём контроля в пустой строке.')
                if after['text'] or after['instrument']:
                    written += 1
    except Exception as exc:
        raise RuntimeError('Перенос остановлен; часть строк или листов могла измениться. '
                           'Для возврата к сохранённому ТП закройте его БЕЗ сохранения.\n'
                           'Резервная запись: %s\n%s' % (backup, exc)) from exc
    return written
