"""Каталог из GRAPHIC.PMN (MENU 52) и instruments.py присланной программы."""
import json
import re
from pathlib import Path
import kompas_dims as K

CATALOG = json.loads(Path(__file__).with_name('instruments.json').read_text(encoding='utf-8'))
CALIPER = 'Штангенциркуль односторонний ШЦК-I-150'
MICROMETER = 'Микрометр МК-25 Mitutoyo'
MICROMETER_50 = 'Микрометр цифровой 25-50 мм серии 293 Mitutoyo'
PROFILOMETER = 'Профилометр Mitutoyo SJ210'
MANUAL = 'Выбрать меритель'


def tolerance_width(d):
    if d.hi is None or d.lo is None or d.hi <= d.lo:
        return None
    return d.hi - d.lo


def covers(d, lo, hi):
    """Прибор должен охватывать предельные размеры, не только номинал."""
    return lo <= d.value + (d.lo or 0) + 1e-9 and d.value + (d.hi or 0) <= hi + 1e-9


def suggest(d):
    if d.kind in (K.KIND_OUTER, K.KIND_INNER):
        width = tolerance_width(d)
        if width is None:
            return MANUAL
        if width >= .1 - 1e-9:
            return CALIPER if covers(d, 0, 150) else MANUAL
        if d.kind == K.KIND_OUTER:
            for lo, hi, name in ((0, 25, MICROMETER), (25, 50, MICROMETER_50)):
                if covers(d, lo, hi):
                    return name
        else:
            for name in CATALOG:
                if not name.startswith('Нутромер'):
                    continue
                m = re.search(r'(\d+)-(\d+)\s*$', name)
                if m and covers(d, float(m[1]), float(m[2])):
                    return name
        return MANUAL
    if d.kind in (K.KIND_LINEAR, K.KIND_CHAMFER):
        return CALIPER if covers(d, 0, 150) else MANUAL
    if d.kind == K.KIND_ROUGHNESS:
        return PROFILOMETER
    if d.kind == K.KIND_RADIUS:
        return 'Обеспеч. инструментом'
    if d.kind == K.KIND_ANGLE:
        return 'Обеспеч. программой'
    # Ни круглость, ни положение относительно баз нельзя однозначно
    # свести к одному индикатору без схемы контроля детали.
    if d.kind == K.KIND_FORM_TOL:
        return MANUAL
    if d.kind in ('требование', 'надпись'):
        return ''
    return MANUAL  # резьбу сверяют с типом, шагом и полем допуска калибра


def assign(dims):
    for d in dims:
        if not d.instrument_manual:
            d.instrument = suggest(d)
