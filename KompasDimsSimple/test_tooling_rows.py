"""MK VO layouts 200/24: one stamp cell per body row (3456…3472)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import tooling as V

FONT=dict(FontName='GOST type A',Height=3.5,WidthFactor=1.0,Italic=True,Bold=False,Underline=False,Color=0)


class Sheet:
    def __init__(self,style,cells,layout):
        self.LayoutStyleNumber=style;self.LayoutLibraryFileName='C:\\TEHNOLOGI.LYT'
        self.cells=dict(cells);self.layout=set(layout)
        self.Stamp=NS(Crossed=False,GetNextColumnId=self.next_id)
    def next_id(self,previous):
        # Like KOMPAS: only filled cells that exist in the layout.
        return next((c for c in sorted(self.cells) if c>previous and c in self.layout and self.cells[c][0].strip()),-1)


class Env:
    def __init__(self,layout=V.ROW_IDS[200]):
        self.sheets={2:Sheet(200,{3440:('Мерительная',FONT),3441:('1. ',FONT),3456:('А1',FONT)},set(layout)|{3440,3441}),
                     3:Sheet(24,{},layout)}
        self.writes=[];self.app=NS(ActiveDocument=NS(PathName='x'))
        self.doc=NS(LayoutSheets=NS(Count=23))
        self.desc=[(i,0,'—') for i in range(23)];self.desc[2]=(2,200,'МК ВО');self.desc[3]=(3,24,'МК ВО — продолжение')
    def write_one(self,doc5,k5,sheet,cid,text,font):
        self.writes.append((sheet,cid,text,font.get('Bold')));self.sheets[sheet].cells[cid]=(V.X.safe(text) if text else ' ',dict(font))
    def read_cell(self,stamp,cid,module):
        sheet=next(s for s in self.sheets.values() if s.Stamp is stamp)
        text,font=sheet.cells.get(cid,('',{}))
        return dict(id=cid,text=text,font=dict(font) if text.strip() else {},count=1)
    def patch(self,folder):
        from contextlib import ExitStack
        st=ExitStack()
        st.enter_context(patch('sketch.context',return_value=(NS(),NS(),NS(),self.app,self.doc,NS())))
        st.enter_context(patch.object(V.X,'sheet_at',side_effect=lambda _,i:self.sheets.get(i) or Sheet(0,{},())))
        st.enter_context(patch.object(V.N,'describe',return_value=self.desc))
        st.enter_context(patch.object(V,'collect',return_value=([dict(text='Калибр-скоба Ø11f7',group=V.GROUPS[0],source=[21]),
                                                                  dict(text='Пластина WNMG 160808',group=V.GROUPS[1],source=[12])],[],[])))
        st.enter_context(patch.object(V.X,'write_one',side_effect=self.write_one))
        st.enter_context(patch.object(V.X,'read_cell',side_effect=self.read_cell))
        st.enter_context(patch.object(V.C,'signature',side_effect=lambda sh:dict(style=sh.LayoutStyleNumber)))
        st.enter_context(patch.object(V,'refresh_document'))
        st.enter_context(patch.object(V.X,'backup_folder',return_value=Path(folder)))
        st.enter_context(patch.object(V.J,'folder',return_value=Path(folder)))
        return st


class Rows(unittest.TestCase):
    def test_rows_are_written_one_per_cell(self):
        env=Env()
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',[20],[2,3])
            self.assertEqual(data['mode'],'rows');self.assertEqual(data['pages'][0]['capacity'],17)
            self.assertEqual(data['group_names'],{})
            self.assertEqual(V.write('x',data,data['entries']),2)
        cells=env.sheets[2].cells
        self.assertEqual([cells.get(c,('',))[0].strip() for c in range(3456,3461)],
                         ['Мерительная','Калибр-скоба @2~11f7','','Режущая','Пластина WNMG 160808'])
        self.assertTrue(cells[3456][1]['Bold']);self.assertFalse(cells[3457][1]['Bold'])
        self.assertEqual(cells[3440][0],'Мерительная')  # other cells untouched
        self.assertFalse(any(sheet==3 for sheet,*_ in env.writes))  # nothing for the empty 2nd page

    def test_cell_missing_from_layout_fails_and_restores(self):
        env=Env(layout=range(3456,3458))  # row 3+ not in the layout
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',[20],[2,3])
            with self.assertRaisesRegex(RuntimeError,'восстановлены и проверены[\\s\\S]*графы 3459 нет в оформлении'):
                V.write('x',data,data['entries'])
        self.assertEqual(env.sheets[2].cells[3456][0],'А1')
        self.assertEqual(env.sheets[2].cells.get(3459,('',))[0].strip(),'')

    def test_changed_rows_block_write(self):
        env=Env()
        with tempfile.TemporaryDirectory() as folder,env.patch(folder):
            data=V.read('x',[20],[2]);env.sheets[2].cells[3457]=('новое',FONT)
            with self.assertRaisesRegex(ValueError,'изменилась'):V.write('x',data,data['entries'])
        self.assertEqual(env.writes,[])


if __name__=='__main__':
    unittest.main()
