"""Группировка: исходный вид → конкретный меритель → параметры."""
import copy
import re
from collections import OrderedDict
import kompas_dims as K
import instruments as I


def visual_len(text):
    text = re.sub(r'@\d+~', 'X', text)
    text = re.sub(r'\$m([^;$]*);([^$]*)\$', lambda m: 'X' * max(len(m[1]), len(m[2])), text)
    return len(text)


def wrap(text, limit):
    # Спецкоды и индексы — неделимые токены; дробить их нельзя.
    tokens = re.findall(r'\$m[^$]*\$|@\d+~|\S+|[ \t]+', text)
    lines, current = [], ''
    for token in tokens:
        if current and not token.isspace() and visual_len(current + token) > limit:
            lines.append(current.rstrip())
            current = ''
        current += token if current else token.lstrip()
    if current.strip():
        lines.append(current.rstrip())
    return lines or ['']


def groups(dims, limit=30):
    views = OrderedDict()
    for d in dims:
        if d.kind in ('требование', 'надпись'):
            continue
        if d.export_error:
            raise ValueError(d.raw_text + '\n' + d.export_error)
        if K.diameter_uncertain(d):
            raise ValueError('Уточните тип диаметра: ' + d.column_text())
        if d.kind == K.KIND_ANGLE and d.hi is None:
            raise ValueError('Задайте угловой допуск: ' + d.column_text())
        views.setdefault(d.view, []).append(d)
    result = []
    def order(ds):
        label = ds[0].view_label or ds[0].view
        if label == 'Неуказанная шероховатость':
            return (90, 0, label)
        return K.view_sort_key(label)
    for ds in sorted(views.values(), key=order):
        tools = OrderedDict()
        for d in ds:
            tools.setdefault(d.instrument, []).append(d)
        rank = {name: i for i, name in enumerate(I.CATALOG)}
        for tool, items in sorted(tools.items(), key=lambda kv: rank.get(kv[0], 10000)):
            lines, current = [], ''
            for d in items:
                dd = copy.copy(d)
                if dd.src == K.SRC_DEFAULT and not dd.manual_tol:
                    dd.fit = ''
                text = dd.column_text()
                special = d.kind in (K.KIND_FORM_TOL, K.KIND_ROUGHNESS)
                if special:
                    if current:
                        lines.append(current); current = ''
                    # Рамки и шероховатость составные: только отдельная строка.
                    lines.append(text)
                else:
                    proposed = current + '; ' + text if current else text
                    if current and visual_len(proposed) > limit:
                        lines.append(current); current = text
                    else:
                        current = proposed
            if current:
                lines.append(current)
            result.append(dict(view=ds[0].view, label=ds[0].view_label or ds[0].view,
                               instrument=tool, params=lines))
    return result


def empty_row():
    return dict(text='', instrument='', bold=False)


def paginate(groups, capacities, start=0, extra_capacity=None):
    """Пустая строка + заголовок всегда вместе с первой записью вида.

    На продолжении повторяются вид и название инструмента. Возвращаются
    только занятые строки; None в начале первой страницы — не изменять.
    """
    if not capacities or not 0 <= start < capacities[0]:
        raise ValueError('Некорректная начальная строка.')
    pages, page, view = [], [None] * start, None
    capacity = capacities[0]
    def advance():
        nonlocal page, view, capacity
        pages.append(page)
        index = len(pages)
        if index < len(capacities):
            capacity = capacities[index]
        elif extra_capacity:
            capacity = extra_capacity
        else:
            raise ValueError('Закончились листы карты контроля. Добавьте лист-продолжение с оформлением 20 в конец ТП.')
        page, view = [], None
    for group in groups:
        params = list(group['params'])
        tools = wrap(group['instrument'], 25) if group['instrument'] else ['']
        while params:
            header = view != group['view']
            # Разделитель предыдущего мерителя одновременно служит
            # пустой строкой перед следующим заголовком вида.
            has_blank = bool(page and page[-1] == empty_row())
            needed = ((1 if has_blank else 2) if header else 0) + max(1, len(tools))
            if capacity - len(page) < needed:
                if not page:
                    raise ValueError('Заголовок и меритель не помещаются на листе.')
                advance()
                continue
            if header:
                if not has_blank:
                    page.append(empty_row())
                page.append(dict(text=(group['label'] or 'Вид без названия').rstrip(':') + ':', instrument='', bold=True))
                view = group['view']
            take = min(len(params), capacity - len(page))
            chunk, params = params[:take], params[take:]
            for n in range(max(len(chunk), len(tools))):
                page.append(dict(text=chunk[n] if n < len(chunk) else '',
                                 instrument=tools[n] if n < len(tools) else '', bold=False))
            if params:
                advance()
        # После всей группы, включая многострочное название мерителя.
        # При заполненном листе разделителем служит начало следующего;
        # отдельный пустой лист ради разделителя не создаём.
        if len(page) < capacity:
            page.append(empty_row())
    if page:
        pages.append(page)
    return pages
