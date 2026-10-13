"""Номер листа в документе: план по составу ТП и проверяемая запись."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import numbering as P

DESC=[(0,1,'ТЛ'),(1,180,'ВТД'),(2,24,'МК ВО — продолжение'),(3,24,'МК ВО — продолжение'),(4,11,'КЭ'),
      (5,21,'МК — маршрутная карта'),(6,22,'МК — маршрутная карта (продолжение)'),(7,22,'МК — маршрутная карта (продолжение)'),
      (8,4,'КЭ ЧПУ'),(9,5,'КЭ ЧПУ — инструмент'),(10,19,'КЭ ЧПУ — эскиз'),(11,4,'КЭ ЧПУ'),(12,19,'КЭ ЧПУ — эскиз'),
      (13,18,'ОК ТК — карта контроля'),(14,20,'ОК ТК — карта контроля')]


class Plan(unittest.TestCase):
    def test_pages_restart_on_main_sheet_and_on_new_document_type(self):
        rows={r['index']:r for r in P.plan(DESC)}
        self.assertEqual([(rows[i]['page'],rows[i]['cell']) for i in (2,3)],[(1,0),(2,0)])  # МК ВО после ВТД
        self.assertEqual([rows[i]['page'] for i in (5,6,7)],[1,2,3])
        self.assertEqual([(rows[i]['page'],rows[i]['cell']) for i in (9,10)],[(2,1813),(3,1813)])
        self.assertEqual(rows[12]['page'],2)  # второй КЭ ЧПУ начинается с главного листа
        self.assertIsNone(rows[14]['cell']);self.assertIn('неизвестна',rows[14]['action'])
        self.assertIn('главный',rows[0]['action'])


class StyleNumbersDiffer(unittest.TestCase):
    def test_style_20_mk_vo_is_main_sheet_and_ok_tk_20_is_continuation(self):
        # «ТП … тест.cdw»: МК ВО оформлен стилем 20 другой библиотеки
        rows=P.plan([(1,180,'ВТД'),(2,20,'МК ВО'),(3,24,'МК ВО — продолжение'),(4,18,'ОК ТК — карта контроля'),(5,20,'ОК ТК — карта контроля')])
        self.assertIn('главный',rows[1]['action'])
        self.assertEqual((rows[2]['page'],rows[2]['cell']),(2,0))
        self.assertEqual(rows[4]['page'],2);self.assertIn('неизвестна',rows[4]['action'])

    def test_update_returning_false_is_not_an_error(self):
        text=NS(Str='')
        stamp=NS(Text=lambda cid:text,Update=lambda:False)
        with patch.object(P.X,'sheet_at',return_value=NS(Stamp=stamp)):P.write_cell(NS(),NS(LayoutSheets=None),12,1813,'5')
        self.assertEqual(text.Str,'5')


class Sheet:
    def __init__(self,cells,layout):
        self.cells=dict(cells);self.layout=set(layout);self.Stamp=NS(GetNextColumnId=self.next_id)
    def next_id(self,previous):
        filled=[c for c in sorted(self.cells) if c in self.layout and self.cells[c].strip()]
        i=filled.index(previous)+1 if previous in filled else (0 if previous==-1 else len(filled))
        return filled[i] if i<len(filled) else -1


class Api7Cell(unittest.TestCase):
    def test_cell_zero_written_through_api7_without_clearing_stamp(self):
        calls=[];text=NS(Str='')
        stamp=NS(Text=lambda cid:calls.append(('text',cid)) or text,Update=lambda:calls.append('update') or True)
        doc=NS(LayoutSheets=None)
        with patch.object(P.X,'sheet_at',return_value=NS(Stamp=stamp)):P.write_cell(NS(),doc,3,0,'2')
        self.assertEqual(text.Str,'2');self.assertEqual(calls,[('text',0),'update'])


class Write(unittest.TestCase):
    def env(self,layout13=(0,7)):
        sheets={i:Sheet({},(0,1813)) for i in range(15)}
        sheets.update({6:Sheet({0:'2',7:'7'},(0,7)),7:Sheet({7:'8'},layout13),9:Sheet({1813:'5'},(1813,))})
        writes=[]
        def write_cell(module,doc,sheet,cid,text):writes.append((sheet,cid,text));sheets[sheet].cells[cid]=text
        def read_cell(stamp,cid,module):
            sh=next(s for s in sheets.values() if s.Stamp is stamp);t=sh.cells.get(cid,'')
            return dict(id=cid,text=t,font={'Height':3.5} if t else {},count=1)
        app=NS(ActiveDocument=NS(PathName='x'))
        doc=NS(LayoutSheets=NS(Count=15))
        st=[patch('sketch.context',return_value=(NS(),NS(),NS(),app,doc,NS())),
            patch.object(P.X,'sheet_at',side_effect=lambda _,i:sheets[i]),
            patch.object(P,'write_cell',side_effect=write_cell),
            patch.object(P.X,'write_one',side_effect=AssertionError('ksClearStamp(0) clears the whole stamp')),patch.object(P.X,'read_cell',side_effect=read_cell),
            patch.object(P.V,'refresh_document'),patch.object(P.K,'connect',return_value=(NS(),NS())),
            patch.object(P.X,'open_doc',return_value=doc),patch.object(P.N,'describe',return_value=DESC)]
        return sheets,writes,st

    def run_with(self,st,fn):
        with tempfile.TemporaryDirectory() as folder:
            for p in st:p.start()
            try:
                with patch.object(P.X,'backup_folder',return_value=Path(folder)):return fn()
            finally:
                for p in st:p.stop()

    def test_writes_only_wrong_or_missing_numbers(self):
        sheets,writes,st=self.env()
        result=self.run_with(st,lambda:P.write('x',P.read('x')))
        self.assertEqual(result,(6,''))  # листы 3,4,8 (графа 0) и 10,11,13 (1813)
        self.assertNotIn(6,[w[0] for w in writes])  # лист 7 уже «2»
        self.assertEqual(sheets[7].cells[0],'3');self.assertEqual(sheets[9].cells[1813],'2')

    def test_missing_layout_cell_restores_previous_numbers(self):
        sheets,writes,st=self.env(layout13=(7,))
        def go():
            data=P.read('x')
            with self.assertRaisesRegex(RuntimeError,'Прежние номера восстановлены[\\s\\S]*графы 0 нет в оформлении'):P.write('x',data)
        self.run_with(st,go)
        self.assertEqual(sheets[7].cells.get(0,''),'')
