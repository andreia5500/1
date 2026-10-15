"""Имитация фрезерных HAAS / IMV (HNC-8): время и проверки на синтетических программах."""
import math
import unittest

import mill_engine as M


def run(machine, files, **over):
    params = M.default_params(machine)
    params.update(over)
    if isinstance(files, str):
        files = [('O1000.NC', files)]
    return M.analyze(files, params)


def codes(setup, severity=None):
    return [i['code'] for i in setup['issues'] if severity is None or i['severity'] == severity]


HEAD = '%\nO1000 (TEST)\nG17 G40 G49 G80 G90 G94\nT1 M6 (FREZA)\nG54\nG0 G43 H1 Z100. S1000 M3\nM8\n'


class Expressions(unittest.TestCase):
    def test_functions_and_operators(self):
        get = {1: 2.0, 2: 30.0}.get
        self.assertAlmostEqual(M.evaluate('[#1*3+1]', get), 7.0)
        self.assertAlmostEqual(M.evaluate('SIN[#2]', get), 0.5)
        self.assertAlmostEqual(M.evaluate('FIX[7.9]', get), 7.0)
        self.assertAlmostEqual(M.evaluate('FIX[#51150/100]', {51150: 357.0}.get), 3.0)
        self.assertEqual(M.evaluate('[#1GE#2]', get), 0.0)
        self.assertEqual(M.evaluate('[#106EQ1.]', {106: 1.0}.get), 1.0)
        self.assertAlmostEqual(M.evaluate('ATAN[1]/[1]', get), 45.0)
        self.assertAlmostEqual(M.evaluate('-#1', get), -2.0)
        self.assertEqual(M.evaluate('#5', get), 0.0)    # пустая переменная


class Timing(unittest.TestCase):
    def test_feed_time_g94_and_g95(self):
        rep = run('haas', HEAD + 'G0 X0 Y0 Z1.\nG1 X100. F1000.\nG0 Z100.\nM30\n', feed_accel_ms=0)
        s = rep['setups'][0]
        self.assertAlmostEqual(s['cat']['cut'], 6000, delta=1)          # 100 мм / 1000 мм/мин
        rep = run('haas', HEAD.replace('G94', 'G95') + 'G0 X0 Y0 Z1.\nG1 X100. F0.1\nG0 Z100.\nM30\n', feed_accel_ms=0)
        self.assertAlmostEqual(rep['setups'][0]['cat']['cut'], 60000, delta=1)   # 0.1 × 1000 = 100 мм/мин

    def test_rapid_uses_override_and_slowest_axis(self):
        def move(pct):
            base = run('haas', HEAD + 'G0 X0 Y0\nM30\n', rapid_override_pct=pct, accel_ms=0)['setups'][0]
            more = run('haas', HEAD + 'G0 X0 Y0\nG0 X500. Y100.\nM30\n', rapid_override_pct=pct, accel_ms=0)['setups'][0]
            return more['cat']['rapid'] - base['cat']['rapid']
        self.assertAlmostEqual(move(100), 500 / 25400 * 60000, delta=2)    # X — самая длинная ось
        self.assertAlmostEqual(move(50), 2 * 500 / 25400 * 60000, delta=2)

    def test_full_circle_length(self):
        rep = run('imv', HEAD + 'G0 X10. Y0 Z1.\nG1 Z0 F100.\nG3 I-10. F600.\nG0 Z100.\nM30\n', feed_accel_ms=0)
        cut = rep['setups'][0]['cat']['cut']
        self.assertAlmostEqual(cut, 600 + 2 * math.pi * 10 / 600 * 60000, delta=2)

    def test_tool_change_and_dwell(self):
        haas = run('haas', HEAD + 'G4 P2.\nG4 P500\nM30\n')['setups'][0]
        self.assertAlmostEqual(haas['cat']['dwell'], 2500, delta=1)
        self.assertAlmostEqual(haas['cat']['tool'], 4200, delta=1)
        imv = run('imv', HEAD + 'G04 P1.\nG04 X2.\nM30\n')['setups'][0]
        self.assertAlmostEqual(imv['cat']['dwell'], 2001, delta=1)     # P — миллисекунды, X — секунды
        self.assertIn('G04 P', codes(imv))

    def test_drilling_cycle_and_repeats(self):
        prog = HEAD.replace('G94', 'G95') + 'G0 X0 Y0 Z10.\nG81 G98 Z-20. R2. F0.1\nX10.\nX20.\nG80\nM30\n'
        s = run('haas', prog, feed_accel_ms=0)['setups'][0]
        self.assertEqual(s['tools'][0]['holes'], 3)
        self.assertAlmostEqual(s['cat']['cut'], 3 * 22 / 100 * 60000, delta=5)
        fanuc = run('imv', prog.replace('F0.1', 'F0.1 K2.'), feed_accel_ms=0)['setups'][0]
        self.assertEqual(fanuc['tools'][0]['holes'], 4)           # K2 в G90 — первое отверстие дважды
        self.assertIn('G81 повтор', codes(fanuc))

    def test_peck_drilling(self):
        prog = HEAD.replace('G94', 'G95') + 'G0 X0 Y0 Z10.\nG83 G98 Z-20. R0 Q5. F0.1\nG80\nM30\n'
        s = run('haas', prog, feed_accel_ms=0, peck_clear=1.0)['setups'][0]
        # 4 прохода по 5 мм, каждый следующий начинается на 1 мм выше дна предыдущего
        self.assertAlmostEqual(s['cat']['cut'], (20 + 3 * 1) / 100 * 60000, delta=5)

    def test_tapping_pitch_and_speed(self):
        prog = HEAD.replace('G94', 'G95').replace('S1000', 'S300') + 'G0 X0 Y0 Z10.\nG84 G98 Z-15. R5. F1.337\nG80\nM30\n'
        s = run('haas', prog, tap_reverse_s=0, feed_accel_ms=0)['setups'][0]
        self.assertNotIn('G84 шаг', codes(s))                      # G1/4 — 19 ниток на дюйм
        self.assertAlmostEqual(s['cat']['cut'], 2 * 20 / (300 * 1.337) * 60000, delta=5)
        bad = run('haas', prog.replace('F1.337', 'F1.3'))['setups'][0]
        self.assertIn('G84 шаг', codes(bad))

    def test_block_skip_alternative_time(self):
        prog = HEAD + 'G0 X0 Y0 Z10.\n/G4 P10.\nM30\n'
        s = run('haas', prog)['setups'][0]
        self.assertAlmostEqual(s['alt_ms'] - s['ms'], 10000, delta=1)


class Subprograms(unittest.TestCase):
    def test_haas_m97_local_and_m98_file(self):
        main = HEAD + 'M97 P100 L2\nM98 P5000\nM30\nN100 G4 P1.\nM99\n'
        sub = '%\nO5000\nG4 P3.\nM99\n%\n'
        rep = run('haas', [('O1000.NC', main), ('O5000.NC', sub)])
        s = rep['setups'][0]
        self.assertAlmostEqual(s['cat']['dwell'], 5000, delta=1)
        self.assertEqual(rep['subs'][0]['no'], '5000')
        self.assertTrue(rep['subs'][0]['used'])

    def test_haas_m98_to_local_label_hint(self):
        s = run('haas', HEAD + 'M98 P100\nM30\nN100 G4 P1.\nM99\n')['setups'][0]
        msg = next(i['message'] for i in s['issues'] if i['code'] == 'M98')
        self.assertIn('M97 P100', msg)

    def test_hnc8_subprograms_in_file_are_local(self):
        a = HEAD + 'M98 P200\nM30\nO200\nG04 X1.\nM99\n'
        b = HEAD.replace('O1000', 'O1001') + 'M98 P200\nM30\nO200\nG04 X2.\nM99\n'
        rep = run('imv', [('1000.NC', a), ('1001.NC', b)])
        self.assertEqual(rep['issues'], [])
        dwell = sorted(s['cat']['dwell'] for s in rep['setups'])
        self.assertAlmostEqual(dwell[0], 1000, delta=1)
        self.assertAlmostEqual(dwell[1], 2000, delta=1)

    def test_duplicate_main_numbers(self):
        rep = run('imv', [('45202.NC', HEAD.replace('O1000', 'O45202') + 'M30\n'),
                          ('45209.NC', HEAD.replace('O1000', 'O45202') + 'M30\n')])
        self.assertTrue(any(i['code'] == 'O45202' and i['severity'] == 'error' for i in rep['issues']))

    def test_macro_loop_and_if_then(self):
        prog = HEAD + '#1=0\nWHILE[#1LT3]DO1\nG4 X1.\n#1=#1+1\nEND1\n#106=1\nIF[#106EQ1.]THEN M98P101\nM30\nO101\nG04 X5.\nM99\n'
        s = run('imv', prog)['setups'][0]
        self.assertAlmostEqual(s['cat']['dwell'], 8000, delta=1)

    def test_dead_code_after_m30(self):
        s = run('imv', HEAD + 'M30\nM98 P2000\nM30\n')['setups'][0]
        self.assertIn('После M30', codes(s))


class Checks(unittest.TestCase):
    def test_machine_specific_codes(self):
        s = run('imv', HEAD.replace('G54', 'G154 P3') + 'M30\n')['setups'][0]
        self.assertIn('G154', codes(s, 'error'))
        s = run('haas', HEAD.replace('G54', 'G54.1 P3') + 'M30\n')['setups'][0]
        self.assertIn('G54.1', codes(s, 'error'))
        s = run('imv', HEAD + 'M97 P10\nM30\nN10 M99\n')['setups'][0]
        self.assertIn('M97', codes(s, 'error'))

    def test_tool_and_spindle_checks(self):
        prog = ('%\nO1000\nT5 M6\nG0 G43 H7 Z50. S900 M3\nG1 Z0 F100.\nM5\nG1 X10.\nT6 M6\nG0 X0 Y0 Z5. S500 M3\n'
                'G1 Z0 F100.\nM30\n')
        s = run('haas', prog)['setups'][0]
        self.assertIn('G43 H', codes(s))          # H7 при T5
        self.assertIn('Шпиндель', codes(s, 'error'))
        self.assertIn('G43', codes(s, 'error'))   # T6 без G43

    def test_arc_radius_errors(self):
        s = run('imv', HEAD + 'G0 X0 Y0 Z1.\nG1 Z0 F100.\nG3 X0 Y10. R2.\nG3 X12. Y10. I5. J0\nM30\n')['setups'][0]
        self.assertIn('G3 R', codes(s, 'error'))
        self.assertIn('Дуга', codes(s, 'error'))

    def test_overtravel_by_g53(self):
        s = run('haas', HEAD + 'G53 X-900.\nM30\n')['setups'][0]
        self.assertIn('Ход X', codes(s, 'error'))

    def test_hnc8_m98_must_be_alone(self):
        s = run('imv', HEAD + 'G0 Z10. M98 P200\nM30\nO200\nM99\n')['setups'][0]
        self.assertIn('M98/M99', codes(s))

    def test_infinite_loop_is_stopped(self):
        s = run('imv', HEAD + 'N10 G4 X0.1\nGOTO10\nM30\n')['setups'][0]
        self.assertTrue(s['incomplete'])


if __name__ == '__main__':
    unittest.main()
