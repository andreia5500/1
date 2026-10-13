import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import patch
import kompas_dims as K
import sketch as S


def dim(kind=K.KIND_LINEAR,value=20):
    d=K.Dim();d.kind=kind;d.value=value;d.view='A';return d


def text_state(**kw):
    data=dict(NominalValue=20.,AutoNominalValue=True,Sign=0,Tolerance='',ToleranceOn=False,
              DeviationOn=False,DeviationType=0,HighDeviationValue=0.,LowDeviationValue=0.,
              NominalText='20',Prefix='',Suffix='',TextUnder='',HighDeviation='',LowDeviation='',
              Rectangle=False,Brackets=False,HasTolerance=False)
    data.update(kw);return data


class SketchTests(unittest.TestCase):
    def test_existing_visible_hidden_and_text_preserved(self):
        for state in (text_state(HighDeviationValue=.1),text_state(Tolerance='H7'),
                      text_state(NominalText='20±1'),text_state(LowDeviation='-0,1'),
                      text_state(DeviationOn=False,HighDeviationValue=.02)):
            proposal,reason=S.propose(dim(),state,[],'m','gost')
            self.assertIsNone(proposal);self.assertIn('сохранить',reason)

    def test_zero_zero_flag_uses_same_default_rules(self):
        proposal,_=S.propose(dim(),text_state(DeviationOn=True),[],'m','gost')
        self.assertEqual((proposal['hi'],proposal['lo']),(.2,-.2))
        d=dim(K.KIND_OUTER,7)
        proposal,_=S.propose(d,text_state(),[],'m','gost')
        self.assertEqual((proposal['hi'],proposal['lo']),(0,-.36))

    def test_source_list_reuse_and_ambiguity(self):
        a=dim();a.hi,a.lo=.12,-.02
        p,reason=S.propose(dim(),text_state(),[a],'m','gost')
        self.assertEqual((p['hi'],p['lo']),(.12,-.02));self.assertIn('списка',reason)
        b=copy.copy(a);b.hi=.3
        p,reason=S.propose(dim(),text_state(),[a,b],'m','gost')
        self.assertIsNone(p);self.assertIn('неоднозначные',reason)

    def test_uncertain_diameter_needs_type(self):
        d=dim(K.KIND_OUTER);d.reason='проверить — геометрия не применима'
        self.assertIsNone(S.propose(d,text_state(),[],'m','gost')[0])
        source=dim(K.KIND_INNER);source.hi=.02;source.lo=0
        p,_=S.propose(d,text_state(),[source],'m','gost')
        self.assertIsNone(p)  # Equal nominal alone cannot identify a surface.
        d.kind=K.KIND_INNER;d.manual=True
        p,_=S.propose(d,text_state(),[source],'m','gost')
        self.assertEqual(p,dict(hi=.02,lo=0,kind=K.KIND_INNER))

    def test_sheet_membership_not_view_origin(self):
        frames=[(20,5,205,292),(230,5,415,292)]
        self.assertTrue(S.on_sheet((260,50,290,80),frames,1))
        self.assertFalse(S.on_sheet((260,50,290,80),frames,0))
        self.assertFalse(S.on_sheet((200,50,250,80),frames,1))
        with self.assertRaises(ValueError):S.validate_frames([frames[0],frames[0]])

    def test_frame_return_and_top_bottom_order(self):
        self.assertEqual(S.frame_rect(N(GetPlaceInsideFrames=lambda:(True,230,292,415,5))),(230,5,415,292))
        with self.assertRaises(ValueError):S.frame_rect(N(GetPlaceInsideFrames=lambda:(False,0,0,0,0)))

    def test_title_without_free_space_does_not_block_sheet_15(self):
        sheets=N(Count=15,Item=lambda i:N(GetPlaceInsideFrames=lambda:
            (True,20,0,205,0) if i==0 else (True,210*i+20,292,210*i+205,5)))
        frames=S.read_frames(sheets,14)
        self.assertIsNone(frames[0]);self.assertEqual(len(frames),15)
        self.assertTrue(S.on_sheet((3000,50,3030,80),frames,14))
        self.assertFalse(S.on_sheet((2800,50,2820,80),frames,14))

    def test_unavailable_other_sheet_does_not_block_selected(self):
        sheets=N(Count=2,Item=lambda i:N(GetPlaceInsideFrames=lambda:
            (False,0,0,0,0) if i==0 else (True,230,292,415,5)))
        self.assertEqual(S.read_frames(sheets,1),[None,(230,5,415,292)])

    def test_selected_empty_sheet_is_still_blocked(self):
        sheets=N(Count=15,Item=lambda i:N(GetPlaceInsideFrames=lambda:(True,0,0,0,0)))
        with self.assertRaisesRegex(ValueError,'выбранного листа 15'):
            S.read_frames(sheets,14)

    def test_only_native_deviation_fields_written(self):
        before=text_state();dt=N(**{k:v for k,v in before.items() if k not in ('HighDeviation','LowDeviation','NominalText','Prefix','Suffix','TextUnder')})
        for key in ('HighDeviation','LowDeviation','NominalText','Prefix','Suffix','TextUnder'):
            setattr(dt,key,N(Str=before[key]))
        calls=[]
        def update():
            dt.HighDeviationValue=float(dt.HighDeviation.Str.replace(',','.') or 0)
            dt.LowDeviationValue=float(dt.LowDeviation.Str.replace(',','.') or 0)
            calls.append(1);return True
        obj=N(Update=update)
        S.write_dimension(N(IDimensionText=lambda o:dt),obj,dict(hi=0,lo=-.36,kind=K.KIND_OUTER),before)
        self.assertEqual(dt.HighDeviation.Str,'');self.assertEqual(dt.LowDeviation.Str,'-0,36')
        self.assertEqual(dt.NominalText.Str,'20');self.assertEqual(calls,[1])

    def test_angular_format_no_duplicate_plusminus(self):
        self.assertEqual(S.deviation_text(.5,True),"+30'")
        self.assertEqual(S.deviation_text(-1,True),'-1°')
        self.assertEqual(S.deviation_text(.1),'+0,1')

    def test_existing_tolerance_rejected_before_connect(self):
        r=dict(ref=123,state=text_state(HighDeviationValue=.1),proposal=dict(hi=.2,lo=-.2))
        with patch('sketch.context',side_effect=AssertionError('Не подключаться')):
            with self.assertRaises(ValueError):S.write('tp.cdw',dict(records=[r]),[123])

    def test_write_selected_only_and_reject_changes(self):
        records=[]
        for ref in (1,2):
            records.append(dict(ref=ref,view=7,collection='LineDimensions',index=ref,
                                box=(250,20,270,30),state=text_state(),dim=dim(),
                                proposal=dict(hi=.2,lo=-.2,kind=K.KIND_LINEAR)))
        expected=dict(sheet=1,count=2,frames=[(0,0,210,297),(210,0,420,297)],records=records)
        module=N(IDimensionText=lambda obj:text_state())
        app=N(ActiveDocument=N(PathName='tp.cdw'))
        objects={1:'first',2:'second'}
        with tempfile.TemporaryDirectory() as folder,patch('sketch.context',return_value=(module,None,None,app,None,None)),patch('sketch.live_scan',return_value=(copy.deepcopy(expected),objects)),patch('sketch.snapshot',return_value=text_state()),patch('sketch.X.backup_folder',return_value=Path(folder)),patch('sketch.write_dimension') as write:
            self.assertEqual(S.write('tp.cdw',expected,[2]),1)
            self.assertEqual(write.call_args.args[1],'second')
        altered=copy.deepcopy(expected);altered['records'][1]['state']['NominalValue']=21
        with patch('sketch.context',return_value=(module,None,None,app,None,None)),patch('sketch.live_scan',return_value=(altered,objects)),patch('sketch.write_dimension',side_effect=AssertionError('Запись запрещена')):
            with self.assertRaisesRegex(ValueError,'изменился'):S.write('tp.cdw',expected,[2])


if __name__=='__main__':unittest.main(verbosity=2)
