"""Движок проверки УП: сверка с эталоном JS (DiamondCAM/Post) и ручным счётом."""
import copy
import unittest
from pathlib import Path
import nc_engine as E

PROGRAMS = Path(__file__).parent / 'nc_tests' / 'programs'
SUBS = {n: (PROGRAMS / ('O' + n)).read_text(encoding='utf-8') for n in ('5000', '5001', '5002')}


def prog(name):
    return (PROGRAMS / name).read_text(encoding='utf-8')


def bare():
    p = E.default_params()
    p.update(model_spindle_ramp=False, t_code_exec_time_ms=0, rapid_override_pct=100)
    p['m_codes']['default_exec_time_ms'] = 0
    for a in p['axes'].values():
        a.update(g0_accel_ms=0, g1_accel_ms=0, feed_clamp_mm_min=1e9)
    return p


def run(text, subs=None, params=None):
    sims, rep = E.calculate([dict(name='T', spindle='1', text=text)], subs or {}, params or bare())
    return sims[0], rep


class ReferenceJs(unittest.TestCase):
    """Значения JS-версии 1.7.0 (217889.52 / 332863.19 мс) минус ошибка JS: кадр «G125Z2»
    (отмена совмещения осей, Z2 — номер оси) считался перемещением по Z до Z=2 на подаче.
    С 2.3.0 такие кадры — не перемещение. С 2.4.0 — по руководству M800/M80 (токарный, 13.5): в G83/G87
    R — расстояние от исходной точки (а не координата), возврат в исходную точку, K — повторы."""
    def check(self, a, b, total, cuts):
        sims, rep = E.calculate([dict(name=a, spindle='1', text=prog(a)), dict(name=b, spindle='2', text=prog(b))], SUBS)
        self.assertAlmostEqual(rep['totalMs'], total, places=6)
        for sim, cut in zip(sims, cuts):
            self.assertAlmostEqual(sim.cutting_ms, cut, places=6)

    def test_o6017_o6018(self):
        self.check('O6017', 'O6018', 205385.24924939836, (130532.37111149699, 26253.494690198477))

    def test_o6108_o6109(self):
        self.check('O6108', 'O6109', 310381.6004368947, (191849.48113379622, 3952.789915966386))


class HandCalc(unittest.TestCase):
    def ms(self, text, subs=None):
        return run(text, subs)[0].seg_ms

    def test_moves(self):
        self.assertAlmostEqual(self.ms('G0X100.Z60.'), 120)
        self.assertAlmostEqual(self.ms('S1=1000M3\nG99G1Z-10.F0.1'), 6000)
        self.assertAlmostEqual(self.ms('G97S1000M3\nG99G1Z-10.F0.1'), 6000)
        self.assertAlmostEqual(self.ms('G98G1Z-10.F100.'), 6000)
        self.assertAlmostEqual(self.ms('G4X1.5\nG4P500'), 2000)
        self.assertAlmostEqual(self.ms('G98G0X0Z0\nG2X20.Z-10.R10.F100.'), 9424.778, places=2)
        self.assertAlmostEqual(self.ms('G0X50.Z0\nG96S1=100M3\nG99G1Z-10.F0.1'), 9474.778, places=2)

    def test_flow(self):
        self.assertAlmostEqual(self.ms('#1=0\nN10G98G1W-10.F100.\n#1=#1+1\nIF[#1LT3]GOTO10\nM30'), 18000)
        self.assertAlmostEqual(self.ms('#1=0\nWHILE[#1LT3]DO1\nG98G1W-10.F100.\n#1=#1+1\nEND1\nM30'), 18000)
        self.assertAlmostEqual(self.ms('M98P100L3\nM30', {'100': 'G98G1W-10.F100.\nM99'}), 18000)
        sim = run('#1=0\nIF[#1EQ1]THEN#2=5\nG98G1Z-10.,C1.F100.')[0]
        self.assertNotIn('2', sim.vars);self.assertEqual(sim.pos['C'], 0);self.assertIsNone(sim.current_tool_raw)
        self.assertIn('нет парного END1', run('#1=0\nWHILE[#1GT3]DO1\nG1Z1.')[0].warnings[0])

    def test_g76_passes(self):
        self.assertEqual(E.Simulator.thread_passes(0.774, 0.15, 3, 0.15, 0.1), 8)
        self.assertEqual(E.Simulator.thread_passes(0.774, 0.65, 1, 0.65, 0.1), 3)

    def test_profile_above_cycle_does_not_loop(self):
        sim, rep = run('S1=1000M3\nG0X40.Z1.\nN10G1X20.\nZ-20.\nN20X42.\nG73U3.W0R3\nG73P10Q20U0.2W0F0.2\nM30')
        self.assertFalse(sim.incomplete);self.assertLess(rep['totalMs'], 60000)

    def test_division_by_zero_does_not_make_infinite_time(self):
        sim, rep = run('#6=5\nG0X[#6/0]\nG98G1Z-10.F100.\nM30')
        self.assertAlmostEqual(rep['totalMs'], 6000);self.assertIn('деление на 0', sim.warnings[0])

    def test_eof_char_is_not_a_block(self):
        stmts, labels, findings = E.validate_program('O1\nG0X1.\nM30\n%\x1a')
        self.assertEqual(len(stmts), 3);self.assertFalse([f for f in findings if f['code'] == 'DEAD'])


class FullCheck(unittest.TestCase):
    def codes(self, text, **kw):
        files = [dict(name='T', text=text, kind='system', spindle='1')]
        rep = E.full_program_check(files, {}, 8000)
        return [(f['code'], f['line']) for f in rep['perFile'][0]['findings']]

    def test_machine_alarms(self):
        codes = dict(self.codes('O0\nN0\nG0G1X1.\nM3M4\nWHILE[1]DO1\nGOTO77\nG83Z-5.Q0\nF-1.\n'))
        for code in ('P37', 'CONFLICT-G', 'CONFLICT-M', 'P294', 'P231', 'PECK-Q', 'NEG-F', 'P36'):
            self.assertIn(code, codes)

    def test_sync_labels_between_systems(self):
        files = [dict(name='A', text='!L1\n!L2\nM30', kind='system', spindle='1'),
                 dict(name='B', text='!L1\nM30', kind='system', spindle='2')]
        rep = E.full_program_check(files, {}, 8000)
        self.assertEqual([f['code'] for f in rep['crossFindings']], ['SYNC'])

    def test_real_programs_have_no_errors(self):
        files = [dict(name='O6108', text=prog('O6108'), kind='system', spindle='1'),
                 dict(name='O6109', text=prog('O6109'), kind='system', spindle='2')]
        files += [dict(name='O' + n, text=t, kind='subprogram') for n, t in SUBS.items()]
        rep = E.full_program_check(files, SUBS, 8000)
        self.assertEqual(rep['totalErrors'], 0)

    def test_sub_number(self):
        self.assertEqual(E.detect_sub_number('O5001\nM99', 'x'), '5001')
        self.assertEqual(E.detect_sub_number('M99', 'O0042.nc'), '42')


if __name__ == '__main__':
    unittest.main()
