"""Автомат: главный/контршпиндель определяются сами, программ не больше двух."""
import unittest
from pathlib import Path

import auto_dialog as A

PROG = Path(__file__).parent / 'nc_tests' / 'programs'


def item(name, text):
    return dict(name=name, path=name, text=text, no=A.program_number(name, text), title=A.header_comment(text))


class Sides(unittest.TestCase):
    def test_real_pairs(self):
        for main, counter in (('O6017', 'O6018'), ('O6108', 'O6109')):
            a, b = item(main, (PROG / main).read_text()), item(counter, (PROG / counter).read_text())
            for order in ((a, b), (b, a)):
                slots, _ = A.assign(list(order))
                self.assertEqual(slots['S1']['name'], main)
                self.assertEqual(slots['S2']['name'], counter)

    def test_single_program_goes_to_its_side(self):
        slots, _ = A.assign([item('O6018', (PROG / 'O6018').read_text())])
        self.assertEqual(list(slots), ['S2'])
        slots, _ = A.assign([item('O6017', (PROG / 'O6017').read_text())], slots)
        self.assertEqual(slots['S1']['name'], 'O6017')
        self.assertEqual(slots['S2']['name'], 'O6018')

    def test_tie_is_decided_by_number(self):
        slots, note = A.assign([item('b', 'O200\n!L1\nG0X1.\nM99'), item('a', 'O100\n!L1\nG0X1.\nM99')])
        self.assertEqual(slots['S1']['no'], '100')
        self.assertIn('Поменять', note)

    def test_programs_and_subprograms(self):
        self.assertTrue(A.is_system((PROG / 'O6017').read_text()))
        self.assertTrue(A.is_system((PROG / 'O6109').read_text()))
        for sub in ('O5000', 'O5001', 'O5002'):
            self.assertFalse(A.is_system((PROG / sub).read_text()))
        self.assertIn('5000', A.called_subs((PROG / 'O6017').read_text()))


if __name__ == '__main__':
    unittest.main()
