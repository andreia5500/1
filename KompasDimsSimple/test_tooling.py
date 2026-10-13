import copy
import unittest
from unittest.mock import patch
from types import SimpleNamespace as NS
from pathlib import Path
import tooling as V
import sheet_names as N

class ToolingTests(unittest.TestCase):
    def test_readback_trailing_empty_paragraphs_only(self):
        template=dict(props={},font={})
        data=dict(heading=template,body=template)
        rows=[dict(text=s,heading=False) for s in ['Мерительная','Микрометр','','Штангенциркуль']]
        def verify(texts):
            V.verify_written([dict(text=s,props={},runs=[]) for s in texts],rows,data,3)
        verify(['Мерительная','Микрометр','','Штангенциркуль',' ',''])
        for texts in [[],['Мерительная','Микрометр'],
                      ['Мерительная','Микрометр','Штангенциркуль'],
                      ['Мерительная','Штангенциркуль','','Микрометр'],
                      ['Мерительная','Микрометр','','Штангенциркуль','Лишний прибор']]:
            with self.subTest(texts=texts),self.assertRaisesRegex(RuntimeError,'листe 4|листе 4'):
                verify(texts)

    def test_decimal_comma_and_parentheses(self):
        self.assertEqual(V.split_tools('Сверло Ø6,5, Резец (пластина, винт); Микрометр МК-25'),
                         ['Сверло Ø6,5','Резец (пластина, винт)','Микрометр МК-25'])

    def test_not_a_tool(self):
        self.assertEqual(V.split_tools('Обеспеч. программой; Обеспеч. инструментом; Выбрать меритель'),[])

    def test_wrapped_control_name(self):
        rows=['Штангенциркуль','односторонний ШЦК-I-150','','Микрометр МК-25','Микрометр МК-25','','Профилометр Mitutoyo','SJ210']
        self.assertEqual(V.joined_instruments(rows),['Штангенциркуль односторонний ШЦК-I-150','Микрометр МК-25','Профилометр Mitutoyo SJ210'])

    def test_mk_only_t_rows(self):
        rows=['А     005 Отрезная','Б JET','О Снять заусенцы', 'Т\x01Сверло Ø6,5,','Тиски станочные','О Промыть', 'Не читать']
        self.assertEqual(V.route_tools(rows)[0],['Сверло Ø6,5, Тиски станочные'])

    def test_grouping(self):
        for name,group in [('Круг абразивный', 'Шлифовальная'),('Шабер Mango','Слесарная'),('Микрометр МК-25','Мерительная'),('Державка SCLCR','Режущая'),('Тиски станочные','Приспособления')]:
            self.assertEqual(V.category(name),group)

    def test_pagination_heading_repeated(self):
        data=dict(pages=[dict(capacity=3),dict(capacity=3)],limit=60)
        entries=[dict(text='Микрометр '+str(i),group=V.GROUPS[0]) for i in range(4)]
        pages=V.plan(data,entries)
        self.assertEqual([len(p) for p in pages],[3,3]);self.assertTrue(all(p[0]['heading'] for p in pages))
        with self.assertRaises(ValueError):V.plan(dict(data,pages=[dict(capacity=3)]),entries)

    def test_long_name_and_unused_target_clear(self):
        data=dict(pages=[dict(capacity=5),dict(capacity=5)],limit=18)
        entries=[dict(text='Штангенциркуль односторонний ШЦК-I-150',group=V.GROUPS[0])]
        pages=V.plan(data,entries)
        self.assertEqual(' '.join(r['text'] for r in pages[0][1:]),entries[0]['text'])
        self.assertEqual(pages[1],[])

    def test_latest_actual_file_captions(self):
        p=Path(__file__).parent.parent/'upload/ТП Р1Е60.100.01.cdw.bak'
        if not p.exists():self.skipTest('local reference absent')
        result=N.saved(p)
        self.assertEqual(len(result),22)
        self.assertEqual([N.short(x['name']) for x in result[2:4]],['МК ВО','МК ВО — продолжение'])
        self.assertEqual(N.short(result[17]['name']),'ОК ТК — карта контроля')
        self.assertIn('инструмент',N.short(result[9]['name']))

    def test_label_without_form_number(self):
        self.assertEqual(N.label((3,24,'МК ВО')),'Лист 4 · МК ВО')

    def test_read_collect_dedup_and_ke_actual_fields(self):
        class Text:
            def __init__(self,rows):self.rows=rows;self.Count=len(rows)
            def TextLine(self,i):return NS(Str=self.rows[i])
        class Stamp:
            def __init__(self,cells):self.cells=cells
            def Text(self,cid):return Text(self.cells.get(cid,[]))
        pages=[NS(Stamp=Stamp({6138:['Штангенциркуль'],6139:['односторонний ШЦК-I-150']})),
               NS(Stamp=Stamp({2002:['Сверло Ø6,5','Пластина CCMT'],2006:['Штангенциркуль односторонний ШЦК-I-150']}))]
        doc=NS(LayoutSheets=pages)
        with patch.object(N,'describe',return_value=[(0,18,'ОК ТК'),(1,5,'КЭ ЧПУ — инструмент')]),patch.object(V.X,'sheet_at',side_effect=lambda x,i:x[i]),patch.object(V.C,'signature',return_value={}):
            entries,_,_=V.collect(doc,None,'x',[0,1])
        self.assertEqual(len(entries),3);self.assertEqual(entries[0]['source'],[1,2])

    def test_changed_source_stops_before_mutation(self):
        data=dict(pages=[dict(index=1,capacity=3,old=[])],sources=[dict(index=0,signature={'v':1},cells={2000:['Т Сверло']})],count=2,limit=60)
        doc=NS(LayoutSheets=NS(Count=2))
        with patch('sketch.context',return_value=(None,None,None,None,doc,None)),patch.object(V.X,'sheet_at',return_value=NS(Stamp=None)),patch.object(V.C,'signature',return_value={'v':1}),patch.object(V,'text_lines',return_value=['Т Фреза']):
            with self.assertRaisesRegex(ValueError,'изменился'):V.write('x',data,[dict(text='Сверло',group='Режущая')])

    def test_dedup_even_if_user_assigned_different_groups(self):
        entries=[dict(text='Микрометр МК-25',group='Мерительная'),dict(text=' микрометр  МК-25 ',group='Прочая оснастка'),dict(text='Микрометр МК-50',group='Мерительная')]
        pages=V.plan(dict(pages=[dict(capacity=10)],limit=60),entries)
        self.assertEqual(sum(not r['heading'] and bool(r['text']) for r in pages[0]),2)

    def test_route_continuation_across_pages(self):
        out,active,pending=V.route_tools(['Т Штангенциркуль'],final=False)
        self.assertEqual(out,[])
        out,_,_=V.route_tools(['односторонний ШЦК-I-150','О Проверить'],active,pending)
        self.assertEqual(out,['Штангенциркуль односторонний ШЦК-I-150'])

    def test_write_selected_body_preserves_other_fields_and_fonts(self):
        import tempfile
        props=dict(Align=0,IndentedLine=0,LeftEdge=0,RightEdge=0,Step=6,StepAfterParagraph=0,StepBeforeParagraph=0)
        font=dict(FontName='GOST type A',Height=3.5,WidthFactor=1.,Italic=True,Bold=False,Underline=False,Color=0)
        class Line:
            def __init__(self,text):
                self.Str=text;self.Count=1;self.__dict__.update(props)
                self.item=NS(Str=text,ItemType=0,**font)
            def TextItem(self,i):self.item.Str=self.Str;return self.item
        class Text:
            def __init__(self,rows):self.rows=[Line(s) for s in rows]
            @property
            def Count(self):return len(self.rows)
            def TextLine(self,i):return self.rows[i]
            def Clear(self):self.rows=[];return True
            def Add(self):line=Line('');self.rows.append(line);return line
        class Stamp:
            def __init__(self):self.body=Text(['Мерительная','Старый прибор']);self.title='Золотник'
            Crossed=False
            def Text(self,cid):assert cid==2000;return self.body
            def Update(self):return True
            def GetNextColumnId(self,previous):return 2000 if previous<2000 else -1
        stamp=Stamp();untouched=Stamp();module=NS(ITextFont=lambda x:x,IKompasDocument1=lambda doc:NS(RedrawDocument=lambda mode:True))
        app=NS(ActiveDocument=NS(PathName='x'));doc5=NS(ksGetDocumentPagesCount=lambda:2)
        page=NS(Stamp=stamp);doc=NS(LayoutSheets=NS(Count=2))
        old=V.snapshot_text(stamp.body,module)
        template=dict(old[1],font=font)
        data=dict(count=2,sources=[],pages=[dict(index=1,signature={},old=old,capacity=10)],limit=60,heading=template,body=template)
        def commit(_,index,rows):
            stamp.body.Clear()
            for row in rows:stamp.body.rows.append(Line(row['text'] or ' '))
        def native_snapshot(*args):
            return [dict(text=r.Str,style=0,items=[dict(text=r.Str,type=0,font=font,flags=0)]) for r in stamp.body.rows]
        with tempfile.TemporaryDirectory() as folder,patch('sketch.context',return_value=(module,None,None,app,doc,doc5)),patch.object(V.C,'require_active'),patch.object(V,'native_read',return_value=old),patch.object(V,'native_styles',side_effect=native_snapshot),patch.object(V,'native_arrays',side_effect=lambda m,k,d,p:p),patch.object(V,'native_write',side_effect=commit),patch.object(V.X,'sheet_at',side_effect=lambda _,i:page if i==1 else NS(Stamp=untouched)),patch.object(V.C,'signature',return_value={}),patch.object(V.X,'backup_folder',return_value=Path(folder)),patch.object(V.J,'folder',return_value=Path(folder)):
            V.write('x',data,[dict(text='Микрометр МК-25',group='Мерительная')])
        self.assertEqual(V.text_lines(stamp,2000),['Мерительная','Микрометр МК-25'])
        self.assertEqual(stamp.title,'Золотник');self.assertEqual(V.text_lines(untouched,2000),['Мерительная','Старый прибор'])

    def test_unsaved_added_control_pages_use_same_library_reference(self):
        pages=[NS(LayoutStyleNumber=s,LayoutLibraryFileName='new\\TEHNOLOGI.LYT') for s in [18,20,21,22,24,19]]
        doc=NS(LayoutSheets=NS(Count=len(pages)))
        meta=[dict(style=18,library='new\\TEHNOLOGI.LYT',name='ОК ТК ф2'),dict(style=20,library='new\\TEHNOLOGI.LYT',name='ОК ТК ф2б')]
        with patch.object(N,'saved',return_value=meta):
            result=N.describe(doc,'x',lambda _,i:pages[i])
        self.assertTrue(all('ОК ТК' in result[i][2] for i in [0,1]))
        self.assertEqual(V.source_indices(result),[0,1,2,3])

    def test_ambiguous_number_without_metadata_is_not_a_writable_card(self):
        pages=[NS(LayoutStyleNumber=s,LayoutLibraryFileName='x') for s in [18,20,24,11]]
        doc=NS(LayoutSheets=NS(Count=4))
        with patch.object(N,'saved',return_value=[]):
            names=N.describe(doc,'x',lambda _,i:pages[i])
        self.assertEqual(V.source_indices(names),[])
        self.assertTrue(all(n[2]=='Название не определено' for n in names))

    def test_latest_tp_descriptions_survive_added_pages(self):
        p=Path(__file__).parent.parent/'upload/ТП Р1Е60.100.01.cdw.bak'
        if not p.exists():self.skipTest('local reference absent')
        meta=N.saved(p)
        pages=[NS(LayoutStyleNumber=r['style'],LayoutLibraryFileName=r['library']) for r in meta]
        pages.append(NS(LayoutStyleNumber=20,LayoutLibraryFileName=meta[-1]['library']))
        doc=NS(LayoutSheets=NS(Count=len(pages)))
        names=N.describe(doc,p,lambda _,i:pages[i])
        self.assertEqual([names[i][2] for i in range(5)],['ТЛ','ВТД','МК ВО','МК ВО — продолжение','КЭ'])
        self.assertEqual(names[-1][2],'ОК ТК — карта контроля')
        self.assertEqual(V.source_indices(names),[5,6,7,8,9,13,15,17,18,19,20,21,22])

    def test_native_read_selects_column_before_reading(self):
        calls=[]
        stamp=NS(SheetNumb=3,ksOpenStamp=lambda:1,ksColumnNumber=lambda cid:calls.append(cid) or 1,
                 ksGetStampColumnText=lambda _:('array',2000),ksCloseStamp=lambda:1)
        self.assertEqual(V.native_read(NS(ksDynamicArray=lambda a:a),NS(GetStampEx=lambda n:stamp),2),'array')
        self.assertEqual(calls,[2000])
        stamp.ksGetStampColumnText=lambda _:('wrong',2002)
        with self.assertRaisesRegex(RuntimeError,'другую графу'):V.native_read(NS(),NS(GetStampEx=lambda n:stamp),2)

    def test_native_stamp_uses_sheetnumb_property(self):
        # Реальный ksStamp (gen_py) не имеет метода GetSheetNumb, только свойство SheetNumb.
        class Stamp:
            SheetNumb=4
            def __getattr__(self,name):raise AttributeError(name)
        stamp=Stamp()
        self.assertIs(V.native_stamp(NS(GetStampEx=lambda n:stamp),3),stamp)
        with self.assertRaisesRegex(RuntimeError,'другого листа'):V.native_stamp(NS(GetStampEx=lambda n:stamp),2)

    def test_native_special_symbol_is_read_back(self):
        # Отчёт 13.10: КОМПАС вернул 'Калибр-скоба ', спецзнак (type 17, iSNumb 2), '11f7'.
        class Font:
            _prop_map_get_={'bitVector':0,'fontName':0,'height':0,'ksu':0,'color':0}
            def __init__(self):self.bitVector=0x1000;self.fontName='GOST type A';self.height=3.5;self.ksu=1.;self.color=0
        class Item:
            _prop_map_get_={'s':0,'type':0,'iSNumb':0}
            def Init(self):self.s='';self.type=0;self.iSNumb=0
            def GetItemFont(self):return Font()
        parts=[('Калибр-скоба ',0,0),('',17,2),('11f7',0,0)]
        items=NS(ksGetArrayCount=lambda:3,ksGetArrayItem=lambda j,it:it.__dict__.update(zip(('s','type','iSNumb'),parts[j])) or 1)
        line=NS(Init=lambda:None,style=0,GetTextItemArr=lambda:items)
        lines=NS(ksGetArrayCount=lambda:1,ksGetArrayItem=lambda i,target:1)
        mod5=NS(ksTextLineParam=lambda _:line,ksDynamicArray=lambda a:a)
        with patch('tooling.X._text_item_param',side_effect=lambda k:Item()):
            rows=V.native_styles(mod5,NS(GetParamStruct=lambda n:None),lines)
        self.assertEqual(rows[0]['text'],'Калибр-скоба @2~11f7')
        V.verify_text(rows,[dict(text='Калибр-скоба Ø11f7')],2,'API5')

    def test_native_font_style_default_flags(self):
        # Отчёт 13.10: заголовок флаги 0x1100 (API5), API7 — курсив по стилю.
        native=dict(FontName='GOST type A',Height=3.5,WidthFactor=1.,Color=0,Italic=None,Bold=True,Underline=None)
        api7=dict(FontName='GOST type A',Height=3.5,WidthFactor=1.,Italic=True,Bold=True,Underline=False,Color=0)
        self.assertTrue(V.same_native_font(native,api7))
        self.assertFalse(V.same_native_font(dict(native,Bold=False),api7))
        self.assertFalse(V.same_native_font(dict(native,Italic=False),api7))
        self.assertFalse(V.same_native_font(dict(native,Height=5.),api7))

    def test_restore_ignores_empty_component_dropped_by_kompas(self):
        bold=dict(FontName='GOST type A',Height=3.5,Bold=True)
        before=[dict(text='Токарная',style=0,items=[dict(text='Токарная',type=0,font=bold),dict(text='',type=0,font={})])]
        after=[dict(text='Токарная',style=0,items=[dict(text='Токарная',type=0,font=bold)])]
        self.assertEqual(V.without_empty(after),V.without_empty(before))

    def test_formatting_check_names_mismatch_and_ignores_step(self):
        font=dict(FontName='GOST type A',Height=3.5,WidthFactor=1.,Italic=True,Bold=False,Underline=False,Color=0)
        props=dict(Align=0,Step=8.25)
        data=dict(heading=dict(props=props,font=dict(font,Bold=True)),body=dict(props=props,font=font))
        line=lambda f,st:dict(text='Сверла',props=dict(Align=0,Step=st),runs=[dict(text='Сверла',type=0,font=f)])
        V.verify_written([line(font,5.0)],[dict(text='Сверла',heading=False)],data,2)
        with self.assertRaisesRegex(RuntimeError,"строка 1 .*Height 5.0 вместо 3.5"):
            V.verify_written([line(dict(font,Height=5.0),8.25)],[dict(text='Сверла',heading=False)],data,2)

    def test_first_difference_names_field(self):
        a=[dict(text='x',style=0)];b=[dict(text='x',style=5)]
        self.assertIn('style',V.first_difference(a,b))
        self.assertIn('отсутствует',V.first_difference([],b))

    def test_route_code_without_space(self):
        # МК листы 6/7 (13.10): 'ТШабер…', 'О1. …', строка операции без 'А'.
        rows=['А 020 Слесарная','О      Снять заусенцы','ТШабер Mango II комплект Е 155-90065, Надфили ГОСТ 1513-77',
              'А 025 Контроль','                030      Шлифовальная ЧПУ   1,1','Т      Круг абразивный 1300-25-127 25А60 J V 35m/sB',
              '                045    Покрытие Хим. Нб. 35','О1. Упаковать детали в тару.','Токарная обработка']
        self.assertEqual(V.route_tools(rows)[0],['Шабер Mango II комплект Е 155-90065, Надфили ГОСТ 1513-77',
                                                 'Круг абразивный 1300-25-127 25А60 J V 35m/sB'])

    def test_two_tools_without_separator_are_split(self):
        self.assertEqual(V.split_tools('Державка резьбовая SER 1616 H16 Резьбонарезная пластина AG60 ER16'),
                         ['Державка резьбовая SER 1616 H16','Резьбонарезная пластина AG60 ER16'])
        self.assertEqual(V.split_tools('Круг абразивный 1300-25-127 25А60 J V 35m/sB'),['Круг абразивный 1300-25-127 25А60 J V 35m/sB'])
        self.assertEqual(V.split_tools('Сверло центровочное 1X5X2X35'),['Сверло центровочное 1X5X2X35'])

    def test_group_order_cutting_grinding_fitter_measuring(self):
        entries=[dict(text=t,group=g) for t,g in [('Микрометр',V.GROUPS[0]),('Очки',V.GROUPS[2]),('Круг',V.GROUPS[3]),
                                                   ('Резец',V.GROUPS[1]),('Тиски',V.GROUPS[4])]]
        data=dict(pages=[dict(capacity=40)],limit=60)
        heads=[r['text'] for r in V.plan(data,entries)[0] if r['heading']]
        self.assertEqual(heads,['Режущая','Шлифовальная','Слесарная','Мерительная','Приспособления'])

    def test_overflow_message_counts_rows(self):
        entries=[dict(text='Резец %d'%i,group=V.GROUPS[1]) for i in range(20)]+[dict(text='Очки %d'%i,group=V.GROUPS[2]) for i in range(20)]
        data=dict(pages=[dict(capacity=17),dict(capacity=17)],limit=85)
        with self.assertRaisesRegex(ValueError,'нужно 42 строк.*— 34.*8 строк'):V.plan(data,entries)
        # 15+14 items + 2 headings = 31 rows: fits with the blank separator.
        planned=V.plan(data,entries[:15]+entries[20:34])
        self.assertEqual(sum(map(len,planned)),32)
        # 16+16 items + 2 headings = 34: fits only without the separator.
        planned=V.plan(data,entries[:16]+entries[20:36])
        self.assertEqual(sum(map(len,planned)),34)
        self.assertFalse(any(not r['text'] for rows in planned for r in rows))

    def test_ke_wrapped_model_is_one_position(self):
        rows=['Сверло твердосплавное','WPC-UNI.4,5.R.3D.DIN6535. HB TIALN','','Пластина CCMT 060202']
        self.assertEqual(V.joined_instruments(rows),['Сверло твердосплавное WPC-UNI.4,5.R.3D.DIN6535. HB TIALN','Пластина CCMT 060202'])

    def test_known_other_caption_is_not_overridden_by_control_fallback(self):
        doc=NS(LayoutSheets=NS(Count=1))
        sh=NS(LayoutStyleNumber=20,LayoutLibraryFileName='x')
        with patch.object(N,'saved',return_value=[dict(style=20,library='x',name='МК ВО л1 нов')]):
            result=N.describe(doc,'x',lambda _,i:sh)
        self.assertEqual(result[0][2],'МК ВО');self.assertEqual(V.source_indices(result),[])

    def test_native_commit_uses_stamp_editing_and_closes_on_failure(self):
        calls=[]
        stamp=NS(SheetNumb=4,ksOpenStamp=lambda:calls.append('open') or 1,
                 ksColumnNumber=lambda cid:calls.append(('select',cid)) or 1,
                 ksSetStampColumnText=lambda cid,arr:calls.append(('write',cid,arr)) or 0,
                 ksCloseStamp=lambda:calls.append('close') or 1)
        doc=NS(GetStampEx=lambda n:stamp)
        with self.assertRaises(RuntimeError):V.native_write(doc,3,'lines')
        self.assertEqual(calls,['open',('select',2000),('write',2000,'lines'),'close'])
