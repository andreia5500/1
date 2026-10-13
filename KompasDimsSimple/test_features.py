import unittest
from types import SimpleNamespace as N
from unittest.mock import patch
import kompas_dims as K
import instruments as I
import layout as L
import requirements as R
import cards as C
import transfer as X


def dim(kind=K.KIND_OUTER, value=12, hi=0, lo=-.1, view='Главный вид'):
    d=K.Dim();d.kind=kind;d.value=value;d.hi=hi;d.lo=lo;d.view=view;d.src=K.SRC_DRAWING
    I.assign([d]);return d


class Features(unittest.TestCase):
    def test_threshold_and_symmetric_width(self):
        self.assertEqual(dim(hi=.05,lo=-.05).instrument,I.CALIPER)
        self.assertEqual(dim(hi=0,lo=-.099).instrument,I.MICROMETER)
        self.assertEqual(dim(hi=-.002,lo=-.004).instrument,I.MICROMETER)
        self.assertEqual(dim(hi=.1,lo=0).instrument,I.CALIPER)

    def test_instrument_ranges_include_limits(self):
        self.assertEqual(dim(value=30,lo=-.01).instrument,I.MICROMETER_50)
        self.assertEqual(dim(value=25,hi=.01,lo=-.01).instrument,I.MANUAL)
        self.assertEqual(dim(value=100,lo=-.01).instrument,I.MANUAL)
        self.assertEqual(dim(K.KIND_INNER,value=9,hi=.02,lo=0).instrument,'Нутромер микрометрический трехточечный НМТ 8-10')
        self.assertIn('40-50',dim(K.KIND_INNER,value=44,hi=.02,lo=0).instrument)
        self.assertEqual(dim(K.KIND_LINEAR,value=151).instrument,I.MANUAL)

    def test_linear_and_override(self):
        d=dim(K.KIND_LINEAR,lo=-.01);self.assertEqual(d.instrument,I.CALIPER)
        d.instrument_manual=True;d.instrument='Мой прибор';I.assign([d]);self.assertEqual(d.instrument,'Мой прибор')

    def test_geometry_not_guessed(self):
        d=dim(K.KIND_FORM_TOL);d.tol_sign=22
        self.assertEqual(I.suggest(d),I.MANUAL)

    def test_catalog_full(self):
        self.assertEqual(len(I.CATALOG),54)
        self.assertIn(I.MICROMETER_50,I.CATALOG)
        self.assertIn('Нутромер микрометрический трехточечный НМТ 25-30',I.CATALOG)

    def test_group_by_view_then_instrument(self):
        a=dim(value=11);b=dim(value=12,lo=-.01);c=dim(value=13);e=dim(value=14,view='Вид слева')
        groups=L.groups([a,b,e,c])
        self.assertEqual([(g['view'],g['instrument']) for g in groups],[(a.view,I.CALIPER),(a.view,I.MICROMETER),(e.view,I.CALIPER)])
        self.assertIn('11',groups[0]['params'][0]);self.assertIn('13',groups[0]['params'][0])
        self.assertNotIn('12',groups[0]['params'][0])

    def test_distinct_views_same_label_stay_separate(self):
        a,b=dim(view='A'),dim(view='B');a.view_label=b.view_label='Главный вид'
        self.assertEqual(len(L.groups([a,b])),2)

    def test_pagination_no_loss_repeat_heading_and_tool(self):
        groups=[dict(view='a',label='Главный вид',instrument=I.CALIPER,params=['p%d'%i for i in range(35)])]
        pages=L.paginate(groups,[13,17],extra_capacity=17)
        self.assertEqual(len(pages),3)
        actual=[]
        for page in pages:
            self.assertEqual(page[0],L.empty_row())
            self.assertTrue(page[1]['bold']);self.assertEqual(page[1]['text'],'Главный вид:')
            self.assertTrue(page[2]['instrument'].startswith('Штангенциркуль'))
            actual.extend(r['text'] for r in page[2:] if r['text'])
        self.assertEqual(actual,groups[0]['params'])

    def test_no_orphan_heading(self):
        group=dict(view='a',label='Сечение А-А',instrument='Прибор',params=['20'])
        pages=L.paginate([group],[13,17],start=11)
        self.assertEqual(pages[0],[None]*11)
        self.assertEqual([r['text'] for r in pages[1]],['','Сечение А-А:','20',''])

    def test_long_instrument_moves_whole(self):
        a=dict(view='a',label='A',instrument='X',params=['p']*10)
        b=dict(view='a',label='A',instrument=I.MICROMETER_50,params=['q'])
        pages=L.paginate([a,b],[13,17])
        self.assertEqual(len(pages),2)
        self.assertEqual(pages[1][2]['text'],'q')
        joined=' '.join(r['instrument'] for r in pages[1] if r['instrument'])
        self.assertEqual(joined,I.MICROMETER_50)

    def test_native_frames_separate(self):
        a=dim(K.KIND_FORM_TOL);b=dim(K.KIND_FORM_TOL)
        a.raw_text='@80~@22~ 0,01';b.raw_text='@80~@25~ 0,02 A'
        self.assertEqual(L.groups([a,b])[0]['params'],[a.raw_text,b.raw_text])

    def test_rough_sign_and_details(self):
        rp=N(SignType=1,RoughParamText='Ra 0,8',ProcessText='Шлифовать',BaseLengthText='0,8',TrendText='X',ProcessingByContour=True)
        d=R.rough_record('A',rp)
        self.assertTrue(d.raw_text.startswith('@172~Ra 0,8'))
        self.assertIn('Шлифовать',d.raw_text);self.assertIn('по контуру',d.raw_text)
        self.assertEqual(d.value,.8)

    def test_native_tolerance_table_modifiers(self):
        cells=['@25~','@2~0,02@35~','^(#1~А)1;123','Б@36~']
        tp=N(Sign=25,Table=N(RowsCount=1,ColumnsCount=4,Cell=lambda r,c:N(Str=cells[c])))
        ds=R.form_records(None,'A',tp)
        self.assertEqual(ds[0].raw_text,'@80~@25~ | @2~0,02@35~ | А | Б@36~')

    def test_unread_requirement_blocks_export(self):
        d=R.record('A',K.KIND_FORM_TOL,'Не прочитано');d.export_error='ошибка API'
        with self.assertRaisesRegex(ValueError,'ошибка API'):L.groups([d])

    def test_text_and_tt_are_never_read(self):
        class Drawing:
            SpecRough=N(IsCreated=False)
            def __getattr__(self,name):
                raise AssertionError('Нельзя читать '+name)
        class Symbols:
            Roughs=N(Count=0)
            Tolerances=N(Count=0)
            def __getattr__(self,name):
                raise AssertionError('Нельзя читать '+name)
        module=N(IDrawingDocument=lambda x:Drawing(),ISymbols2DContainer=lambda x:Symbols())
        doc=N(ViewsAndLayersManager=N(Views=N(Count=1,View=lambda i:N(Name='Вид 1'))))
        records,warnings=R.read(module,doc)
        self.assertEqual(records,[]);self.assertEqual(warnings,[])
        # Даже старые записи в памяти не должны попасть в экспорт.
        self.assertEqual(L.groups([R.record('A','надпись','Согласовано'),R.record('A','требование','ТТ')]),[])

    def test_separator_between_tools_and_before_next_view(self):
        groups=[dict(view='a',label='A',instrument='X',params=['p']),
                dict(view='a',label='A',instrument='Y',params=['q']),
                dict(view='b',label='B',instrument='Z',params=['r'])]
        page=L.paginate(groups,[17])[0]
        self.assertEqual([r['text'] for r in page],['','A:','p','','q','','B:','r',''])
        self.assertEqual(page[3],L.empty_row())
        self.assertEqual(page[5],L.empty_row())

    def test_full_page_separator_does_not_create_empty_sheet(self):
        group=dict(view='a',label='A',instrument='X',params=['p']*11)
        pages=L.paginate([group],[13])
        self.assertEqual(len(pages),1)
        self.assertEqual(len(pages[0]),13)

    def test_partial_font_bold_preserves_other_flags(self):
        f=N(bitvector=0x40|0x200|0x800)
        p=N(GetItemFont=lambda:f,SetItemFont=lambda f:1)
        X.set_font(p,{'Bold':True})
        self.assertEqual(f.bitvector,0x40|0x100|0x800)

    def test_changed_instrument_blocks_before_api5(self):
        old=dict(index=15,signature={},rows=[])
        block=dict(count=19,pages=[old],template=None)
        doc=N(LayoutSheets=N(Count=19,Item=lambda i:N()))
        with patch('cards.K.connect',return_value=(None,None)),patch('cards.X.open_doc',return_value=doc),patch('cards.read_page',return_value=dict(old,rows=[{'instrument':'changed'}])),patch('cards.X._connect5',side_effect=AssertionError('Must not connect')):
            with self.assertRaisesRegex(ValueError,'изменился'):C.write('tp.cdw',block,[])

    def test_plan_preserves_prefix_clears_tail(self):
        rows=[dict(param={'id':i,'text':'old','font':{},'count':1},instrument={'id':i+100,'text':'tool','font':{},'count':1}) for i in range(13)]
        page=dict(index=15,signature={'style':18},rows=rows)
        block=dict(count=17,pages=[page,dict(page,index=16)],template=None)
        groups=[dict(view='a',label='A',instrument='',params=['p'])]
        pages=C.plan(block,groups,2)
        self.assertEqual(pages[0]['after'][:2],[None,None])
        self.assertTrue(all(r==L.empty_row() for r in pages[1]['after']))
        self.assertEqual(block['pages'][0]['rows'][0]['param']['text'],'old')

    def test_write_two_pages_correct_columns_and_bold(self):
        font=dict(FontName='GOST type A',Height=3.5,WidthFactor=1,Color=0,Italic=True,Bold=False,Underline=False)
        memory={}
        pages=[]
        for index,style in ((15,18),(16,20)):
            rows=[]
            for pid,iid,vid in zip(X.PARAM_IDS[style],C.INSTRUMENT_IDS[style],C.VOLUME_IDS[style]):
                cells={col:dict(id=cid,text='old',font=font.copy(),count=1) for col,cid in (('param',pid),('instrument',iid),('volume',vid))}
                rows.append(cells)
                for cell in cells.values():memory[index,cell['id']]=cell.copy()
            pages.append(dict(index=index,signature={'style':style},rows=rows))
        block=dict(count=17,pages=pages,template=pages[1])
        groups=[dict(view='a',label='Главный вид',instrument='Прибор',params=['p%d'%i for i in range(20)])]
        planned=C.plan(block,groups,0)
        sheets=N(Count=17,Item=lambda i:N(Stamp=i))
        doc=N(LayoutSheets=sheets)
        app=N(ActiveDocument=N(PathName='tp.cdw'))
        module=N(IApplication=lambda x:app)
        k5=N(ksGetApplication7=lambda:None,ActiveDocument2D=lambda:None)
        writes=[]
        def write(doc5,k5,index,cid,text,ft):
            writes.append((index,cid,text,ft))
            memory[index,cid]=dict(id=cid,text=X.safe(text),font=ft,count=1)
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp,patch('cards.K.connect',return_value=(module,app)),patch('cards.X.open_doc',return_value=doc),patch('cards.assert_unchanged'),patch('cards.X._connect5',return_value=(None,k5)),patch('cards.X.backup_folder',return_value=Path(temp)),patch('cards.X.write_one',side_effect=write),patch('cards.X.read_cell',side_effect=lambda stamp,cid,mod:memory[stamp,cid]):
            C.write('tp.cdw',block,planned)
        self.assertEqual({w[0] for w in writes},{15,16})
        heading=next(w for w in writes if w[0]==15 and w[1]==6126)
        self.assertEqual(heading[2],'Главный вид:');self.assertTrue(heading[3]['Bold'])
        params=[w[2] for w in writes if w[1] in X.PARAM_IDS[18]+X.PARAM_IDS[20] and w[2].startswith('p')]
        self.assertEqual(params,groups[0]['params'])
        for index,cid,text,ft in writes:
            style=18 if index==15 else 20
            self.assertIn(cid,X.PARAM_IDS[style]+C.INSTRUMENT_IDS[style]+C.VOLUME_IDS[style])
            if cid in C.VOLUME_IDS[style]:self.assertEqual(text,'')
        self.assertEqual(memory[15,6151]['text'],'')
        self.assertEqual(memory[15,6152]['text'],'')
        self.assertEqual(memory[15,6153]['text'],'old')


if __name__=='__main__':unittest.main(verbosity=2)
