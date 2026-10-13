"""Автономные проверки: не заменяют испытание с реальным КОМПАСом."""
import unittest
from types import SimpleNamespace as N
from unittest.mock import patch
import kompas_dims as K
import tolerances as T
import transfer as X

MOD=N(IDimensionText=lambda x:x)

def read(**props):
    defaults=dict(NominalValue=58,AutoNominalValue=True,DeviationOn=True,HighDeviationValue=0,LowDeviationValue=0)
    defaults.update(props)
    return K.read_dimension(MOD,N(**defaults),'line','Главный вид')

class Tests(unittest.TestCase):
    def test_zero_flag(self):
        d=read();K.assign_tolerances([d]);self.assertEqual((d.hi,d.lo),(.3,-.3));self.assertEqual(d.src,K.SRC_DEFAULT)
    def test_real_tol(self):
        d=read(HighDeviationValue=-.002,LowDeviationValue=-.004);K.assign_tolerances([d]);self.assertEqual((d.hi,d.lo),(-.002,-.004))
    def test_nominal_display(self):
        d=read(NominalValue=10.049417,NominalText=N(Str='10'));self.assertEqual(d.value,10)
    def test_high_precision(self):
        d=read(NominalText=N(Str='10,125'));self.assertTrue(d.column_text().startswith('10,125'))
    def test_angle_side_survives_recalc(self):
        d=K.read_dimension(MOD,N(NominalValue=60,X1=5,Y1=0,X2=0,Y2=20,Xc=0,Yc=0),'angle','A')
        K.assign_tolerances([d]);self.assertEqual(d.hi,1)
        K.assign_tolerances([d]);self.assertEqual(d.hi,1)
    def test_unknown_angle_not_guessed(self):
        d=read();d.kind=K.KIND_ANGLE;K.assign_tolerances([d]);self.assertIsNone(d.hi)
        with self.assertRaises(ValueError):X.pack([d])
    def test_radius_explicit(self):
        d=read(NominalValue=2,HighDeviationValue=.1,LowDeviationValue=-.1);d.kind=K.KIND_RADIUS
        self.assertEqual(d.column_text(),'R2±0,1')
    def test_indices(self):
        d=read(NominalValue=11,HighDeviationValue=-.016,LowDeviationValue=-.034);d.kind=K.KIND_OUTER
        self.assertEqual(X.pack([d]),['Главный вид:', '@2~11$m-0,016;-0,034$'])
    def test_auto_diameter(self):
        d=read(NominalValue=7);d.kind=K.KIND_OUTER;K.assign_tolerances([d]);self.assertEqual(X.pack([d]),['Главный вид:', '@2~7$m;-0,36$'])
    def test_asymmetric_angle(self):
        self.assertEqual(T.fmt_angle_pair(.5,0),"+30'")
        self.assertEqual(T.fmt_angle_pair(1,-.5),"+1°;-30'")
    def test_pack_preserves_views(self):
        a=read();b=read();a.view='A';b.view='B';K.assign_tolerances([a,b]);self.assertEqual(len(X.pack([a,b])),4)
    def test_no_false_chamfer(self):
        a=read(NominalValue=1);b=read(NominalValue=45);b.kind=K.KIND_ANGLE
        K.detect_chamfers([a,b]);self.assertEqual(a.kind,K.KIND_LINEAR)
    def test_manual_tol(self):
        d=read(NominalValue=20,NominalText=N(Str='20±0,1'),AutoNominalValue=False)
        K.assign_tolerances([d]);self.assertEqual(d.column_text(),'20±0,1')
    def test_it14_out_of_range(self):
        with self.assertRaises(ValueError):T.it14(600)
    def test_font_flags(self):
        f=N();p=N(GetItemFont=lambda:f,SetItemFont=lambda f:1)
        X.set_font(p,dict(FontName='GOST type A',Height=3.5,WidthFactor=.8,Color=0,Italic=True,Bold=False,Underline=False))
        self.assertEqual(f.bitvector,0x40|0x200|0x800);self.assertEqual(f.height,3.5)
    def test_font_props_case_insensitive(self):
        # Реальный ksTextItemFont: bitVector/fontName, gen_py чувствителен к регистру.
        class Font:
            _prop_map_get_={'bitVector':0,'fontName':0,'height':0,'ksu':0,'color':0}
            _prop_map_put_=_prop_map_get_
            def __init__(self):self.__dict__.update(bitVector=0x2,fontName='',height=0,ksu=1,color=0)
        f=Font();p=N(GetItemFont=lambda:f,SetItemFont=lambda f:1)
        self.assertEqual(X.get_prop(f,'bitvector'),0x2)
        X.set_font(p,dict(FontName='GOST type A',Height=3.5,Bold=True))
        self.assertEqual(f.bitVector,0x2|0x100);self.assertEqual(f.fontName,'GOST type A')
        self.assertFalse(hasattr(f,'bitvector'))
    def test_explicit_sheet(self):
        seen=[]
        stamp=N(ksOpenStamp=lambda:1,ksColumnNumber=lambda i:seen.append(i) or 1,ksTextLine=lambda p:seen.append(p.s) or 1,ksCloseStamp=lambda:1)
        doc=N(GetStampEx=lambda n:seen.append(('sheet',n)) or stamp)
        p=N(Init=lambda:None)
        with patch('transfer._text_item_param',return_value=p):X.write_one(doc,None,15,6125,'Ø7$m-0,36;$',{})
        self.assertEqual(seen,[('sheet',16),6125,'@2~7$m-0,36;$'])
    def test_cell_cleared_before_write(self):
        # Журнал 13.10: 'Главный вид:' поверх '@2~12$m…$' читалось как 'Главный вид:@2~'.
        seen=[]
        stamp=N(ksOpenStamp=lambda:1,ksClearStamp=lambda i:seen.append(('clear',i)) or 1,
                ksColumnNumber=lambda i:seen.append(('select',i)) or 1,ksTextLine=lambda p:seen.append(p.s) or 1,
                ksCloseStamp=lambda:seen.append('close') or 1)
        with patch('transfer._text_item_param',return_value=N(Init=lambda:None)):
            X.write_one(N(GetStampEx=lambda n:stamp),None,15,6126,'Главный вид:',{})
        self.assertEqual(seen,[('clear',6126),('select',6126),'Главный вид:','close'])
    def test_rejected_clear_no_write(self):
        seen=[]
        stamp=N(ksOpenStamp=lambda:1,ksClearStamp=lambda i:0,ksColumnNumber=lambda i:seen.append(i) or 1,
                ksTextLine=lambda p:seen.append(p) or 1,ksCloseStamp=lambda:seen.append('close') or 1)
        with patch('transfer._text_item_param',return_value=N(Init=lambda:None)):
            with self.assertRaises(RuntimeError):X.write_one(N(GetStampEx=lambda n:stamp),None,15,6126,'20',{})
        self.assertEqual(seen,['close'])
    def test_rejected_column_no_write(self):
        seen=[];stamp=N(ksOpenStamp=lambda:1,ksColumnNumber=lambda i:0,ksTextLine=lambda p:seen.append(1),ksCloseStamp=lambda:1)
        with patch('transfer._text_item_param',return_value=N(Init=lambda:None)):
            with self.assertRaises(RuntimeError):X.write_one(N(GetStampEx=lambda n:stamp),None,15,6125,'20',{})
        self.assertEqual(seen,[])
    def test_capacity_before_connect(self):
        with patch('transfer.K.connect',side_effect=AssertionError('Must not connect')):
            with self.assertRaises(ValueError):X.transfer('x',15,12,[{}]*13,['1','2'])
    def test_control_row_maps(self):
        self.assertEqual(len(X.PARAM_IDS[18]),13);self.assertEqual(len(X.PARAM_IDS[20]),17)
        self.assertNotIn(2,X.PARAM_IDS)

    def test_changed_field_prevents_api5_connection(self):
        rows=[dict(id=i,text='old',font={},count=1) for i in X.PARAM_IDS[18]]
        sh=N(LayoutStyleNumber=18,Stamp=object())
        doc=N(LayoutSheets=N(Item=lambda i:sh))
        with patch('transfer.K.connect',return_value=(None,None)), patch('transfer.open_doc',return_value=doc), patch('transfer.read_cell',return_value=dict(rows[0],text='edited')), patch('transfer._connect5',side_effect=AssertionError('Must not connect')):
            with self.assertRaisesRegex(ValueError,'изменилась'):X.transfer('tp.cdw',15,0,rows,['20'])

    def test_wrong_active_document_prevents_writes(self):
        rows=[dict(id=i,text='old',font={},count=1) for i in X.PARAM_IDS[18]]
        sh=N(LayoutStyleNumber=18,Stamp=object())
        doc=N(LayoutSheets=N(Item=lambda i:sh))
        app5=N(ActiveDocument=N(PathName='other.cdw'))
        mod=N(IApplication=lambda obj:app5)
        k5=N(ksGetApplication7=lambda:None)
        with patch('transfer.K.connect',return_value=(mod,None)), patch('transfer.open_doc',return_value=doc), patch('transfer.read_cell',return_value=rows[0]), patch('transfer._connect5',return_value=(None,k5)), patch('transfer.write_one',side_effect=AssertionError('Must not write')):
            with self.assertRaisesRegex(ValueError,'активным'):X.transfer('tp.cdw',15,0,rows,['20'])


    def test_single_deviation_position(self):
        self.assertEqual(K._maybe_index_dev('-0,36'), '$m;-0,36$')
        self.assertEqual(K._maybe_index_dev('+0,43'), '$m+0,43;$')
        self.assertEqual(K._maybe_index_dev('±0,1'), '±0,1')
        self.assertEqual(K._maybe_index_dev('-0,002;-0,004'), '$m-0,002;-0,004$')
    def test_headings_once_per_source_view(self):
        a=read();b=read();c=read()
        a.view=c.view='Спереди 1';a.view_label=c.view_label='Главный вид'
        b.view='Сечение Б-Б';K.assign_tolerances([a,b,c])
        lines=X.pack([b,a,c])
        self.assertEqual(lines[0],'Главный вид:')
        self.assertEqual(lines.count('Главный вид:'),1)
        self.assertEqual(lines.count('Сечение Б-Б:'),1)
    def test_view_roles(self):
        roles=K.classify_view_roles([('Системный вид',0,0),('Спереди 1',100,100),('Проекционный вид 2',150,100),('Проекционный вид 3',50,100),('Сечение Б-Б',0,200),('Разрез А-А',0,300)])
        self.assertEqual(roles['Спереди 1'],'Главный вид')
        self.assertEqual(roles['Проекционный вид 2'],'Вид слева')
        self.assertEqual(roles['Проекционный вид 3'],'Вид справа')
        self.assertEqual(roles['Сечение Б-Б'],'Сечение Б-Б')
        self.assertEqual(roles['Разрез А-А'],'Разрез А-А')
    def test_explicit_orientation(self):
        roles=K.classify_view_roles([('Спереди 1',0,0),('Слева 2',-100,200),('Сзади 3',200,-300)])
        self.assertEqual(roles['Слева 2'],'Вид слева')
        self.assertEqual(roles['Сзади 3'],'Вид сзади')
    def test_heading_counts_towards_capacity(self):
        d=read();K.assign_tolerances([d]);lines=X.pack([d]);self.assertEqual(len(lines),2)
        with patch('transfer.K.connect',side_effect=AssertionError('Must not connect')):
            with self.assertRaises(ValueError):X.transfer('x',15,12,[{}]*13,lines)

if __name__=='__main__':unittest.main(verbosity=2)
