import unittest
import kompas_dims as K
import layout as L
import sketch as S
from test_sketch import text_state

class DiameterRegression(unittest.TestCase):
    def profile(self):
        g=K.Geometry();g.axis_y=0;g.profile_ok=True
        # Small spigot meets the larger shoulder at x=0.
        g.segments=[(-10,-3,0,-3),(-10,3,0,3),(0,-6,10,-6),
                    (0,6,10,6),(0,3,0,6),(0,-3,0,-6)]
        return g

    def dim(self,value=6,x=0):
        d=K.Dim();d.kind=K.KIND_OUTER;d.view='A';d.value=value
        d.x=x;d.anchors=(x,-value/2,x,value/2)
        return d

    def test_spigot_at_shoulder_is_outer(self):
        d=self.dim();K.classify_diameters([d],{'A':self.profile()})
        self.assertFalse(K.diameter_uncertain(d));self.assertEqual(d.kind,K.KIND_OUTER)
        K.assign_tolerances([d]);self.assertEqual((d.hi,d.lo),(0,-.3))

    def test_larger_outline_does_not_prove_hole(self):
        d=self.dim(x=5);K.classify_diameters([d],{'A':self.profile()})
        self.assertTrue(K.diameter_uncertain(d))
        K.assign_tolerances([d]);self.assertIsNone(d.hi)
        self.assertIsNone(S.propose(d,text_state(),[],'m','gost')[0])
        with self.assertRaises(ValueError):L.groups([d])

    def test_missing_or_off_axis_anchors_need_review(self):
        for anchors in (None,(0,1,0,7),(0,-3,5,3)):
            d=self.dim();d.anchors=anchors
            K.classify_diameters([d],{'A':self.profile()})
            self.assertTrue(K.diameter_uncertain(d))

    def test_old_groove_flag_cannot_turn_outer_positive(self):
        d=self.dim(11);d.groove=True;K.assign_tolerances([d])
        self.assertEqual((d.hi,d.lo),(0,-.43))

    def test_explicit_fit_and_tolerance_preserved(self):
        d=self.dim();d.fit='H7';d.src=K.SRC_DRAWING;d.hi=.012;d.lo=0
        K.classify_diameters([d],{'A':self.profile()});K.assign_tolerances([d])
        self.assertEqual(d.kind,K.KIND_INNER);self.assertEqual((d.hi,d.lo),(.012,0))

    def test_uncertain_source_cannot_supply_tolerance(self):
        d=self.dim();d.manual=True
        src=self.dim();src.reason='проверить — нет контура';src.hi=.3;src.lo=0
        p,_=S.propose(d,text_state(),[src],'m','gost')
        self.assertEqual((p['hi'],p['lo']),(0,-.3))

    def test_manual_choice_resolves_card_block(self):
        d=self.dim();d.reason='проверить — нет контура';d.manual=True
        K.assign_tolerances([d]);self.assertTrue(L.groups([d]))
