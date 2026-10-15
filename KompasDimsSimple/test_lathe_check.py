"""Автомат: траектория, модель заготовки и проверки врезаний/резьбы/припуска; исправления движка 2.3.0."""
import unittest
from pathlib import Path

import auto_dialog as A
import lathe_check as L
import nc_engine as E

PROG = Path(__file__).parent / 'nc_tests' / 'programs'
HEAD = 'O1000(TEST)\n(ZAGOTOVKA - KRUG D20)\nG0G40G80G99G18T0\nT0202(CNMG)\nG50S1=3000\nG96S1=150M03\nG0X24.Z-1.\nG1Z0.F0.1\nX-1.\nG0Z-1.\n'


def sim_of(text, subs=None):
    sims, rep = E.calculate([dict(name='S1', spindle='1', text=text)], subs or {}, E.default_params())
    return sims[0], rep


def codes(text, names=None):
    sim, _ = sim_of(text)
    return [i['code'] for i in L.analyze(sim, text, names or {'0202': 'CNMG', '0303': 'REZBA'})['issues']]


class Engine(unittest.TestCase):
    def test_profile_label_searched_forward(self):
        text = HEAD + ('X22.\nG71U1.R0.2\nG71P10Q20U0.F0.2\nN10G1X16.\nZ10.\nN20X22.\nG0X40.\n'
                       'G0X22.Z9.\nG71U1.R0.2\nG71P10Q20U0.F0.2\nN10G1X14.Z9.\nZ20.\nN20X22.\nM30')
        sim, _ = sim_of(text)
        profiles = [c for c in sim.cycles if c['kind'] == 'G71']
        self.assertEqual(len(profiles), 2)
        self.assertAlmostEqual(profiles[1]['profile'][-2][1], 20.0)   # второй цикл взял свой N10–N20
        _, _, found = E.validate_program(text)
        self.assertIn('CYCLE-PQ-DUP', [f['code'] for f in found])
        self.assertNotIn('CYCLE-PQ-ORDER', [f['code'] for f in found])

    def test_sync_codes_are_not_moves(self):
        sim, _ = sim_of('G0X10.Z5.\nG98G1Z50.F100.\nG125Z2\nM30')
        self.assertEqual(sim.pos['Z'], 50.0)

    def test_g75_grooving_time_and_path(self):
        sim, _ = sim_of('G97S1=1000M3\nG0X20.Z10.\nG75R0.5\nG75X10.Z14.P2.Q2.F0.1\nM30')
        grooves = [s for s in sim.path if s['kind'] == 'groove']
        self.assertEqual(len(grooves), 3)                    # Z10, Z12, Z14
        self.assertGreater(sim.cutting_ms, 3 * 5 / 100 * 60000 * 0.99)

    def test_thread_checks_in_validator(self):
        found = [f['code'] for f in E.validate_program('G96S1=100M3\nG76P020061Q0.1R0.1\nG76X10.Z20.P0.8Q1.F1.3\n')[2]]
        for code in ('G96-G50', 'G76-P', 'G76-Q', 'THREAD-G96', 'THREAD-F'):
            self.assertIn(code, found)


class Stock(unittest.TestCase):
    def test_rapid_into_material(self):
        self.assertIn('G0 в материал', codes(HEAD + 'G0X16.Z5.\nM30'))
        self.assertIn('G0 в материал', codes(HEAD + 'G0X22.Z5.\nM30'))       # по диагонали через торец
        self.assertNotIn('G0 в материал', codes(HEAD + 'G0X22.\nZ5.\nM30'))   # сначала вверх, потом вдоль

    def test_thread_end_beyond_relief_groove(self):
        text = HEAD + ('G0X22.Z0.\nG1X16.F0.1\nZ10.\nX12.\nZ12.\nX16.\nZ20.\nX22.\nG0X30.\n'
                       'G97S1=800M3\nG0X18.Z-3.\nG76P010060Q0.1R0.1\nG76X14.Z13.P1.Q0.3F1.5\nM30')
        found = codes(text)
        self.assertIn('G76 конец', found)
        ok = text.replace('G76X14.Z13.', 'G76X14.Z11.')
        self.assertNotIn('G76 конец', codes(ok))

    def test_thread_start_clearance_and_oversize(self):
        text = HEAD + ('G0X22.Z-1.\nG71U1.R0.2\nG71P10Q20U0.4F0.2\nN10G1X16.\nZ10.\nN20X22.\nG0X30.\n'
                       'G97S1=800M3\nG0X16.Z-3.\nG76P010060Q0.1R0.1\nG76X14.Z8.P1.Q0.3F1.5\nM30')
        found = codes(text)
        self.assertIn('G76 отвод', found)
        self.assertIn('G76 Ø', found)
        self.assertIn('Припуск', found)

    def test_reference_programs_have_no_geometry_errors(self):
        for name in ('O6017', 'O6108'):
            text = (PROG / name).read_text()
            sim, _ = sim_of(text, {n: (PROG / ('O' + n)).read_text() for n in ('5000', '5001', '5002')})
            names = {x['T']: x['name'] for x in A.tool_list(text)}
            errors = [i for i in L.analyze(sim, text, names)['issues'] if i['severity'] == 'error']
            self.assertEqual(errors, [], name)

    def test_bar_diameter(self):
        self.assertEqual(L.bar_diameter('(ZAGOTOVKA - KRUG D28 40X)'), 28.0)
        self.assertEqual(L.bar_diameter('#20=26.(DIAMETR ZAGOTOVKI)'), 26.0)


if __name__ == '__main__':
    unittest.main()


class Manual(unittest.TestCase):
    """По руководству M800/M80 (токарный) и «Техническому обслуживанию» Diamond CSBII/CSBIII."""

    def test_g83_r_is_distance_from_start(self):
        sim, _ = sim_of('G97S1=1000M3\nG99\nG0X0Z-5.\nG83Z10.R2.F0.1\nM30')
        drill = next(s for s in sim.path if s['kind'] == 'drill')
        self.assertEqual(drill['pts'][0][1], -3.0)      # R2 от Z-5 -> Z-3
        self.assertEqual(sim.pos['Z'], -5.0)            # возврат в исходную точку
        sim2, _ = sim_of('G97S1=1000M3\nG99\nG0X0Z-5.\nG83Z10.R2.F0.1K0\nM30')
        self.assertFalse([s for s in sim2.path if s['kind'] == 'drill'])

    def test_goto_searches_forward_first(self):
        sim, _ = sim_of('#1=0\nN10G98G1W-1.F100.\n#1=#1+1\nIF[#1LT2]GOTO20\nM30\nN20G4X1.\nGOTO10\nN10G4X5.\nM30')
        raws = [b['raw'] for b in sim.block_log]
        self.assertIn('N10G4X5.', raws)                  # GOTO10 из стр. 7 нашёл N10 ниже, а не в начале
        self.assertEqual(raws.count('N10G98G1W-1.F100.'), 1)

    def test_list2_single_cycles(self):
        sim, _ = sim_of('G97S1=1000M3\nG99\nG0X30.Z1.\nG90X26.Z-20.F0.1\nX24.\nG0X30.Z1.\nG94X10.Z-1.F0.1\nM30')
        self.assertTrue(sim.feed_per_rev)              # G94 здесь не подача в минуту
        feeds = [s for s in sim.path if s['kind'] == 'feed']
        self.assertEqual(len(feeds), 3)
        self.assertEqual(feeds[1]['pts'][1], (24.0, -20.0))

    def test_unknown_m_code(self):
        found = [f['code'] for f in E.validate_program('M3\nM06\nM777\n')[2]]
        self.assertEqual(found.count('M?'), 1)

    def test_sync_order_and_missing(self):
        sims, _ = E.calculate([dict(name='S1', spindle='1', text='!L1\nG4X1.\n!L2\nM30'),
                               dict(name='S2', spindle='2', text='!L2\nG4X1.\n!L1\nM30')], {})
        self.assertEqual([f['code'] for f in E.sync_check(sims)][0], 'SYNC-ORDER')
        sims, _ = E.calculate([dict(name='S1', spindle='1', text='#1=0\nIF[#1EQ0]GOTO5\n!L3\nN5!L1\nM30'),
                               dict(name='S2', spindle='2', text='!L3\n!L1\nM30')], {})
        self.assertIn('SYNC-MISS', [f['code'] for f in E.sync_check(sims)])

    def test_timeline_matches_finish(self):
        subs = {n: (PROG / ('O' + n)).read_text() for n in ('5000', '5001', '5002')}
        sims, rep = E.calculate([dict(name='S1', spindle='1', text=(PROG / 'O6017').read_text()),
                                 dict(name='S2', spindle='2', text=(PROG / 'O6018').read_text())], subs)
        tl = E.timeline(sims)
        for sim, finish in zip(sims, rep['finishMs']):
            self.assertAlmostEqual(tl['rows'][sim.name][-1]['t1'], finish, places=3)
        self.assertEqual(len(tl['marks']), len(rep['barriers']))


class WorkingPrograms(unittest.TestCase):
    """Программы, которые работают на станке: проверка не должна находить в них ошибок (✖)."""
    PAIRS = (('O2105', 'O2106'), ('O4009', 'O4010'), ('O4013', 'O4014'), ('O3105', 'O3106'), ('O6102',), ('O6103',))

    def test_no_errors(self):
        subs = {n: (PROG / ('O' + n)).read_text() for n in ('5000', '5001', '5002')}
        for pair in self.PAIRS:
            texts = [(PROG / n).read_text() for n in pair]
            sims, _ = E.calculate([dict(name='S%d' % (i + 1), spindle=str(i + 1), text=t) for i, t in enumerate(texts)], subs)
            errors = [f for f in E.sync_check(sims) if f['severity'] == 'error']
            for name, t in zip(pair, texts):
                errors += [f for f in E.validate_program(t, subs)[2] if f['severity'] == 'error']
            names = {x['T']: x['name'] for x in A.tool_list(texts[0])}
            errors += [i for i in L.analyze(sims[0], texts[0], names)['issues'] if i['severity'] == 'error']
            self.assertEqual([e['message'][:120] for e in errors], [], pair)
