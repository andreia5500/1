"""Допуски в настоящих размерных объектах выбранного листа КЭ.

API5 читает габариты в координатах листа; API7 редактирует отклонения.
Числовые High/LowDeviationValue доступны только для чтения: запись через
HighDeviation.Str/LowDeviation.Str, затем Update размерного объекта.
"""
import copy
import json
import math
import re
from datetime import datetime
import kompas_dims as K
import tolerances as T
import transfer as X
import debug_log as J

COLLECTIONS = (
    ('LineDimensions','LineDimension','line'),
    ('BreakLineDimensions','BreakLineDimension','line'),
    ('DiametralDimensions','DiametralDimension','diam'),
    ('RadialDimensions','RadialDimension','rad'),
    ('BreakRadialDimensions','BreakRadialDimension','rad'),
    ('AngleDimensions','AngleDimension','angle'),
    ('ArcDimensions','ArcDimension','arc'),
    ('HeightDimensions','HeightDimension','line'),
)
KINDS = (K.KIND_LINEAR,K.KIND_OUTER,K.KIND_INNER,K.KIND_RADIUS,K.KIND_CHAMFER,K.KIND_ANGLE)


def rect(values):
    x1,y1,x2,y2 = map(float,values)
    if not all(math.isfinite(v) for v in (x1,y1,x2,y2)):
        raise ValueError('Некорректные координаты.')
    return (min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2))


def frame_rect(sh):
    result = sh.GetPlaceInsideFrames()
    if not isinstance(result,(list,tuple)) or len(result)!=5 or not result[0]:
        raise ValueError('КОМПАС не вернул границы листа. Запись запрещена.')
    return rect(result[1:])


def validate_frames(frames):
    for i,a in enumerate(frames):
        if a is None:
            continue
        if a[2]<=a[0] or a[3]<=a[1]:
            raise ValueError('Не удалось определить область листа %d.'%(i+1))
        for b in frames[:i]:
            if b is None:
                continue
            if min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6:
                raise ValueError('Границы листов пересекаются: API вернул неоднозначные координаты. Запись не начата.')


def read_frames(sheets, selected):
    """Титульные и полностью табличные листы могут не иметь свободной области.

    Сохраняем None на их месте, чтобы номера следующих листов не сдвигались.
    Выбранный лист обязан иметь достоверную ненулевую область.
    """
    frames=[]
    for i in range(int(sheets.Count)):
        try:
            area=frame_rect(X.sheet_at(sheets,i))
            if area[2]<=area[0] or area[3]<=area[1]:
                raise ValueError('API вернул пустую область: %r'%(area,))
        except Exception as exc:
            if i==selected:
                raise ValueError('Не удалось определить область выбранного листа %d. %s'%(i+1,exc)) from exc
            area=None
        frames.append(area)
    validate_frames(frames)
    return frames


def on_sheet(box, frames, sheet):
    # Весь размер, включая стрелки и надпись, должен лежать на одном листе.
    owners=[i for i,r in enumerate(frames) if r is not None and r[0]-1e-6<=box[0] and r[1]-1e-6<=box[1]
            and box[2]<=r[2]+1e-6 and box[3]<=r[3]+1e-6]
    return owners==[sheet]


def snapshot(dt):
    props=('NominalValue','AutoNominalValue','Sign','Tolerance','ToleranceOn',
           'DeviationOn','DeviationType','HighDeviationValue','LowDeviationValue')
    data={name:getattr(dt,name) for name in props}
    for name in ('NominalText','Prefix','Suffix','TextUnder','HighDeviation','LowDeviation'):
        data[name]=K.txt_str(getattr(dt,name))
    for name in ('Rectangle','Brackets','HasTolerance'):
        data[name]=K.get(dt,name)
    return data


def has_existing(state):
    if str(state['Tolerance'] or '').strip():
        return True
    if any(abs(float(state[p] or 0))>1e-12 for p in ('HighDeviationValue','LowDeviationValue')):
        return True
    for p in ('HighDeviation','LowDeviation'):
        text=state[p].strip()
        if text and not re.fullmatch(r'[+\-−]?0+(?:[.,]0+)?',text):
            return True
    text=' '.join(state[p] for p in ('NominalText','Suffix','TextUnder'))
    return bool(re.search(r'[±+−-]\s*\d',text))


def propose(d, state, sources, grade, mode):
    if has_existing(state):
        return None,'Уже есть допуск — сохранить'
    if d.kind not in KINDS or d.limit or state.get('Rectangle') or '*' in d.raw_text:
        return None,'Справочный, предельный или специальный размер — пропущен'
    if d.value<=0 or not math.isfinite(d.value):
        return None,'Некорректный номинал'
    candidates=[s for s in sources if s.kind in KINDS and abs(s.value-d.value)<1e-7
                and not K.diameter_uncertain(s)]
    if K.diameter_uncertain(d):
        return None,'Уточните: вал или отверстие (двойной щелчок)'
    candidates=[s for s in candidates if s.kind==d.kind]
    pairs={(s.hi,s.lo) for s in candidates if s.hi is not None and s.lo is not None}
    if candidates and (len(pairs)!=1 or any(s.hi is None or s.lo is None for s in candidates)):
        return None,'В списке чертежа неоднозначные допуски — задайте вручную'
    if pairs:
        hi,lo=pairs.pop();reason='Из рассчитанного списка чертежа'
    else:
        calc=copy.copy(d)
        calc.src=K.SRC_DEFAULT;calc.manual_tol=False
        try:K.assign_tolerances([calc],grade,mode)
        except ValueError as exc:return None,str(exc)
        hi,lo=calc.hi,calc.lo;reason='Общий допуск: '+('±IT14/2' if mode=='it14' else 'ГОСТ 30893.1-'+grade)
    if hi is None or lo is None or not all(math.isfinite(v) for v in (hi,lo)) or hi<=lo:
        return None,'Допуск не определён — задайте вручную'
    return dict(hi=hi,lo=lo,kind=d.kind),reason


def preview_text(d, proposal):
    dd=copy.copy(d)
    if proposal:
        dd.hi,dd.lo=proposal['hi'],proposal['lo'];dd.kind=proposal['kind']
        dd.fit='';dd.src=K.SRC_DRAWING;dd.manual_tol=True
    return X.display(dd.column_text())


def context(path):
    module,_=K.connect()
    mod5,k5=X._connect5()
    app=module.IApplication(k5.ksGetApplication7())
    doc=X.open_doc(module,app,path);doc.Active=True
    require_active(app,path)
    J.event('Подключение к документу КОМПАСа',requested_path=path,active_path=app.ActiveDocument.PathName,
            application=K.get(app,'ApplicationName'),visible=K.get(app,'Visible'),
            count=int(doc.LayoutSheets.Count),read_only=K.get(doc,'ReadOnly'),changed=K.get(doc,'Changed'))
    return module,mod5,k5,app,doc,k5.ActiveDocument2D()


def require_active(app,path):
    if app.ActiveDocument is None or X.path_key(app.ActiveDocument.PathName)!=X.path_key(path):
        raise ValueError('Выбранный ТП не является активным. Запись не начата.')


def live_scan(module,mod5,k5,doc,doc5,sheet):
    sheets=doc.LayoutSheets
    if not 0<=sheet<int(sheets.Count):raise ValueError('Лист отсутствует.')
    frames=read_frames(sheets,sheet)
    doc2=module.IKompasDocument2D(doc)
    views=doc2.ViewsAndLayersManager.Views
    records,objects,geoms,warnings=[],{},{},[]
    param=mod5.ksRectParam(k5.GetParamStruct(15))  # ko_RectParam, SDK
    for vi in range(int(views.Count)):
        view=views.View(vi);name=K.get(view,'Name','') or 'Вид %d'%vi
        sym=module.ISymbols2DContainer(view)
        for collname,getter,kind in COLLECTIONS:
            try:
                coll=getattr(sym,collname)
            except Exception:
                warning='В этой версии API недоступна коллекция '+collname
                if warning not in warnings:warnings.append(warning)
                continue
            for index in range(int(coll.Count)):
                obj=getattr(coll,getter)(index)
                ref=int(obj.Reference)
                if not doc5.ksGetObjGabaritRect(ref,param):
                    warnings.append('%s: не определён лист размера %s'%(name,ref));continue
                bot,top=param.GetpBot(),param.GetpTop()
                box=rect((bot.x,bot.y,top.x,top.y))
                if not on_sheet(box,frames,sheet):
                    r=frames[sheet]
                    if min(box[2],r[2])>max(box[0],r[0]) and min(box[3],r[3])>max(box[1],r[1]):
                        warnings.append('%s: размер %s пересекает границу листа — пропущен'%(name,ref))
                    continue
                dt=module.IDimensionText(obj)
                d=K.read_dimension(module,obj,kind,name)
                if d is None:
                    warnings.append('%s: не прочитан размер %s'%(name,ref));continue
                if name not in geoms:geoms[name]=K.Geometry.from_view(module,view,False)
                records.append(dict(ref=ref,view=int(view.Reference),collection=collname,index=index,
                                    box=box,state=snapshot(dt),dim=d))
                if ref in objects:raise ValueError('Размер найден повторно; запись остановлена.')
                objects[ref]=obj
    K.classify_diameters([r['dim'] for r in records],geoms)
    return dict(sheet=sheet,count=int(sheets.Count),frames=frames,records=records,warnings=warnings),objects


def read(path,sheet,sources,grade,mode,assume_outer=False):
    module,mod5,k5,app,doc,doc5=context(path)
    data,_=live_scan(module,mod5,k5,doc,doc5,sheet)
    for record in data['records']:
        d=record['dim']
        if assume_outer and K.diameter_uncertain(d):
            d.kind=K.KIND_OUTER;d.manual=True;d.reason='Наружный по выбранной настройке'
        record['proposal'],record['reason']=propose(record['dim'],record['state'],sources,grade,mode)
        if d.reason=='Наружный по выбранной настройке' and record['proposal']:
            record['reason']='Наружный по настройке; '+record['reason']
    J.event('Прочитаны размеры эскиза',path=path,sheet=sheet+1,grade=grade,mode=mode,
            records=[{k:v for k,v in r.items() if k!='dim'} for r in data['records']],warnings=data['warnings'])
    return data


def deviation_text(value,angular=False):
    if abs(value)<1e-12:return ''
    if angular:
        return ('+' if value>0 else '-')+T.fmt_angle_dev(abs(value))[1:]
    return ('+' if value>0 else '-')+T.fmt_num(abs(value))


def write_dimension(module,obj,proposal,before):
    dt=module.IDimensionText(obj)
    dt.DeviationType=0
    dt.ToleranceOn=False
    dt.HighDeviation.Str=deviation_text(proposal['hi'],proposal['kind']==K.KIND_ANGLE)
    dt.LowDeviation.Str=deviation_text(proposal['lo'],proposal['kind']==K.KIND_ANGLE)
    dt.DeviationOn=True
    X.check_result(obj.Update(),'обновление размерного объекта')
    actual=snapshot(module.IDimensionText(obj))
    J.event('Обратное чтение допуска размера',before=before,proposal=proposal,actual=actual)
    if not actual['DeviationOn'] or actual['DeviationType']!=0:
        raise RuntimeError('КОМПАС не включил отображение отклонений.')
    for key,expected in (('HighDeviationValue',proposal['hi']),('LowDeviationValue',proposal['lo'])):
        if not math.isclose(float(actual[key]),expected,rel_tol=1e-8,abs_tol=1e-8):
            raise RuntimeError('Отклонение не подтверждено: %s, ожидалось %s, прочитано %s'%(key,expected,actual[key]))
    for key in ('NominalValue','NominalText','AutoNominalValue','Sign','Prefix','Suffix','TextUnder'):
        if actual[key]!=before[key]:raise RuntimeError('Неожиданно изменилось поле размера: '+key)


def write(path,expected,selected):
    selected=set(selected)
    records=[r for r in expected['records'] if r['ref'] in selected]
    if not records:raise ValueError('Не выбраны размеры.')
    for r in records:
        if not r['proposal'] or has_existing(r['state']):raise ValueError('Нельзя изменять размер с существующим или неопределённым допуском.')
        p=r['proposal']
        if not all(math.isfinite(p[k]) for k in ('hi','lo')) or p['hi']<=p['lo']:raise ValueError('Некорректные отклонения.')
    module,mod5,k5,app,doc,doc5=context(path)
    live,objects=live_scan(module,mod5,k5,doc,doc5,expected['sheet'])
    if live['count']!=expected['count'] or live['frames']!=expected['frames']:
        raise ValueError('Листы ТП изменились. Прочитайте лист заново.')
    current={r['ref']:r for r in live['records']}
    for r in records:
        now=current.get(r['ref'])
        if now is None or any(now[k]!=r[k] for k in ('state','box','view','collection','index')):
            raise ValueError('Размер изменился после просмотра. Прочитайте лист заново.')
    backup=X.backup_folder()/('sketch_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    serial=[{k:v for k,v in r.items() if k!='dim'} for r in records]
    J.event('План расстановки допусков',path=path,sheet=expected['sheet']+1,records=serial,backup=str(backup))
    backup.write_text(json.dumps(dict(path=path,sheet=expected['sheet']+1,records=serial),ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        for r in records:
            require_active(app,path)
            obj=objects[r['ref']]
            if snapshot(module.IDimensionText(obj))!=r['state']:
                raise RuntimeError('Размер изменился во время записи.')
            write_dimension(module,obj,r['proposal'],r['state'])
    except Exception as exc:
        raise RuntimeError('Расстановка остановлена. Часть размеров могла измениться.\n'
                           'Для возврата к сохранённому ТП закройте его без сохранения.\n'
                           'Резервные значения: %s\n%s'%(backup,exc)) from exc
    return len(records)
