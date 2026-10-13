"""Roundtrip the real TP text fixture through both simulated COM interfaces.

This checks routing and payload construction. It does not run KOMPAS.
"""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import tooling as V
import sheet_names as N

PROPS=dict(Align=0,IndentedLine=0.,LeftEdge=0.,RightEdge=0.,Step=0.,
           StepAfterParagraph=0.,StepBeforeParagraph=0.)
FONT=dict(FontName='GOST type A',Height=3.5,WidthFactor=1.,Italic=True,
          Bold=False,Underline=False,Color=0)


class Item:
    def Init(self):
        self.s='';self.type=0
        self.font=NS(fontName='GOST type A',height=3.5,ksu=1.,color=0,bitvector=0)
        return True
    def GetItemFont(self):return self.font
    def SetItemFont(self,font):self.font=font;return True


class Array:
    def __init__(self,kind):self.kind=kind;self.rows=[]
    def ksAddArrayItem(self,_,item):self.rows.append(copy.deepcopy(item));return 1
    def ksGetArrayCount(self):return len(self.rows)
    def ksGetArrayItem(self,index,target):target.__dict__.update(copy.deepcopy(self.rows[index].__dict__));return 1


class NativeLine:
    def Init(self):self.style=0;self.items=Array(4);return True
    def SetTextItemArr(self,items):self.items=copy.deepcopy(items);return True
    def GetTextItemArr(self):return self.items


class Line:
    def __init__(self,text,style=None,font=None):
        self.Str=text;self.Count=1;self.__dict__.update(PROPS)
        heading=V.clean(text).casefold() in V.HEADINGS
        self._native_style=style if style is not None else 9013 if heading else 8997
        self.font=dict(font or dict(FONT,Bold=heading))
    def TextItem(self,_):return NS(Str=self.Str,ItemType=0,**self.font)


class Text:
    def __init__(self,rows):self.rows=[Line(s) for s in rows]
    @property
    def Count(self):return len(self.rows)
    def TextLine(self,i):return self.rows[i]


class Stamp:
    def __init__(self,fields):self.fields={int(cid):Text(rows) for cid,rows in fields.items()};self.Crossed=False;self.hidden=set()
    def Update(self):self.Crossed=False;return True
    def Text(self,cid):return self.fields.get(cid,Text([]))
    def GetNextColumnId(self,previous):
        # hidden: IDs that the sheet layout does not contain (not enumerated).
        return next((cid for cid in sorted(self.fields) if cid>previous and self.fields[cid].Count and cid not in self.hidden),-1)


class NativeStamp:
    def __init__(self,env,index):self.env=env;self.index=index;self.cid=None;self.selected=False;self.enum_index=0
    @property
    def SheetNumb(self):return self.index+1
    def ksOpenStamp(self):return 1
    def ksCloseStamp(self):return 1
    def ksColumnNumber(self,cid):self.cid=cid;self.selected=True;return 1
    def ksGetStampColumnText(self,_):
        if not self.selected:
            ids=sorted(cid for cid,t in self.env.pages[self.index].Stamp.fields.items() if t.Count)
            if self.enum_index==len(ids):return None,0
            self.cid=ids[self.enum_index];self.enum_index+=1
        arr=Array(3)
        source=self.env.pages[self.index].Stamp.Text(self.cid)
        if self.cid==2000:source=self.env.native_override.get(self.index,source)
        for row in source.rows:
            line=NativeLine();line.Init();line.style=row._native_style
            item=Item();item.Init();item.s=row.Str+'\n';V.X.set_font(item,row.font)
            line.items.ksAddArrayItem(-1,item);arr.ksAddArrayItem(-1,line)
        return arr,self.cid
    def ksSetStampColumnText(self,cid,array):
        assert cid==2000
        assert self.cid==2000
        self.env.writes.append(self.index)
        before=copy.deepcopy(self.env.pages[self.index].Stamp.Text(cid))
        text=Text([])
        for native in array.rows:
            # Emulate the SDK stream: without explicit separators adjacent
            # text records join. This caught the 1.4.1/1.4.2 payload mistake.
            value=''.join(i.s for i in native.items.rows)
            item=native.items.rows[0] if native.items.rows else None
            if item:
                f=item.font
                font=dict(FontName=f.fontName,Height=f.height,WidthFactor=f.ksu,
                          Italic=bool(f.bitvector&0x40),Bold=bool(f.bitvector&0x100),
                          Underline=bool(f.bitvector&0x400),Color=f.color)
            else:font=FONT
            if value.endswith('\n'):
                text.rows.append(Line(value[:-1],native.style,font))
            elif text.rows:
                text.rows[-1].Str+=value
            else:text.rows.append(Line(value,native.style,font))
        self.env.pages[self.index].Stamp.fields[cid]=text
        if self.env.stale_native_sheet==self.index and not self.env.failed:
            self.env.failed=True;self.env.native_override[self.index]=before
        else:self.env.native_override.pop(self.index,None)
        if self.env.fail_sheet==self.index and not self.env.failed:
            self.env.failed=True
            if text.rows:text.rows.pop(0)
        return 1


class Env:
    def __init__(self):
        data=json.loads((Path(__file__).parent/'tp_fixture.json').read_text(encoding='utf-8'))
        self.records=data['sheets'];self.pages=[];self.writes=[];self.fail_sheet=None;self.failed=False
        self.stale_native_sheet=None;self.native_override={};self.redraws=0;self.redraw_result=True
        for row in self.records:
            fields=dict(row['fields']);fields['1']=['Золотник'];fields['2110']=['Р1Е60.100.01']
            self.pages.append(NS(Stamp=Stamp(fields),LayoutStyleNumber=row['style'],
                                 LayoutLibraryFileName=row['library']))
        self.doc=NS(LayoutSheets=NS(Count=len(self.pages)))
        self.app=NS(ActiveDocument=NS(PathName='x'))
        self.mod7=NS(ITextFont=lambda item:item)
        self.mod7.IKompasDocument1=lambda doc:NS(RedrawDocument=self.redraw)
        self.mod5=NS(ksTextLineParam=lambda line:line,ksDynamicArray=lambda arr:arr)
        self.k5=NS(GetParamStruct=lambda _:NativeLine(),GetDynamicArray=lambda kind:Array(kind))
        self.doc5=NS(GetStampEx=lambda n:NativeStamp(self,n-1),ksGetDocumentPagesCount=lambda:len(self.pages))
        self.meta=[dict(style=r['style'],library=r['library'],name=r['name']) for r in self.records]
    def redraw(self,mode):
        assert mode==0
        self.redraws+=1;return self.redraw_result
    def patch(self,folder):
        from contextlib import ExitStack
        stack=ExitStack()
        stack.enter_context(patch('sketch.context',return_value=(self.mod7,self.mod5,self.k5,self.app,self.doc,self.doc5)))
        stack.enter_context(patch.object(V.X,'sheet_at',side_effect=lambda _,i:self.pages[i]))
        stack.enter_context(patch.object(N,'saved',return_value=self.meta))
        stack.enter_context(patch.object(V.C,'signature',side_effect=lambda sh:dict(style=sh.LayoutStyleNumber,library=sh.LayoutLibraryFileName)))
        stack.enter_context(patch.object(V.X,'_text_item_param',side_effect=lambda _:Item()))
        stack.enter_context(patch.object(V.X,'backup_folder',return_value=Path(folder)))
        stack.enter_context(patch.object(V.J,'folder',return_value=Path(folder)))
        return stack


class RoundTrip(unittest.TestCase):
    def test_all_fixture_tools_roundtrip_with_automatic_spacing(self):
        env=Env()
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[2,3])
            self.assertEqual(len(data['entries']),28)
            self.assertEqual(data['pages'][1]['height'],140.25)
            V.write('x',data,data['entries'])
            report=json.loads(next(Path(folder).glob('tooling_*.json')).read_text(encoding='utf-8'))
            self.assertEqual(len(report['readback']),2)
            self.assertEqual(len(env.writes),2)

    def test_failed_second_page_restores_both_in_reverse_order(self):
        env=Env();env.fail_sheet=3
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[2,3]);data['pages'][0]['capacity']=2;data['pages'][1]['capacity']=10
            chosen=[e for e in data['entries'] if e['text'] in ['Микрометр МК-25 Mitutoyo','Державка PСLNL 1616H-06']]
            with self.assertRaisesRegex(RuntimeError,'восстановлены и проверены'):
                V.write('x',data,chosen)
            self.assertEqual(env.writes,[2,3,3,2])
            for page in data['pages']:
                self.assertEqual(V.snapshot_text(env.pages[page['index']].Stamp.Text(2000),env.mod7),page['old'])
            report=json.loads(next(Path(folder).glob('tooling_*.json')).read_text(encoding='utf-8'))
            self.assertTrue(report['restored']);self.assertIn('строка',report['error'])

    def test_real_source_fields_and_full_native_roundtrip(self):
        env=Env()
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[2,3])
            names=[e['text'] for e in data['entries']]
            self.assertIn('Державка PСLNL 1616H-06',names)  # First KE sheet 9.
            self.assertIn('Сверло твердосплавное WPC-UNI.4,5.R.3D.DIN6535. HB TIALN',names)
            self.assertIn('Микрометр МК-25 Mitutoyo',names)  # Merged control col 2001.
            self.assertIn('Калибр-скоба ∅11f7',names)
            self.assertEqual(len(names),len({V.key(n) for n in names}))
            self.assertEqual(names.count('Штангенциркуль односторонний ШЦК-I-150'),1)
            self.assertFalse(any(n.startswith('Обеспеч') for n in names))
            self.assertEqual(data['heading']['style'],9013)
            self.assertEqual(data['body']['style'],8997)
            before=[copy.deepcopy(p.Stamp.fields) for p in env.pages]
            # A deliberately small selection fits both chosen pages and tests
            # headings, empty separators, diameter escape, and two tool groups.
            chosen=[e for e in data['entries'] if e['text'] in ['Микрометр МК-25 Mitutoyo','Калибр-скоба ∅11f7','Державка PСLNL 1616H-06']]
            data['pages'][0]['capacity']=3
            data['pages'][1]['capacity']=10
            planned=V.plan(data,chosen)
            self.assertTrue(any(r['text']=='Токарная' for rows in planned for r in rows))
            V.write('x',data,chosen)
            self.assertEqual(env.writes,[2,3])
            for page,rows in zip(data['pages'],planned):
                actual=V.snapshot_text(env.pages[page['index']].Stamp.Text(2000),env.mod7)
                V.verify_written(actual,rows,data,page['index'])
            for i,p in enumerate(env.pages):
                for cid,old in before[i].items():
                    if i in [2,3] and cid==2000:continue
                    self.assertEqual(V.snapshot_text(p.Stamp.Text(cid),env.mod7),V.snapshot_text(old,env.mod7))

    @patch.object(V,'ROW_IDS',{})  # legacy single-cell (2000) layouts
    def test_empty_selected_page_uses_unselected_sample(self):
        env=Env();env.pages[3].Stamp.fields[2000]=Text([])
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[3])
            self.assertEqual([p['index'] for p in data['pages']],[3])
            self.assertEqual(data['heading']['sample'],2)
            self.assertEqual(data['body']['sample'],2)

    def test_api7_text_without_native_commit_is_not_success(self):
        env=Env();env.stale_native_sheet=2
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[2,3])
            with self.assertRaisesRegex(RuntimeError,'API5: текст'):
                V.write('x',data,[dict(text='Микрометр новый',group=V.GROUPS[0])])
            self.assertEqual(env.writes,[2,2])
            report=json.loads(next(Path(folder).glob('tooling_*.json')).read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'rolled_back');self.assertTrue(report['restored'])
            self.assertIn('native_actual',report['readback'][0])
            self.assertEqual(V.snapshot_text(env.pages[2].Stamp.Text(2000),env.mod7),data['pages'][0]['old'])

    def test_redraw_failure_is_reported_and_data_restored(self):
        env=Env();env.redraw_result=False
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[2,3])
            with self.assertRaisesRegex(RuntimeError,'RedrawDocument'):
                V.write('x',data,[dict(text='Микрометр новый',group=V.GROUPS[0])])
            self.assertEqual(env.writes,[2,2])
            self.assertEqual(V.snapshot_text(env.pages[2].Stamp.Text(2000),env.mod7),data['pages'][0]['old'])
            report=json.loads(next(Path(folder).glob('tooling_*.json')).read_text(encoding='utf-8'))
            self.assertTrue(report['restored']);self.assertIn('restore_redraw_error',report)

    def test_success_contains_two_readbacks_and_redraws(self):
        env=Env()
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[2,3]);V.write('x',data,data['entries'])
            self.assertEqual(env.redraws,2)
            report=json.loads(next(Path(folder).glob('tooling_*.json')).read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'verified_api5_api7_redrawn')
            self.assertTrue(all('actual' in r and 'native_actual' in r for r in report['readback']))

    def test_diagnostics_enumerates_cells_without_writing(self):
        env=Env()
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            result=V.diagnose('x',[2,3]);self.assertIn('совпали',result)
            self.assertEqual(env.writes,[]);self.assertEqual(env.redraws,1)
            report=json.loads(next(Path(folder).glob('tooling_diagnostic_*.json')).read_text(encoding='utf-8'))
            self.assertEqual(len(report['sheets']),2)
            self.assertIn('2000',report['sheets'][0]['api5'])
            self.assertIn('2110',report['sheets'][0]['api5'])

    def test_filled_cell_missing_from_layout_is_rejected_before_write(self):
        # Журнал 13.10: МК ВО (стили 200/24) не содержит графы 2000.
        env=Env();env.pages[2].Stamp.hidden.add(2000)
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            with self.assertRaisesRegex(ValueError,'Графы 2000 нет'):V.read('x',None,[2])
            self.assertEqual(env.writes,[])

    @patch.object(V,'ROW_IDS',{})  # legacy single-cell (2000) layouts
    def test_write_to_cell_missing_from_layout_is_not_success(self):
        env=Env();env.pages[3].Stamp.fields[2000]=Text([]);env.pages[3].Stamp.hidden.add(2000)
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[3])
            with self.assertRaisesRegex(RuntimeError,'Графы 2000 нет[\\s\\S]*восстановлены и проверены|восстановлены и проверены[\\s\\S]*Графы 2000 нет'):
                V.write('x',data,[dict(text='Микрометр новый',group=V.GROUPS[0])])
            self.assertEqual(env.writes,[3,3])

    def test_diagnostics_reports_invisible_cell(self):
        env=Env();env.pages[2].Stamp.hidden.add(2000)
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            result=V.diagnose('x',[2])
            self.assertIn('не видны',result);self.assertEqual(env.writes,[])

    def test_pending_stamp_is_updated_and_rechecked(self):
        env=Env();env.pages[2].Stamp.Crossed=True
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',None,[2,3]);V.write('x',data,data['entries'])
            self.assertFalse(env.pages[2].Stamp.Crossed)

    def test_wrong_native_sheet_stops_before_writing(self):
        env=Env();env.doc5.GetStampEx=lambda n:NativeStamp(env,n)  # Deliberate off-by-one.
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            with self.assertRaisesRegex(RuntimeError,'штамп другого листа'):V.read('x',None,[2,3])
            self.assertEqual(env.writes,[])

