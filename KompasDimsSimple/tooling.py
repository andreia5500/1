"""Collect tooling from selected TP sheets and prepare the existing MK VO."""
import copy
import json
import math
import re
from datetime import datetime
import kompas_dims as K
import transfer as X
import cards as C
import sheet_names as N
import layout as L
import debug_log as J

GROUPS=('Мерительная','Режущая','Слесарная','Шлифовальная','Приспособления','Прочая оснастка')
HEADINGS={'мерительная':GROUPS[0],'режущая':GROUPS[1],'токарная':GROUPS[1],
          'слесарная':GROUPS[2],'селсарная':GROUPS[2],'шлифовальная':GROUPS[3],
          'приспособления':GROUPS[4],'прочая оснастка':GROUPS[5]}
FONT=('FontName','Height','WidthFactor','Italic','Bold','Underline','Color')
PROPS=('Align','IndentedLine','LeftEdge','RightEdge','Step','StepAfterParagraph','StepBeforeParagraph')
IGNORE=('обеспеч.', 'обеспечивается', 'выбрать меритель')
MEASURE=re.compile(r'штанген|микрометр|нутромер|калибр|профилометр|индикатор|кругломер|твердомер|прибор измерения|угломер|линейка|рулетка|щуп|скоба',re.I)
START=re.compile(r'^(?:штанген|микрометр|нутромер|калибр|профилометр|индикатор|кругломер|твердомер|прибор|угломер|линейка|рулетка|щуп|скоба|державка|резец|пластина|сверл|фрез|метчик|развертк|зенкер|цанг|втулк|тиски|патрон|шабер|надфил|круг|очки|перчат|щетк|совок|рольганг|обеспеч|выбрать)',re.I)


def clean(s):
    return re.sub(r'\s+',' ',s.replace('\x01',' ').replace('\t',' ')).strip(' ;,')


def key(s):
    return clean(X.display(s)).casefold().replace('ё','е').replace('−','-').replace('–','-').rstrip('.')


def category(s,measuring=False):
    if measuring or MEASURE.search(s):return GROUPS[0]
    if re.search(r'круг\b|абразив|шлиф',s,re.I):return GROUPS[3]
    if re.search(r'шабер|надфил|напиль|щетк|совок|очки|перчат|молот|ключ\b',s,re.I):return GROUPS[2]
    if re.search(r'тиски|цанг|патрон|втулк|рольганг|оправк|приспособ|упор',s,re.I):return GROUPS[4]
    if re.search(r'держав|резец|пластин|сверл|фрез|метчик|развертк|зенкер|зенков|плашк',s,re.I):return GROUPS[1]
    return GROUPS[5]


def split_tools(s):
    # Keep decimal commas and slash-separated alternatives intact.
    out=[];start=0;depth=0
    for i,ch in enumerate(s):
        if ch in '([':depth+=1
        elif ch in ')]':depth=max(0,depth-1)
        elif depth==0 and (ch==';' or ch==',' and not (i and i+1<len(s) and s[i-1].isdigit() and s[i+1].isdigit()) or ch=='/' and START.match(X.display(s[i+1:].lstrip()))):
            out.append(s[start:i]);start=i+1
    out.append(s[start:])
    return [clean(t).rstrip(' .') for t in out if clean(t).rstrip(' .') and not key(t).startswith(IGNORE)]


def text_lines(stamp,cid):
    t=stamp.Text(cid)
    return [str(t.TextLine(i).Str or '') for i in range(int(t.Count))]


def column_ids(stamp):
    ids=[];seen=set();previous=-1
    for _ in range(10000):
        cid=int(stamp.GetNextColumnId(previous))
        if cid<=0 or cid in seen:break
        seen.add(cid);ids.append(cid);previous=cid
    else:raise ValueError('Не удалось завершить перечисление граф штампа.')
    return ids


MISSING_2000=('Графы 2000 нет в оформлении листа %d (%s, стиль %s): КОМПАС хранит текст, '
              'но не выводит его на лист. Нужны номера граф строк ведомости этого оформления.')


def invisible_text(stamp,cid,snapshot):
    """Text stored under an ID that the layout does not contain is never drawn.

    GetNextColumnId lists only the layout's own filled cells; a filled ID absent
    from that list (seen for 2000 on MK VO styles 200/24) is invisible."""
    return any(clean(line['text']) for line in snapshot) and cid not in column_ids(stamp)


def optional_lines(stamp,cid):
    try:return text_lines(stamp,cid)
    except Exception:return []


def joined_instruments(rows):
    """A catalog name can be wrapped across consecutive card rows."""
    out=[];pending=''
    for s in rows+['']:
        s=clean(s)
        if not s:
            if pending:out.append(pending);pending=''
        elif not pending:pending=s
        elif key(s)==key(pending):continue
        elif START.match(X.display(s)):
            out.append(pending);pending=s
        else:pending+=' '+s
    return out


def route_tools(lines,active=False,pending='',final=True):
    out=[]
    for raw in lines:
        m=re.match(r'^\s*([АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯA-Z])(?:\s|\x01)+',raw)
        if m:
            if pending:out.append(pending);pending=''
            active=m.group(1) in ('Т','T')
            if active:pending=raw[m.end():]
        elif active and raw.strip():pending+=' '+raw
    if pending and final:out.append(pending);pending=''
    return out,active,pending


def collect(doc,module,path,selected):
    descriptors=N.describe(doc,path,X.sheet_at);entries=[];snapshots=[];warnings=[]
    active=False;previous=-2;carry='';carry_refs=[]
    for index in sorted(selected):
        sh=X.sheet_at(doc.LayoutSheets,index);_,style,name=descriptors[index]
        cells={};items=[]
        def get(cid):
            rows=text_lines(sh.Stamp,cid);cells[cid]=rows
            J.event('Прочитан источник инструмента',path=path,sheet=index+1,name=name,
                    signature=C.signature(sh),column=cid,rows=rows)
            return rows
        if 'ОК ТК' in name and style in C.INSTRUMENT_IDS:
            rows=get(2001)
            if not any(clean(s) for s in rows):
                rows=[]
                for cid in C.INSTRUMENT_IDS[style]:rows.extend(get(cid) or [''])
            items=[(s,True) for s in joined_instruments(rows)]
        elif name.startswith('МК —'):
            rows=get(2000)
            if not any(clean(s) for s in rows):
                mb,cb,n=(3306,3322,14) if style==21 else (3338,3355,17)
                rows=[(' '.join(get(mb+i))+' '+' '.join(get(cb+i))).strip() for i in range(n)]
            if rows and clean(rows[0]) and not re.match(r'^\s*[А-ЯA-Z](?:\s|\x01)+',rows[0]) and previous!=index-1:
                warnings.append('Лист %d начинается продолжением строки. Выберите также предыдущий лист МК.'%(index+1))
            contiguous=previous==index-1
            old_refs=list(carry_refs) if contiguous else []
            next_continues=index+1 in selected and descriptors[index+1][2].startswith('МК —')
            chunks,active,carry=route_tools(rows,active if contiguous else False,carry if contiguous else '',not next_continues)
            items=[(s,False,sorted(set(old_refs+[index+1])) if j==0 and old_refs else [index+1]) for j,s in enumerate(chunks)]
            carry_refs=(sorted(set(old_refs+[index+1])) if not chunks else [index+1]) if carry else []
        elif 'КЭ ЧПУ' in name and 'эскиз' not in name:
            for cid,base,measuring in [(2002,3095,False),(2006,3159,True)]:
                rows=get(cid)
                if not any(clean(s) for s in rows) and style==5:
                    rows=[' '.join(get(base+i)) for i in range(16)]
                items.extend((s,measuring) for s in joined_instruments(rows))
        else:raise ValueError(N.label(descriptors[index])+': нет поддерживаемых граф инструмента. Выберите МК, ОК ТК или КЭ с инструментом.')
        previous=index
        snapshots.append(dict(index=index,signature=C.signature(sh),cells=cells,name=name))
        if not items:warnings.append('Лист %d: инструмент в поддерживаемых графах не найден.'%(index+1))
        for item_record in items:
            raw,measuring=item_record[:2]
            refs=item_record[2] if len(item_record)>2 else [index+1]
            if 'выбрать меритель' in key(raw):warnings.append('Лист %d: есть незаполненный меритель.'%(index+1))
            for item in split_tools(raw):
                entries.append(dict(text=item,group=category(item,measuring),source=refs))
    merged={}
    for e in entries:
        k=key(e['text'])
        if k in merged:
            merged[k]['source']=sorted(set(merged[k]['source']+e['source']))
            if e['group']==GROUPS[0]:merged[k]['group']=GROUPS[0]
        else:merged[k]=e
    J.event('Сбор инструмента завершён',raw_count=len(entries),unique_count=len(merged),
            entries=list(merged.values()),warnings=warnings)
    return list(merged.values()),snapshots,warnings


def snapshot_text(t,module):
    result=[]
    for i in range(int(t.Count)):
        line=t.TextLine(i)
        props={p:getattr(line,p) for p in PROPS}
        runs=[]
        for j in range(int(line.Count)):
            item=line.TextItem(j);f=module.ITextFont(item)
            runs.append(dict(text=str(item.Str or ''),type=int(item.ItemType),font={p:getattr(f,p) for p in FONT}))
        result.append(dict(text=str(line.Str or ''),style=int(K.get(line,'Style',0)),props=props,runs=runs))
    return result


def source_indices(descriptions):
    return [index for index,style,name in descriptions if
            ('ОК ТК' in name and style in C.INSTRUMENT_IDS) or
            name.startswith('МК —') or ('КЭ ЧПУ' in name and 'эскиз' not in name)]


def read(path,sources,targets):
    if not targets:raise ValueError('Выберите справа листы МК ВО для записи.')
    from sketch import context
    module,mod5,k5,app,doc,doc5=context(path)
    desc=N.describe(doc,path,X.sheet_at)
    J.event('Состав ТП',path=path,active_path=app.ActiveDocument.PathName,
            sheets=[dict(sheet=i+1,style=s,name=n,signature=C.signature(X.sheet_at(doc.LayoutSheets,i))) for i,s,n in desc],
            selected_sources=sources,selected_targets=[i+1 for i in targets])
    auto=sources is None
    if auto:sources=source_indices(desc)
    if not sources:raise ValueError('Не найдены листы-источники инструмента: МК, ОК ТК или КЭ с инструментом.')
    if set(sources)&set(targets):raise ValueError('Источник и ведомость должны быть разными листами.')
    entries,snapshots,warnings=collect(doc,module,path,sources)
    if auto:
        unknown=[str(i+1) for i,_,name in desc if name=='Название не определено']
        if unknown:warnings.append('Не распознаны и пропущены листы: '+', '.join(unknown))
    pages=[];heading=None;body=None;sample_sheets=[];group_names={}
    for index in sorted(targets):
        if not desc[index][2].startswith('МК ВО'):raise ValueError('Лист %d не распознан как МК ВО. Сохраните оформление ТП и перечитайте файл.'%(index+1))
        sh=X.sheet_at(doc.LayoutSheets,index)
        old=snapshot_text(sh.Stamp.Text(2000),module)
        if invisible_text(sh.Stamp,2000,old):
            raise ValueError(MISSING_2000%(index+1,desc[index][2],desc[index][1])+' Запись не начата.')
        pages.append(dict(index=index,signature=C.signature(sh),old=old,
                          height=140.25 if 'продолжение' in desc[index][2] else 132.0))
    # Empty continuation pages use a filled reference anywhere in this TP.
    # Reference-only pages are never included in the write plan.
    for index,_,name in desc:
        if not name.startswith('МК ВО'):continue
        sh=X.sheet_at(doc.LayoutSheets,index)
        old=snapshot_text(sh.Stamp.Text(2000),module)
        if invisible_text(sh.Stamp,2000,old):continue  # not a visible sample
        used=False
        for line_index,line in enumerate(old):
            name=clean(line['text']).rstrip(':').casefold()
            if name in HEADINGS:
                group_names.setdefault(HEADINGS[name],clean(line['text']).rstrip(':'))
                if heading is None:heading=copy.deepcopy(line);heading['native_index']=line_index;heading['sample']=index;used=True
            elif clean(line['text']) and line['runs'] and body is None:
                body=copy.deepcopy(line);body['native_index']=line_index;body['sample']=index;used=True
        if used:sample_sheets.append(dict(index=index,signature=C.signature(sh),old=old))
    if not body or not heading:
        raise ValueError('В ТП не найден заполненный образец МК ВО. Не удалось подтвердить оформление ведомости; запись не начата.')
    for template in (heading,body):
        fonts=[r['font'] for r in template['runs'] if r['text'].strip()]
        if not fonts:raise ValueError('Не удалось прочитать шрифт образца ведомости.')
        template['font']=fonts[0]
        native=native_read(mod5,doc5,template['sample'])
        styles=native_styles(mod5,k5,native)
        matching=[r['style'] for r in styles if clean(X.display(r['text']))==clean(X.display(template['text']))]
        if not matching:
            raise ValueError('Образец МК ВО не совпал при чтении через API5 и API7. Запись не начата.')
        template['style']=matching[0]
        J.event('Образец оформления МК ВО',sheet=template['sample']+1,template=template,native_rows=styles)
    # Automatic line spacing follows font height; an arbitrary fixed 8.25 mm
    # discarded usable space in the supplied free-text body rectangles.
    step=max(float(t['props']['Step']) if float(t['props']['Step'])>0 else float(t['font']['Height'])*1.6 for t in (heading,body))
    step=max(step,max(float(t['font']['Height'])*1.6 for t in (heading,body)))
    extra=max(max(float(t['props']['StepBeforeParagraph']),0)+max(float(t['props']['StepAfterParagraph']),0) for t in (heading,body))
    for p in pages:p['capacity']=int(p['height']//(step+extra))
    width=273-max(float(body['props']['LeftEdge']),0)-max(float(body['props']['RightEdge']),0)-10
    charwidth=max(float(body['font']['Height'])*max(float(body['font']['WidthFactor']),1),1)
    limit=max(20,min(100,int(width/charwidth)))
    return dict(count=int(doc.LayoutSheets.Count),sources=snapshots,pages=pages,entries=entries,samples=sample_sheets,
                heading=heading,body=body,limit=limit,warnings=warnings,descriptions=desc,group_names=group_names)


def plan(data,entries):
    if not entries:raise ValueError('Не выбран инструмент.')
    if any(e['group'] not in GROUPS or not clean(e['text']) for e in entries):
        raise ValueError('Проверьте наименование и группу инструмента.')
    unique={}
    for e in entries:
        k=key(e['text'])
        if k not in unique:unique[k]=e
    entries=list(unique.values())
    groups=[]
    for group in GROUPS:
        values=[];seen=set()
        for e in entries:
            if e['group']!=group:continue
            k=key(e['text'])
            if not k or k in seen:continue
            seen.add(k);values.append(e['text'])
        if values:groups.append((group,values))
    pages=[[] for _ in data['pages']];pi=0
    for group,values in groups:
        rows=[]
        # Each item starts a new line; long names are wrapped without splitting
        # native index/special-symbol sequences.
        for value in values:
            wrapped=L.wrap(value,data['limit'])
            if any(L.visual_len(row)>data['limit'] for row in wrapped):
                raise ValueError('Слишком длинное обозначение без пробелов: '+value+' — добавьте место переноса.')
            rows.extend(wrapped)
        if pages[pi] and len(pages[pi])<data['pages'][pi]['capacity']:
            pages[pi].append(dict(text='',heading=False))
        need_heading=True
        for row in rows:
            required=2 if need_heading else 1
            if len(pages[pi])+required>data['pages'][pi]['capacity']:
                pi+=1
                if pi>=len(pages):raise ValueError('На выбранных листах МК ВО не хватает места. Выберите дополнительные листы ведомости или сократите список.')
                need_heading=True
                if data['pages'][pi]['capacity']<2:raise ValueError('На листе нет места для заголовка и инструмента.')
            if need_heading:pages[pi].append(dict(text=data.get('group_names',{}).get(group,group),heading=True));need_heading=False
            pages[pi].append(dict(text=row,heading=False))
    return pages


def native_arrays(mod5,k5,data,planned):
    arrays=[]
    for rows in planned:
        lines=mod5.ksDynamicArray(k5.GetDynamicArray(3))  # TEXT_LINE_ARR
        for row in rows:
            template=data['heading'] if row['heading'] else data['body']
            line=mod5.ksTextLineParam(k5.GetParamStruct(29));line.Init()
            line.style=template.get('style',0)
            items=mod5.ksDynamicArray(k5.GetDynamicArray(4))  # TEXT_ITEM_ARR
            item=X._text_item_param(k5);item.Init();item.type=0
            # The array is a stream of text components. Explicit paragraph
            # separators are necessary; separate array items alone can join.
            item.s=(X.safe(row['text']) if row['text'] else ' ')+'\n'
            X.set_font(item,template['font'])
            X.check_result(items.ksAddArrayItem(-1,item),'подготовка компонента текста')
            X.check_result(line.SetTextItemArr(items),'подготовка строки ведомости')
            X.check_result(lines.ksAddArrayItem(-1,line),'подготовка массива строк')
        arrays.append(lines)
    return arrays


def native_stamp(doc5,index):
    stamp=J.call('GetStampEx',doc5.GetStampEx,index+1,sheet=index+1,column=2000)
    if stamp is None:raise RuntimeError('API5 не вернул штамп листа %d.'%(index+1))
    # ksStamp exposes the sheet number as the SheetNumb property, not a method.
    actual=getattr(stamp,'SheetNumb',None)
    J.event('Номер листа штампа API5',sheet=index+1,actual=actual)
    if actual is None or int(actual)!=index+1:
        raise RuntimeError('API5 вернул штамп другого листа: выбран %d, получен %s.'%(index+1,actual))
    return stamp


def native_columns(mod5,k5,doc5,index):
    """Enumerate the native cells independently, including their actual IDs."""
    stamp=native_stamp(doc5,index);result={}
    J.call('ksOpenStamp',stamp.ksOpenStamp,require_result=True,sheet=index+1,mode='diagnostic')
    try:
        for _ in range(10000):
            value=J.call('ksGetStampColumnText',stamp.ksGetStampColumnText,0,sheet=index+1,mode='enumerate')
            if not isinstance(value,tuple) or len(value)!=2:raise RuntimeError('API5: нет пары массив/номер графы.')
            array,cid=value
            if array is None:break
            cid=int(cid)
            if cid in result:raise RuntimeError('API5 повторил графу %d при перечислении.'%cid)
            result[cid]=native_styles(mod5,k5,mod5.ksDynamicArray(array))
            J.event('Нативная графа ТП',sheet=index+1,column=cid,rows=result[cid])
        else:raise RuntimeError('Не удалось завершить перечисление граф API5.')
        return result
    finally:J.call('ksCloseStamp',stamp.ksCloseStamp,require_result=True,sheet=index+1,mode='diagnostic')


def diagnose(path,indices):
    if not indices:raise ValueError('Выберите справа листы для проверки.')
    from sketch import context
    module,mod5,k5,app,doc,doc5=context(path)
    desc=N.describe(doc,path,X.sheet_at);report=dict(version=J.VERSION,operation=J.operation_id(),path=path,sheets=[])
    file=X.backup_folder()/('tooling_diagnostic_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    summaries=[]
    try:
        for index in sorted(indices):
            if not 0<=index<int(doc.LayoutSheets.Count):raise ValueError('Лист %d отсутствует.'%(index+1))
            C.require_active(app,path)
            sh=X.sheet_at(doc.LayoutSheets,index)
            api7={cid:snapshot_text(sh.Stamp.Text(cid),module) for cid in column_ids(sh.Stamp)}
            listed=2000 in api7
            api7.setdefault(2000,snapshot_text(sh.Stamp.Text(2000),module))
            native=native_columns(mod5,k5,doc5,index)
            record=dict(sheet=index+1,name=desc[index][2],signature=C.signature(sh),crossed=sh.Stamp.Crossed,
                        api7=api7,api5=native)
            report['sheets'].append(record);J.event('Диагностика листа',**record)
            rows=[dict(text=s) for line in api7[2000] for s in line['text'].replace('\r\n','\n').replace('\r','\n').rstrip('\n').split('\n')]
            if not listed and any(clean(r['text']) for r in rows):
                record['invisible_2000']=True
                summaries.append('Лист %d · %s: в графе 2000 хранится %d строк, но такой графы нет в оформлении — на листе они не видны. Графы оформления: %s.'
                                 %(index+1,desc[index][2],sum(bool(clean(r['text'])) for r in rows),', '.join(str(c) for c in api7 if c!=2000)))
                continue
            try:verify_text(native.get(2000,[]),rows,index,'API5 / API7')
            except RuntimeError as exc:
                record['mismatch']=str(exc);J.failure('Два API читают разное содержимое графы',exc,sheet=index+1,column=2000)
                summaries.append('Лист %d: API5 и API7 читают разные тексты графы 2000.'%(index+1))
            else:
                count=sum(bool(clean(r['text'])) for r in rows)
                summaries.append('Лист %d · %s: графа 2000, %d непустых строк; тексты API5 и API7 совпали.'%(index+1,desc[index][2],count))
        refresh_document(module,app,doc,path)
    except Exception as exc:
        report['error']=str(exc);J.failure('Диагностика ТП остановлена',exc,path=path,report=str(file));raise
    finally:file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    J.event('Диагностика сохранена',report=str(file),summary=summaries)
    return '\n'.join(summaries)+'\n\nПолные графы, стили и шрифты записаны в журнал. Совпадение текстов API не подтверждает видимость на листе.'


def native_read(mod5,doc5,index):
    stamp=native_stamp(doc5,index)
    J.call('ksOpenStamp',stamp.ksOpenStamp,require_result=True,sheet=index+1,column=2000,mode='read')
    try:
        J.call('ksColumnNumber',stamp.ksColumnNumber,2000,require_result=True,sheet=index+1,column=2000)
        result=J.call('ksGetStampColumnText',stamp.ksGetStampColumnText,0,sheet=index+1,column=2000)
        if not isinstance(result,tuple) or len(result)!=2:
            raise RuntimeError('API5 не вернул номер прочитанной графы.')
        array,cid=result
        if int(cid)!=2000 or array is None:
            raise RuntimeError('API5 прочитал другую графу вместо 2000: %s.'%cid)
        return mod5.ksDynamicArray(array)
    finally:J.call('ksCloseStamp',stamp.ksCloseStamp,require_result=True,sheet=index+1,column=2000,mode='read')


def native_styles(mod5,k5,array):
    result=[]
    for i in range(int(array.ksGetArrayCount())):
        line=mod5.ksTextLineParam(k5.GetParamStruct(29));line.Init()
        X.check_result(array.ksGetArrayItem(i,line),'чтение строки образца')
        items=mod5.ksDynamicArray(line.GetTextItemArr());texts=[];components=[]
        for j in range(int(items.ksGetArrayCount())):
            item=X._text_item_param(k5);item.Init()
            X.check_result(items.ksGetArrayItem(j,item),'чтение компоненты образца')
            # A special symbol (e.g. Ø = @2~) is a separate non-text component
            # carrying its number in iSNumb; keep it, or 'Ø11f7' reads '11f7'.
            snumb=int(X.get_prop(item,'iSNumb',0) or 0)
            if int(item.type)==0:texts.append(str(item.s or ''))
            elif snumb>0:texts.append('@%d~'%snumb)
            # ksTextItemFont spells its properties as in the type library
            # (bitVector, not bitvector); gen_py lookups are case-sensitive.
            f=item.GetItemFont();g=lambda name:X.get_prop(f,name);bits=int(g('bitvector'))
            # ON/OFF bits are explicit overrides; with neither set the value comes
            # from the text style (KOMPAS keeps only 0x1000 for italic GOST
            # headings), so it is unknown here (None), not False.
            flag=lambda on,off:True if bits&on else False if bits&off else None
            font=dict(FontName=str(g('fontName')),Height=float(g('height')),WidthFactor=float(g('ksu')),
                      Color=int(g('color')),Italic=flag(0x40,0x80),Bold=flag(0x100,0x200),Underline=flag(0x400,0x800))
            components.append(dict(text=str(item.s or ''),type=int(item.type),snumb=snumb,font=font,flags=bits))
        result.append(dict(text=''.join(texts),style=int(line.style),items=components))
    return result


def native_write(doc5,index,lines):
    stamp=native_stamp(doc5,index)
    J.call('ksOpenStamp',stamp.ksOpenStamp,require_result=True,sheet=index+1,column=2000,mode='write')
    try:
        # Select the cell explicitly, as in the working original program.
        J.call('ksColumnNumber',stamp.ksColumnNumber,2000,require_result=True,sheet=index+1,column=2000)
        J.call('ksSetStampColumnText',stamp.ksSetStampColumnText,2000,lines,require_result=True,sheet=index+1,column=2000)
    finally:J.call('ksCloseStamp',stamp.ksCloseStamp,require_result=True,sheet=index+1,column=2000,mode='write')


def refresh_document(module,app,doc,path):
    C.require_active(app,path)
    interface=module.IKompasDocument1(doc)
    # RedrawDocument(ksRedrawFull=0), not ksRebuildDocument: the latter only
    # rebuilds associative views and cannot refresh a stamp-only TP.
    J.call('RedrawDocument',interface.RedrawDocument,0,require_result=True,path=path)
    C.require_active(app,path)
    J.event('Окно ТП перерисовано',path=path,active_path=app.ActiveDocument.PathName,
            changed=K.get(doc,'Changed'),read_only=K.get(doc,'ReadOnly'))


def refresh_stamp(module,doc,index):
    stamp=X.sheet_at(doc.LayoutSheets,index).Stamp
    crossed=stamp.Crossed
    J.event('Состояние отображения штампа',sheet=index+1,column=2000,crossed=crossed)
    # Update is needed only when KOMPAS reports unapplied stamp parameters.
    # Calling it unconditionally produced false failures in older releases.
    if crossed:
        J.call('IStamp.Update',stamp.Update,require_result=True,sheet=index+1,column=2000)
        stamp=X.sheet_at(doc.LayoutSheets,index).Stamp
        J.event('Штамп после Update',sheet=index+1,crossed=stamp.Crossed)
        if stamp.Crossed:raise RuntimeError('Лист %d: КОМПАС оставил штамп неперестроенным.'%(index+1))


def verify_native(actual,rows,data,index):
    verify_text(actual,rows,index,'API5')
    if len(actual)<len(rows):raise RuntimeError('API5: лист %d, строки склеены.'%(index+1))
    for n,(line,row) in enumerate(zip(actual,rows)):
        template=data['heading'] if row['heading'] else data['body']
        if line['style']!=template.get('style',0):
            raise RuntimeError('API5: лист %d, строка %d, стиль %s вместо %s.'%(index+1,n+1,line['style'],template.get('style',0)))
        if any(not same_native_font(item['font'],template['font']) for item in line['items'] if item['type']==0 and item['text'].strip()):
            raise RuntimeError('API5: лист %d, строка %d, шрифт не совпал с образцом.'%(index+1,n+1))


def verify_text(verified,rows,index,api='API7'):
    actual=[clean(X.display(s)) for line in verified for s in line['text'].replace('\r\n','\n').replace('\r','\n').rstrip('\n').split('\n')]
    expected=[clean(X.display(X.safe(row['text']))) for row in rows]
    while actual and not actual[-1]:actual.pop()
    while expected and not expected[-1]:expected.pop()
    if actual!=expected:
        pos=next(i for i in range(max(len(actual),len(expected)))
                 if (actual[i] if i<len(actual) else None)!=(expected[i] if i<len(expected) else None))
        want=expected[pos] if pos<len(expected) else '<конец текста>'
        got=actual[pos] if pos<len(actual) else '<строка отсутствует>'
        raise RuntimeError('%s: текст на листе %d не совпал: строка %d.\nОжидалось: %r\nПрочитано: %r\nСтрок без пустого хвоста: ожидалось %d, прочитано %d.'%(api,index+1,pos+1,want,got,len(expected),len(actual)))


def verify_written(verified,rows,data,index):
    # A trailing empty paragraph does not change the contents of the cell.
    # Internal empty lines, order, and all nonempty lines must still match.
    verify_text(verified,rows,index)
    # Do not silently accept one paragraph containing every item: each planned
    # row needs its own paragraph to preserve its heading/body formatting.
    if len(verified)<len(rows):raise RuntimeError('Лист %d: строки склеены в абзац; оформление не подтверждено.'%(index+1))
    for n,(line,row) in enumerate(zip(verified,rows)):
        template=data['heading'] if row['heading'] else data['body']
        if not same_props(line['props'],template['props']) or any(not same_props(run['font'],template['font']) for run in line['runs'] if run['text'].strip() and run['type']==0):
            raise RuntimeError('Форматирование ведомости не совпало с образцом: лист %d, строка %d.'%(index+1,n+1))


def first_difference(actual,expected):
    """Human-readable first mismatch between two native/API7 line lists."""
    for n in range(max(len(actual),len(expected))):
        a=actual[n] if n<len(actual) else None;e=expected[n] if n<len(expected) else None
        if a!=e:
            if a is None or e is None:return 'строка %d: %s'%(n+1,'отсутствует' if a is None else 'лишняя')
            fields=[k for k in sorted(set(a)|set(e)) if a.get(k)!=e.get(k)]
            return 'строка %d (%r), отличается: %s; было %s, стало %s'%(
                n+1,e.get('text',''),', '.join(fields),
                json.dumps({k:e.get(k) for k in fields},ensure_ascii=False)[:400],
                json.dumps({k:a.get(k) for k in fields},ensure_ascii=False)[:400])
    return 'отличий не найдено'


def same_native_font(native,expected):
    """API5 font vs API7 template; flags left to the text style are not compared."""
    known={k:v for k,v in native.items() if v is not None}
    return same_props(known,{k:expected.get(k) for k in known})


def same_props(a,b):
    if a.keys()!=b.keys():return False
    return all(math.isclose(a[k],b[k],abs_tol=1e-5,rel_tol=1e-6) if isinstance(a[k],(int,float)) and isinstance(b[k],(int,float)) else a[k]==b[k] for k in a)


def write(path,data,entries):
    planned=plan(data,entries)
    J.require_storage()
    from sketch import context
    module,mod5,k5,app,doc,doc5=context(path)
    if int(doc.LayoutSheets.Count)!=data['count']:raise ValueError('Состав листов изменился. Перечитайте ТП.')
    for source in data['sources']:
        sh=X.sheet_at(doc.LayoutSheets,source['index'])
        if C.signature(sh)!=source['signature']:raise ValueError('Источник изменился. Перечитайте ТП.')
        for cid,rows in source['cells'].items():
            if text_lines(sh.Stamp,int(cid))!=rows:raise ValueError('Инструмент в источнике изменился. Перечитайте ТП.')
    for page in data['pages']:
        sh=X.sheet_at(doc.LayoutSheets,page['index'])
        if C.signature(sh)!=page['signature'] or snapshot_text(sh.Stamp.Text(2000),module)!=page['old']:
            raise ValueError('Ведомость изменилась после просмотра. Перечитайте ТП.')
    for sample in data.get('samples',[]):
        sh=X.sheet_at(doc.LayoutSheets,sample['index'])
        if C.signature(sh)!=sample['signature'] or snapshot_text(sh.Stamp.Text(2000),module)!=sample['old']:
            raise ValueError('Образец оформления изменился после просмотра. Перечитайте ТП.')
    native_count=J.call('ksGetDocumentPagesCount',doc5.ksGetDocumentPagesCount,path=path)
    if int(native_count)!=int(doc.LayoutSheets.Count):
        raise RuntimeError('API5 и API7 вернули разный состав ТП: %s / %s листов.'%(native_count,doc.LayoutSheets.Count))
    J.event('План записи МК ВО',path=path,active_path=app.ActiveDocument.PathName,
            targets=[p['index']+1 for p in data['pages']],column=2000,planned=planned,
            heading=data['heading'],body=data['body'])
    originals=[native_read(mod5,doc5,page['index']) for page in data['pages']]
    original_texts=[native_styles(mod5,k5,array) for array in originals]
    untouched=[]
    for page in data['pages']:
        stamp=X.sheet_at(doc.LayoutSheets,page['index']).Stamp
        # Enum returns only nonempty fields. Keep the full snapshots, not just
        # visible text: font/style changes outside the body must also fail.
        untouched.append({cid:snapshot_text(stamp.Text(cid),module) for cid in column_ids(stamp) if cid!=2000})
    arrays=native_arrays(mod5,k5,data,planned)
    payload=[native_styles(mod5,k5,array) for array in arrays]
    backup=X.backup_folder()/('tooling_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    report=dict(version=J.VERSION,operation=J.operation_id(),path=path,before=data,after=planned,
                native_before=original_texts,native_payload=payload,readback=[],status='prepared')
    def save_report():
        backup.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    save_report()
    J.event('Резервные графы и отправляемые структуры сохранены',report=str(backup),native_before=original_texts,native_payload=payload)
    changed=0
    try:
        for page,rows,array,other in zip(data['pages'],planned,arrays,untouched):
            C.require_active(app,path)
            changed+=1
            report['status']='writing';report['current_sheet']=page['index']+1;save_report()
            native_write(doc5,page['index'],array)
            native_actual=native_styles(mod5,k5,native_read(mod5,doc5,page['index']))
            record=dict(sheet=page['index']+1,column=2000,native_actual=native_actual)
            report['readback'].append(record);save_report()
            J.event('Обратное чтение API5 после закрытия штампа',**record)
            verify_native(native_actual,rows,data,page['index'])
            refresh_stamp(module,doc,page['index'])
            refresh_document(module,app,doc,path)
            # Reacquire API7 objects after the API5 edit session has closed.
            sh=X.sheet_at(doc.LayoutSheets,page['index'])
            verified=snapshot_text(sh.Stamp.Text(2000),module)
            record['actual']=verified
            # Both APIs read back text even for an ID missing from the layout.
            if invisible_text(sh.Stamp,2000,verified):
                raise RuntimeError(MISSING_2000%(page['index']+1,'МК ВО',page['signature']['style']))
            save_report()
            J.event('Обратное чтение API7 после перерисовки',sheet=page['index']+1,column=2000,actual=verified)
            verify_written(verified,rows,data,page['index'])
            after_other={cid:snapshot_text(sh.Stamp.Text(cid),module) for cid in column_ids(sh.Stamp) if cid!=2000}
            if after_other!=other:raise RuntimeError('Лист %d: изменились графы вне ведомости.'%(page['index']+1))
            J.event('Лист подтверждён двумя API',sheet=page['index']+1,column=2000,rows=len(rows),other_columns=list(other))
        # Check the first pages again after the last page has been written:
        # an accidental shared stamp/edit session must not pass as success.
        for page,rows in reversed(list(zip(data['pages'],planned))):
            C.require_active(app,path)
            native_actual=native_styles(mod5,k5,native_read(mod5,doc5,page['index']))
            verified=snapshot_text(X.sheet_at(doc.LayoutSheets,page['index']).Stamp.Text(2000),module)
            J.event('Итоговая проверка в обратном порядке',sheet=page['index']+1,column=2000,native_actual=native_actual,actual=verified)
            verify_native(native_actual,rows,data,page['index']);verify_written(verified,rows,data,page['index'])
        for source in data['sources']:
            stamp=X.sheet_at(doc.LayoutSheets,source['index']).Stamp
            if any(text_lines(stamp,int(cid))!=old for cid,old in source['cells'].items()):
                raise RuntimeError('Изменились графы источника: лист %d.'%(source['index']+1))
        J.require_storage()
        report['status']='verified_api5_api7_redrawn';save_report()
    except Exception as exc:
        report['error']=str(exc)
        J.failure('Запись МК ВО остановлена, начинается восстановление',exc,path=path,changed_pages=changed,report=str(backup))
        restored=True;restore_errors=[]
        # Restore touched cells in reverse order, then read every restored cell.
        for page,original,original_text,other in reversed(list(zip(data['pages'][:changed],originals[:changed],original_texts[:changed],untouched[:changed]))):
            try:
                C.require_active(app,path)
                native_write(doc5,page['index'],original)
                native_restored=native_styles(mod5,k5,native_read(mod5,doc5,page['index']))
                J.event('Обратное чтение API5 после восстановления',sheet=page['index']+1,column=2000,actual=native_restored)
                if native_restored!=original_text:
                    raise RuntimeError('API5: исходная графа не восстановилась полностью: '+first_difference(native_restored,original_text))
                refresh_stamp(module,doc,page['index'])
                sh=X.sheet_at(doc.LayoutSheets,page['index'])
                restored_api7=snapshot_text(sh.Stamp.Text(2000),module)
                if restored_api7!=page['old']:
                    raise RuntimeError('API7: исходная графа не восстановилась полностью: '+first_difference(restored_api7,page['old']))
                now={cid:snapshot_text(sh.Stamp.Text(cid),module) for cid in column_ids(sh.Stamp) if cid!=2000}
                if now!=other:raise RuntimeError('Прочие графы изменились.')
                J.event('Исходная графа восстановлена через оба API',sheet=page['index']+1,column=2000,actual=native_restored)
            except Exception as err:
                restored=False;restore_errors.append('Лист %d: %s'%(page['index']+1,err))
                J.failure('Ошибка восстановления графы',err,sheet=page['index']+1,column=2000)
        try:refresh_document(module,app,doc,path)
        except Exception as err:
            # A failed redraw is not evidence of failed data restoration.
            report['restore_redraw_error']=str(err);J.failure('Не удалось обновить окно после восстановления',err)
        # Restoration of an earlier page must not silently alter a later one.
        for page,original_text in reversed(list(zip(data['pages'][:changed],original_texts[:changed]))):
            try:
                actual=native_styles(mod5,k5,native_read(mod5,doc5,page['index']))
                stamp=X.sheet_at(doc.LayoutSheets,page['index']).Stamp
                if actual!=original_text:
                    raise RuntimeError('Итоговое восстановление (API5) не совпало: '+first_difference(actual,original_text))
                final_api7=snapshot_text(stamp.Text(2000),module)
                if final_api7!=page['old']:
                    raise RuntimeError('Итоговое восстановление (API7) не совпало: '+first_difference(final_api7,page['old']))
            except Exception as err:
                restored=False;restore_errors.append('Лист %d: %s'%(page['index']+1,err))
                J.failure('Итоговая проверка восстановления не прошла',err,sheet=page['index']+1)
        for source in data['sources']:
            try:
                stamp=X.sheet_at(doc.LayoutSheets,source['index']).Stamp
                if any(text_lines(stamp,int(cid))!=old for cid,old in source['cells'].items()):
                    raise RuntimeError('Графы источника отличаются от исходных.')
            except Exception as err:
                restored=False;restore_errors.append('Источник, лист %d: %s'%(source['index']+1,err))
                J.failure('Источник изменён после восстановления',err,sheet=source['index']+1)
        report['restored']=restored;report['restore_errors']=restore_errors
        report['status']='rolled_back' if restored else 'rollback_failed'
        try:save_report()
        except OSError:pass  # Keep the original write/readback error visible.
        status='Исходные графы ведомости восстановлены и проверены.' if restored else 'Восстановление не подтверждено. Закройте ТП без сохранения.'
        details='\n'.join(restore_errors)
        raise RuntimeError('Запись остановлена. %s\nОтчёт: %s\n%s%s'%(status,backup,exc,
                           '\n\nВосстановление:\n'+details if details else '')) from exc
    J.event('МК ВО подтверждена после записи',path=path,positions=len({key(e['text']) for e in entries}),report=str(backup),
            verification='API5 + API7, с перерисовкой; внешний вид автоматически не подтверждён')
    return len({key(e['text']) for e in entries})
