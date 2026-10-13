"""Controller/error-flow tests without a display or installed KOMPAS."""
import json
import queue
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import app as A
import debug_log as J
import kompas_dims as K
import tooling_dialog as D


class Var:
    def __init__(self):self.value=''
    def set(self,value):self.value=value


class WorkflowTests(unittest.TestCase):
    def worker_app(self):
        return NS(busy=False,status=Var(),events=queue.Queue(),configure=lambda **kw:None,
                  progress=NS(start=lambda _:None,stop=lambda:None),after=lambda *args:None,
                  poll=lambda:None,callback_error=lambda *args:self.fail('Unexpected UI exception'))

    def test_background_success_balances_com_and_delivers_callback(self):
        instance=self.worker_app();calls=[]
        pythoncom=NS(CoInitialize=lambda:calls.append('init'),CoUninitialize=lambda:calls.append('uninit'))
        with tempfile.TemporaryDirectory() as folder,patch.object(J,'folder',return_value=Path(folder)),patch.object(A.U,'busy'),patch.dict('sys.modules',pythoncom=pythoncom):
            A.App.run(instance,lambda:42,lambda result:calls.append(result),'Чтение ТП')
            event=instance.events.get(timeout=2);instance.events.put(event);A.App.poll(instance)
            self.assertEqual(calls,['init','uninit',42]);self.assertFalse(instance.busy)

    def test_background_error_clears_busy_notifies_window_and_appends_errors(self):
        instance=self.worker_app();calls=[]
        pythoncom=NS(CoInitialize=lambda:calls.append('init'),CoUninitialize=lambda:calls.append('uninit'))
        with tempfile.TemporaryDirectory() as folder,patch.object(J,'folder',return_value=Path(folder)),patch.object(A.X,'backup_folder',return_value=Path(folder)),patch.object(A.U,'busy'),patch.dict('sys.modules',pythoncom=pythoncom),patch.object(A.messagebox,'showerror') as popup:
            for _ in range(2):
                def bad():raise RuntimeError('Ошибка выбранного листа')
                A.App.run(instance,bad,lambda _:self.fail('No success callback'), 'Запись ТП',lambda error:calls.append(error))
                event=instance.events.get(timeout=2);instance.events.put(event);A.App.poll(instance)
                self.assertFalse(instance.busy)
            self.assertEqual(popup.call_count,2)
            self.assertEqual(calls.count('Ошибка выбранного листа'),2)
            self.assertEqual((Path(folder)/'error.log').read_text(encoding='utf-8').count('RuntimeError: Ошибка выбранного листа'),2)

    def test_filtered_page_lists_route_to_original_document_indices(self):
        class List:
            def __init__(self,role):self._role=role;self.labels=[]
            def delete(self,*args):self.labels=[]
            def insert(self,_,text):self.labels.append(text)
        rows=json.loads((Path(__file__).parent/'tp_fixture.json').read_text(encoding='utf-8'))['sheets']
        import sheet_names as N
        descriptors=[(i,r['style'],N.short(r['name'])) for i,r in enumerate(rows)]
        sources,targets=List('sources'),List('targets')
        D.ToolingWindow.fill_list(None,sources,descriptors);D.ToolingWindow.fill_list(None,targets,descriptors)
        self.assertEqual([s[0] for s in targets._sheets],[2,3])
        self.assertIn('3',targets.labels[0]);self.assertIn('МК ВО',targets.labels[0])
        self.assertIn(17,[s[0] for s in sources._sheets])
        self.assertNotIn(2,[s[0] for s in sources._sheets])

    def test_unreadable_dimension_is_reported_without_losing_other_dimensions(self):
        collection=NS(Count=2,LineDimension=lambda i:NS(bad=i==1))
        sym=NS(LineDimensions=collection)
        view=NS(Name='Главный вид')
        doc=NS(ViewsAndLayersManager=NS(Views=NS(Count=1,View=lambda i:view)))
        good=K.Dim();good.value=20
        def read(_,obj,*args):
            if obj.bad:raise RuntimeError('Ошибка чтения допуска')
            return good
        warnings=[]
        with patch.object(K.Geometry,'from_view',return_value=K.Geometry()),patch.object(K,'read_dimension',side_effect=read):
            dims,_=K.collect(NS(ISymbols2DContainer=lambda _:sym),doc,warnings=warnings)
        self.assertEqual(dims,[good])
        self.assertTrue(any('LineDimensions[1]' in w for w in warnings))
