import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile
import debug_log as J


class LoggingTests(unittest.TestCase):
    def test_log_appends_and_keeps_full_com_error_and_operation(self):
        class ComError(Exception):
            hresult=-2147467259;excepinfo=(0,'КОМПАС','Отказ записи',None,0,0);argerror=2
        with tempfile.TemporaryDirectory() as folder,patch.object(J,'folder',return_value=Path(folder)):
            J.event('Старая запись',text='Ø11 −0,1')
            with self.assertRaises(ComError),J.operation('Перенос','test-operation'):
                J.call('ksTextLine',lambda:(_ for _ in ()).throw(ComError('Подробная ошибка')),sheet=3,column=2000)
            records=[json.loads(s) for s in J.log_path().read_text(encoding='utf-8').splitlines()]
            self.assertEqual(records[0]['event'],'Старая запись')
            errors=[r for r in records if r['level']=='ERROR']
            self.assertEqual(len(errors),2)
            for error in errors:
                self.assertEqual(error['operation'],'test-operation')
                self.assertEqual(error['details']['hresult_hex'],'0x80004005')
                self.assertEqual(error['details']['argerror'],2)
                self.assertIn('ComError',error['details']['traceback'])

    def test_threads_have_separate_operation_ids_and_valid_json_lines(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(J,'folder',return_value=Path(folder)):
            def write(n):
                with J.operation('Проверка','op'+str(n)):
                    for i in range(20):J.event('Строка',value=n,index=i)
            threads=[threading.Thread(target=write,args=(n,)) for n in range(4)]
            for t in threads:t.start()
            for t in threads:t.join()
            records=[json.loads(s) for s in J.log_path().read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(records),88)
            for r in records:
                if r['event']=='Строка':self.assertEqual(r['operation'],'op'+str(r['details']['value']))

    def test_export_includes_journal_and_reports(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(J,'folder',return_value=Path(folder)):
            J.event('Прочитан ТП',path='ТП.cdw')
            (Path(folder)/'tooling_sample.json').write_text('{"test":true}',encoding='utf-8')
            output=Path(folder)/'report.zip';J.export_bundle(output)
            with zipfile.ZipFile(output) as archive:
                self.assertIn(J.log_path().name,archive.namelist())
                self.assertIn('tooling_sample.json',archive.namelist())
                self.assertNotIn('report.zip',archive.namelist())

    def test_storage_failure_is_explicit_but_does_not_hide_original_exception(self):
        with patch.object(J,'folder',side_effect=OSError('Нет доступа')):
            exc=RuntimeError('Исходная ошибка записи')
            J.failure('Ошибка',exc)
            with self.assertRaisesRegex(RuntimeError,'Не удалось сохранить журнал'):
                J.require_storage()
        with tempfile.TemporaryDirectory() as folder,patch.object(J,'folder',return_value=Path(folder)):
            J.require_storage()  # Later successful writes recover the logger.
