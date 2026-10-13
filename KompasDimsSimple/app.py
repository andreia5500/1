# -*- coding: utf-8 -*-
import copy
import math
import sheet_names as N
import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import kompas_dims as K
import tolerances as T
import transfer as X
import cards as C
import layout as L
import requirements as R
import instruments as I
import debug_log as J
import ui as U


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        U.theme(self)
        U.window(self,'Размеры → ТП · '+J.VERSION,1240,800,950,640)
        J.event('Запуск программы',**J.runtime())
        self.report_callback_exception=self.callback_error
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.dims, self.geoms, self.checked = [], {}, set()
        self.busy = False
        self.events = queue.Queue()
        self.status = tk.StringVar(value='1. Откройте чертёж. 2. Отметьте размеры. 3. Перенесите в ТП.')
        header=U.header(self,'Размеры → ТП','Размеры, допуски и инструмент — в выбранные листы техпроцесса.')
        U.journal_button(header,self).pack(side='right')
        source=ttk.LabelFrame(self,text='1. Чертёж',padding=12);source.pack(fill='x',padx=16,pady=(4,12))
        ttk.Button(source,text='Открыть чертёж…',command=self.open_drawing,style='Accent.TButton').pack(side='left')
        self.file_label=ttk.Label(source,text='Чертёж не выбран',style='Muted.TLabel');self.file_label.pack(side='left',padx=16)
        # Keep the workflow and status visible when the table grows.
        footer=ttk.Frame(self,padding=(16,8,16,10));footer.pack(side='bottom',fill='x')
        self.progress=ttk.Progressbar(footer,mode='indeterminate',length=105);self.progress.pack(side='right',padx=(12,0))
        status=ttk.Label(footer,textvariable=self.status,style='Muted.TLabel',wraplength=1050)
        status.pack(side='left',fill='x',expand=True)
        footer.bind('<Configure>',lambda e:status.configure(wraplength=max(300,e.width-160)))
        actions=ttk.LabelFrame(self,text='3. Работа с ТП',padding=12);actions.pack(side='bottom',fill='x',padx=16,pady=(8,0))
        self.transfer_button=ttk.Button(actions,text='Карта контроля…',command=self.open_transfer,style='Accent.TButton',state='disabled')
        for i,button in enumerate((self.transfer_button,
                ttk.Button(actions,text='Допуски на эскизе…',command=self.open_sketch),
                ttk.Button(actions,text='Ведомость оснастки…',command=self.open_tooling))):
            actions.columnconfigure(i,weight=1,uniform='actions');button.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 8,0))
        heading=ttk.Frame(self);heading.pack(fill='x',padx=16)
        ttk.Label(heading,text='2. Размеры и допуски',style='Heading.TLabel').pack(side='left')
        ttk.Button(heading,text='Снять отметки',command=lambda:self.mark_all(False)).pack(side='right')
        ttk.Button(heading,text='Отметить всё',command=lambda:self.mark_all(True)).pack(side='right',padx=8)
        row=ttk.Frame(self,padding=(0,8,0,8));row.pack(fill='x',padx=16)
        ttk.Label(row,text='Неуказанные линейные допуски:').pack(side='left')
        self.mode = tk.StringVar(value='ГОСТ 30893.1')
        self.grade = tk.StringVar(value='m')
        cb=ttk.Combobox(row, textvariable=self.mode, values=['ГОСТ 30893.1','±IT14/2'], width=16, state='readonly'); cb.pack(side='left',padx=5)
        ttk.Label(row, text='Класс:').pack(side='left')
        gc=ttk.Combobox(row,textvariable=self.grade,values=['f','m','c','v'],width=3,state='readonly'); gc.pack(side='left',padx=5)
        cb.bind('<<ComboboxSelected>>',lambda e:self.recalc());gc.bind('<<ComboboxSelected>>',lambda e:self.recalc())
        ttk.Label(self,text='Галочка — включить запись. Двойной щелчок — изменить размер, вид или меритель.',style='Muted.TLabel').pack(anchor='w',padx=16,pady=(0,8))
        frame=ttk.Frame(self);frame.pack(fill='both',expand=True,padx=16)
        self.table=ttk.Treeview(frame,columns=('use','dim','kind','source','view','instrument','note'),show='headings')
        for name,title,width in [('use','✓',35),('dim','Размер с допуском',220),('kind','Тип',95),('source','Допуск',70),('view','Вид',140),('instrument','Меритель',250),('note','Примечание',200)]:
            self.table.heading(name,text=title);self.table.column(name,width=width,stretch=name not in ('use','source'))
        U.table_scroll(self.table)
        self.table.bind('<Button-1>',self.toggle)
        self.table.bind('<Double-1>',self.edit)
        ttk.Label(self,text='Индексы в таблице показаны в [скобках]; в КОМПАС передаётся штатное обозначение.',style='Muted.TLabel').pack(anchor='w',padx=16,pady=(6,0))
        self.after(80,self.poll)

    def close(self):
        if self.busy:
            self.status.set('Дождитесь окончания операции перед закрытием программы.')
            return
        self.destroy()

    def run(self, job, done, label, failed=None):
        if self.busy:return
        self.busy=True;self.status.set(label);self.configure(cursor='watch');U.busy(self,True);self.progress.start(12)
        op_id=J.new_id()
        def worker():
            try:
                with J.operation(label,op_id):
                    import pythoncom
                    pythoncom.CoInitialize()
                    try:result=job()
                    finally:pythoncom.CoUninitialize()
                self.events.put((done,result,None,op_id,failed))
            except Exception as exc:
                self.events.put((done,None,(str(exc),traceback.format_exc()),op_id,failed))
        threading.Thread(target=worker,daemon=True,name='COM-'+op_id).start()

    def callback_error(self,kind,exc,tb):
        exc=exc.with_traceback(tb);J.failure('Ошибка интерфейса',exc)
        messagebox.showerror('Ошибка интерфейса',str(exc)+'\n\nЖурнал: '+str(J.log_path()),parent=self)

    def poll(self):
        try:
            while True:
                done,result,error,op_id,failed=self.events.get_nowait()
                self.busy=False;self.configure(cursor='');U.busy(self,False);self.progress.stop()
                if error:
                    try:
                        with (X.backup_folder()/'error.log').open('a',encoding='utf-8') as log:
                            log.write('\nОперация '+op_id+'\n'+error[1]+'\n')
                    except OSError:pass
                    self.status.set('Операция остановлена. Подробности в сообщении.')
                    if failed:
                        try:failed(error[0])
                        except Exception as exc:J.failure('Ошибка отображения состояния операции',exc)
                    messagebox.showerror('Ошибка',error[0]+'\n\nОперация: '+op_id+'\nЖурнал: '+str(J.log_path()),parent=self)
                else:
                    try:
                        with J.operation('Отображение результата',op_id):done(result)
                    except Exception as exc:self.callback_error(type(exc),exc,exc.__traceback__)
        except queue.Empty:pass
        self.after(80,self.poll)

    def open_drawing(self):
        if self.busy:return
        path=filedialog.askopenfilename(parent=self,title='Исходный чертёж',filetypes=[('Чертёж КОМПАС','*.cdw')])
        if not path:return
        def job():
            module,app=K.connect();doc=X.open_doc(module,app,path)
            dimension_warnings=[]
            dims,geoms=K.collect(module,module.IKompasDocument2D(doc),warnings=dimension_warnings)
            K.classify_diameters(dims,geoms)
            extra,warnings=R.read(module,module.IKompasDocument2D(doc))
            warnings=dimension_warnings+warnings
            dims.extend(extra)
            K.apply_view_roles(dims,module,module.IKompasDocument2D(doc))
            return dims,geoms,warnings
        def done(result):
            self.dims,self.geoms,warnings=result
            J.event('Чтение чертежа завершено',path=path,count=len(self.dims),warnings=warnings)
            self.checked=set(range(len(self.dims)))
            self.file_label.configure(text=path.replace('\\','/').rsplit('/',1)[-1]);self.recalc()
            if warnings:
                log=X.backup_folder()/'reading_warnings.txt'
                log.write_text('\n'.join(warnings),encoding='utf-8')
                messagebox.showwarning('Прочитано не всё','\n'.join(warnings[:8])+'\n\nПолный список: '+str(log),parent=self)
        self.run(job,done,'Читаю размеры чертежа…')

    def recalc(self):
        if self.busy:return
        try:
            K.assign_tolerances(self.dims, self.grade.get(), 'it14' if self.mode.get()=='±IT14/2' else 'gost')
            I.assign(self.dims)
            self.refresh()
        except Exception as e:
            J.failure('Ошибка расчёта допусков',e)
            messagebox.showerror('Допуски',str(e),parent=self)

    def refresh(self):
        self.table.delete(*self.table.get_children())
        self.table.tag_configure('review',foreground='#965100')
        for i,d in enumerate(self.dims):
            text=X.display(d.column_text())
            tags=(('stripe',) if i%2 else ())+(('review',) if K.diameter_uncertain(d) else ())
            self.table.insert('','end',iid=str(i),tags=tags,values=('✓' if i in self.checked else '',text,d.kind,'вручную' if d.manual_tol else d.src,d.view_label or d.view,d.instrument,d.export_error or d.note or d.reason))
        self.transfer_button.configure(state='normal' if self.checked else 'disabled')
        self.status.set('Прочитано %d записей; отмечено %d. Меритель не выбран: %d.' % (len(self.dims),len(self.checked),sum(d.instrument==I.MANUAL for d in self.dims)))

    def mark_all(self, yes):
        if self.busy:return
        self.checked=set(range(len(self.dims))) if yes else set();self.refresh()

    def toggle(self,event):
        if self.busy or self.table.identify_column(event.x)!='#1':return
        row=self.table.identify_row(event.y)
        if not row:return
        i=int(row)
        self.checked.symmetric_difference_update({i});self.refresh()

    def edit(self,event):
        if self.busy or self.table.identify_column(event.x)=='#1':return
        row=self.table.identify_row(event.y)
        if not row:return
        if self.table.identify_column(event.x)=='#5':
            self.edit_view(self.dims[int(row)])
            return
        d=self.dims[int(row)]
        if self.table.identify_column(event.x)=='#6' or d.kind in (K.KIND_ROUGHNESS,K.KIND_FORM_TOL,'требование','надпись'):
            self.edit_instrument(d);return
        w=U.dialog(self,'Размер и допуск',540,350)
        values=[tk.StringVar(value=d.kind),tk.StringVar(value=T.fmt_num(d.hi)),tk.StringVar(value=T.fmt_num(d.lo))]
        ttk.Label(w,text=X.display(d.column_text())).grid(row=0,column=0,columnspan=2,padx=15,pady=10)
        for i,label in enumerate(('Тип','Верхнее отклонение','Нижнее отклонение'),1):
            ttk.Label(w,text=label).grid(row=i,column=0,padx=10,pady=5,sticky='w')
            if i==1:widget=ttk.Combobox(w,textvariable=values[0],values=[K.KIND_OUTER,K.KIND_INNER,K.KIND_LINEAR,K.KIND_RADIUS,K.KIND_CHAMFER,K.KIND_ANGLE,K.KIND_THREAD],state='readonly')
            else:widget=ttk.Entry(w,textvariable=values[i-1])
            widget.grid(row=i,column=1,padx=10,pady=5)
        ttk.Label(w,text='Для углов — градусы: 30 минут = 0,5.').grid(row=4,column=0,columnspan=2,padx=10)
        def save():
            try:
                hi=float(values[1].get().replace(',','.')) if values[1].get().strip() else None
                lo=float(values[2].get().replace(',','.')) if values[2].get().strip() else None
                if (hi is None)!=(lo is None):raise ValueError('Заполните оба отклонения. Если одно равно нулю, введите 0.')
                if hi is not None and not all(math.isfinite(v) for v in (hi,lo)):raise ValueError('Отклонения должны быть конечными числами.')
                if hi is not None and hi<lo:raise ValueError('Верхнее отклонение меньше нижнего.')
                if d.note.startswith('допуск в тексте:'):raise ValueError('Этот допуск вписан в текст чертежа. Исправьте его на чертеже и перечитайте.')
                d.kind=values[0].get();d.manual=True;d.fit='';d.hi=hi;d.lo=lo;d.manual_tol=hi is not None
                if not d.manual_tol:d.src=K.SRC_DEFAULT
                w.destroy();self.recalc()
            except ValueError as e:messagebox.showerror('Допуск',str(e),parent=w)
        ttk.Button(w,text='Отмена',command=w._close).grid(row=5,column=0,pady=12)
        ttk.Button(w,text='Применить',command=save,style='Accent.TButton').grid(row=5,column=1,pady=12)

    def edit_instrument(self,d):
        w=U.dialog(self,'Меритель',820,260)
        ttk.Label(w,text=X.display(d.column_text()),wraplength=650).pack(padx=12,pady=10)
        value=tk.StringVar(value=d.instrument)
        ttk.Combobox(w,textvariable=value,values=['']+I.CATALOG,width=85).pack(padx=12,pady=8)
        ttk.Label(w,text='Можно выбрать из списка или вписать свой. Порог диаметра — ширина допуска 0,1 мм.').pack(padx=12,pady=6)
        def save():
            d.instrument=value.get().strip();d.instrument_manual=True
            w.destroy();self.refresh()
        def reset():
            d.instrument_manual=False;I.assign([d]);w.destroy();self.refresh()
        ttk.Button(w,text='Применить',command=save,style='Accent.TButton').pack(side='right',padx=12,pady=12)
        ttk.Button(w,text='Отмена',command=w._close).pack(side='right',pady=12)
        ttk.Button(w,text='Подобрать автоматически',command=reset).pack(side='left',padx=12,pady=12)

    def edit_view(self,d):
        w=U.dialog(self,'Название вида',520,210)
        ttk.Label(w,text='В чертеже: '+d.view).pack(padx=12,pady=8)
        label=tk.StringVar(value=d.view_label or d.view)
        ttk.Combobox(w,textvariable=label,width=35,values=['Главный вид','Вид слева','Вид справа','Вид сверху','Вид снизу','Вид сзади']).pack(padx=12,pady=5)
        def save():
            value=label.get().strip().rstrip(':')
            if not value:return
            for dim in self.dims:
                if dim.view==d.view:dim.view_label=value
            w.destroy();self.refresh()
        bar=ttk.Frame(w);bar.pack(fill='x',padx=12,pady=12)
        ttk.Button(bar,text='Применить к виду',command=save,style='Accent.TButton').pack(side='right')
        ttk.Button(bar,text='Отмена',command=w._close).pack(side='right',padx=8)

    def open_tooling(self):
        if self.busy:return
        from tooling_dialog import ToolingWindow
        path=filedialog.askopenfilename(parent=self,title='ТП для ведомости оснастки',filetypes=[('ТП КОМПАС','*.cdw')])
        if path:self.run(lambda:X.sheet_list(path),lambda sheets:ToolingWindow(self,path,sheets),'Читаю названия листов ТП…')

    def open_sketch(self):
        if self.busy:return
        from sketch_dialog import SketchWindow
        path=filedialog.askopenfilename(parent=self,title='ТП с эскизами КЭ ЧПУ',filetypes=[('ТП КОМПАС','*.cdw')])
        if not path:return
        sources=copy.deepcopy(self.dims)
        grade=self.grade.get();mode='it14' if self.mode.get()=='±IT14/2' else 'gost'
        self.run(lambda:X.sheet_list(path),lambda sheets:SketchWindow(self,path,sheets,sources,grade,mode),'Читаю листы ТП…')

    def open_transfer(self):
        if self.busy:return
        dims=[copy.deepcopy(d) for i,d in enumerate(self.dims) if i in self.checked]
        if not dims:messagebox.showinfo('Выберите размеры','Отметьте хотя бы один размер.',parent=self);return
        try:lines=L.groups(dims)
        except ValueError as e:messagebox.showerror('Проверьте размеры',str(e),parent=self);return
        path=filedialog.askopenfilename(parent=self,title='Техпроцесс для переноса',filetypes=[('ТП КОМПАС','*.cdw')])
        if not path:return
        self.run(lambda:X.sheet_list(path),lambda sheets:TransferWindow(self,path,sheets,lines),'Читаю листы ТП…')


class TransferWindow(tk.Toplevel):
    def __init__(self,app,path,sheets,groups):
        super().__init__(app)
        self.app,self.path,self.sheets,self.groups=app,path,sheets,groups
        self.block,self.pages=None,[]
        U.window(self,'Карта контроля',1240,760,960,600);self.transient(app);self.grab_set()
        self.protocol('WM_DELETE_WINDOW',self.close)
        U.header(self,'Карта контроля',path)
        buttons=ttk.Frame(self);buttons.pack(side='bottom',fill='x',padx=16,pady=(8,12))
        self.send=ttk.Button(buttons,text='Записать в карту контроля',command=self.write,state='disabled',style='Accent.TButton');self.send.pack(side='right')
        ttk.Button(buttons,text='Закрыть',command=self.close).pack(side='right',padx=10)
        U.journal_button(buttons,self).pack(side='left')
        self.info=tk.StringVar(value='Выберите первый лист карты контроля и строку начала записи.')
        ttk.Label(self,textvariable=self.info,wraplength=1150,style='Muted.TLabel').pack(side='bottom',fill='x',padx=16,pady=(8,0))
        bar=ttk.Frame(self);bar.pack(fill='x',padx=12)
        ttk.Label(bar,text='Первый лист карты:').pack(side='left')
        self.sheet=ttk.Combobox(bar,state='readonly',width=27,values=[N.label(sheet) for sheet in sheets])
        self.sheet.pack(side='left',padx=6);self.sheet.bind('<<ComboboxSelected>>',self.load)
        ttk.Label(bar,text='Начать со строки:').pack(side='left',padx=10)
        self.start=tk.StringVar(value='1')
        self.start_box=ttk.Combobox(bar,textvariable=self.start,state='readonly',width=4,values=list(range(1,14)))
        self.start_box.pack(side='left');self.start.trace_add('write',lambda *a:self.preview())
        ttk.Label(self,text='Выберите первый лист ОК ТК. В таблице показано содержимое до и после переноса.',style='Muted.TLabel').pack(anchor='w',padx=16,pady=10)
        frame=ttk.Frame(self);frame.pack(fill='both',expand=True,padx=12)
        columns=('sheet','row','old','new','oldtool','newtool')
        self.table=ttk.Treeview(frame,columns=columns,show='headings')
        for key,title,width in [('sheet','Лист',55),('row','Строка',55),('old','Параметры: было',245),('new','Параметры: станет',245),('oldtool','Меритель: было',220),('newtool','Меритель: станет',220)]:
            self.table.heading(key,text=title);self.table.column(key,width=width,stretch=key not in ('sheet','row'))
        self.table.tag_configure('heading',font=('Segoe UI',10,'bold'))
        self.table.tag_configure('new',background='#e9f5e9')
        U.table_scroll(self.table)

    def close(self):
        if not self.app.busy:self.destroy()

    def unlock(self):
        if not self.winfo_exists():return
        if self.app.busy:self.after(100,self.unlock)
        else:
            self.sheet.configure(state='readonly');self.start_box.configure(state='readonly')

    def load(self,event=None):
        if self.app.busy:return
        self.block=None;self.preview();index=self.sheet.current()
        self.sheet.configure(state='disabled');self.start_box.configure(state='disabled')
        self.info.set('Читаю выбранную карту контроля…')
        self.app.run(lambda:C.read_block(self.path,self.sheets[index][0]),self.loaded,'Читаю карты контроля…',self.failed)
        self.after(100,self.unlock)

    def loaded(self,block):
        self.block=block
        self.start_box['values']=list(range(1,len(block['pages'][0]['rows'])+1))
        self.start.set('1');self.preview()

    def preview(self):
        self.table.delete(*self.table.get_children());self.send.configure(state='disabled');self.pages=[]
        if not self.block:return
        try:self.pages=C.plan(self.block,self.groups,int(self.start.get())-1)
        except ValueError as exc:self.info.set(str(exc));return
        for page in self.pages:
            for index,(old,new) in enumerate(zip(page['rows'],page['after'])):
                if new is None:continue
                tags=['new'] if page['new'] else []
                if new['bold']:tags.append('heading')
                self.table.insert('','end',values=(str(page['index']+1)+(' +' if page['new'] else ''),index+1,
                    X.display(old['param']['text']),X.display(new['text']),X.display(old['instrument']['text']),X.display(new['instrument'])),tags=tags)
        added=sum(p['new'] for p in self.pages)
        self.info.set('Карты: листы %d–%d. Новых листов: %d. Заменяются параметры и мерители; остаток этих граф очищается. В пустых строках и заголовках очищается также объём контроля. Проценты остальных строк проверьте. Сохранение ТП — вручную.' %
                      (self.pages[0]['index']+1,self.pages[-1]['index']+1,added))
        self.send.configure(state='normal')

    def failed(self,error):
        self.block,self.pages=None,[];self.send.configure(state='disabled')
        self.info.set('Операция остановлена. Перечитайте карту. Подробности доступны в журнале отладки.')

    def write(self):
        if self.app.busy or not self.pages:return
        block,pages=copy.deepcopy(self.block),copy.deepcopy(self.pages)
        self.send.configure(state='disabled');self.sheet.configure(state='disabled');self.start_box.configure(state='disabled')
        self.info.set('Записываю выбранные карты и проверяю результат…')
        self.app.run(lambda:C.write(self.path,block,pages),self.done,'Записываю карты контроля и проверяю результат…',self.failed)
        self.after(100,self.unlock)

    def done(self,n):
        self.info.set('Перенесено заполненных строк: %d. Проверьте результат в КОМПАСе и сохраните ТП (Ctrl+S).'%n)
        self.app.status.set('Перенос выполнен. Проверьте карту и сохраните ТП.')
        self.block,self.pages=None,[]


if __name__=='__main__':
    App().mainloop()


