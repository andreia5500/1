"""Постоянная библиотека подпрограмм проверки УП."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import nc_dialog as D
import nc_engine as E


class Library(unittest.TestCase):
    def test_builtin_subprograms_available_without_files(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(D.X, 'backup_folder', return_value=Path(folder)):
            subs = D.load_library()
        self.assertEqual(sorted(subs), ['5000', '5001', '5002'])
        self.assertEqual(subs['5000']['source'], 'встроенная')
        prog = (Path(__file__).parent / 'nc_tests' / 'programs')
        sims, rep = E.calculate([dict(name='S1', spindle='1', text=(prog / 'O6108').read_text()),
                                 dict(name='S2', spindle='2', text=(prog / 'O6109').read_text())],
                                {n: s['text'] for n, s in subs.items()})
        self.assertAlmostEqual(rep['totalMs'], 332863.1915513018, places=6)
        self.assertFalse(any('не загружена' in w for s in sims for w in s.warnings))

    def test_added_subprogram_is_remembered(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(D.X, 'backup_folder', return_value=Path(folder)):
            subs = D.load_library()
            subs['7000'] = dict(text='O7000\nM99', file='O7000.nc', source='добавлена')
            del subs['5001']
            D.save_library(subs)
            again = D.load_library()
        self.assertIn('7000', again);self.assertNotIn('5001', again)


if __name__ == '__main__':
    unittest.main()
