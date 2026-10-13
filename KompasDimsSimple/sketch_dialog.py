import copy
import sheet_names as N
import math
import tkinter as tk
from tkinter import ttk,messagebox
import kompas_dims as K
import tolerances as T
import sketch as S
import ui as U


class SketchWindow(tk.Toplevel):
    def __init__(self,app,path,sheets,sources,grade,mode):
        super().__init__(app)
        self.app,self.path,self.sheets=app,path,sheets
        self.sources,self.grade,self.mode=sources,grade,mode
        self.data=None;self.checked=set()
        U.window(self,'Допуски на эскизе · КЭ ЧПУ',1240,760,960,600);self.transient(app);self.grab_set()
        self.protocol('WM_DELETE_WINDOW',self.close)
        U.header(self,'Допуски на эскизе',path,icon='sketch')
        buttons=ttk.Frame(self);buttons.pack(side='bottom',fill='x',padx=16,pady=(8,12))
        self.send=ttk.Button(buttons,text='Проставить допуски',command=self.write,state='disabled',style='Accent.TButton');self.send.pack(side='right')
        ttk.Button(buttons,text='Закрыть',command=self.close).pack(side='right',padx=10)
        U.journal_button(buttons,self).pack(side='left')
        self.info=tk.StringVar(value='Выберите лист КЭ ЧПУ с эскизом. Затем отметьте размеры для записи.')
        ttk.Label(self,textvariable=self.info,wraplength=1150,style='Muted.TLabel').pack(side='bottom',fill='x',padx=16,pady=(8,0))
        bar=ttk.Frame(self);bar.pack(fill='x',padx=12)
        ttk.Label(bar,text='Лист эскиза:').pack(side='left')
        self.sheet=ttk.Combobox(bar,state='readonly',width=30,values=[N.label(sheet) for sheet in sheets])
        self.sheet.pack(side='left',padx=8);self.sheet.bind('<<ComboboxSelected>>',self.load)
        ttk.Label(bar,text='Расчёт: '+('±IT14/2' if mode=='it14' else 'ГОСТ 30893.1-'+grade)).pack(side='left',padx=10)
        ttk.Button(bar,text='Снять отметки',command=lambda:self.mark(False)).pack(side='right')
        ttk.Button(bar,text='Отметить доступные',command=lambda:self.mark(True)).pack(side='right',padx=8)
        ttk.Label(self,text='Отметьте размеры для записи. Двойной щелчок — уточнить тип или допуск.\nУже заданные допуски сохраняются; надписи и ТТ не читаются.',wraplength=1150,style='Muted.TLabel').pack(anchor='w',padx=16,pady=12)
        options=ttk.Frame(self);options.pack(fill='x',padx=12,pady=4)
        self.assume_outer=tk.BooleanVar(value=False)
        ttk.Checkbutton(options,text='Неопределённые диаметры считать наружными (перечитать лист)',variable=self.assume_outer,command=self.load).pack(side='left')
        ttk.Button(options,text='Отверстие',command=lambda:self.choose_type(K.KIND_INNER)).pack(side='right')
        ttk.Button(options,text='Вал',command=lambda:self.choose_type(K.KIND_OUTER)).pack(side='right',padx=8)
        ttk.Label(options,text='Тип выбранных строк:',style='Muted.TLabel').pack(side='right',padx=8)
        frame=ttk.Frame(self);frame.pack(fill='both',expand=True,padx=12)
        self.table=ttk.Treeview(frame,columns=('use','before','after','kind','view','reason'),show='headings')
        for col,title,width in [('use','✓',35),('before','Было',140),('after','Станет',180),('kind','Тип',95),('view','Вид',160),('reason','Результат распознавания',370)]:
            self.table.heading(col,text=title);self.table.column(col,width=width,stretch=col!='use')
        self.table.tag_configure('preserved',foreground='#777777')
        self.table.tag_configure('review',foreground='#965100')
        U.table_scroll(self.table)
        self.table.bind('<Button-1>',self.toggle);self.table.bind('<Double-1>',self.edit)

    def close(self):
        if not self.app.busy:self.destroy()

    def unlock(self):
        if not self.winfo_exists():return
        if self.app.busy:self.after(100,self.unlock)
        else:self.sheet.configure(state='readonly')

    def load(self,event=None):
        if self.app.busy:return
        self.data=None;self.checked=set();self.refresh()
        index=self.sheet.current()
        if index<0:return
        number=self.sheets[index][0];self.sheet.configure(state='disabled')
        assume_outer=self.assume_outer.get()
        self.info.set('Распознаю размеры и допуски выбранного эскиза…')
        self.app.run(lambda:S.read(self.path,number,self.sources,self.grade,self.mode,assume_outer),self.loaded,'Распознаю размеры выбранного эскиза…',self.failed)
        self.after(100,self.unlock)

    def loaded(self,data):
        self.data=data;self.checked={r['ref'] for r in data['records'] if r['proposal']}
        self.refresh()
        if data['warnings']:
            messagebox.showwarning('Проверьте пропущенные размеры','\n'.join(data['warnings'][:12]),parent=self)

    def refresh(self):
        self.table.delete(*self.table.get_children());self.send.configure(state='disabled')
        if self.data is None:return
        for r in self.data['records']:
            existing=S.has_existing(r['state'])
            tags=('preserved',) if existing else (() if r['proposal'] else ('review',))
            self.table.insert('','end',iid=str(r['ref']),values=('✓' if r['ref'] in self.checked else '',
                S.preview_text(r['dim'],None),S.preview_text(r['dim'],r['proposal']),r['dim'].kind,r['dim'].view,r['reason']),tags=tags)
        count=len(self.data['records'])
        self.info.set('Найдено размеров: %d. Выбрано для записи: %d. ТП сохраняется вручную.'%(count,len(self.checked)) if count else
                      'На выбранном листе не найдены доступные размерные объекты. Размеры внутри вставок, макроэлементов и размеры, разбитые на линии, не редактируются.')
        self.send.configure(state='normal' if self.checked else 'disabled')

    def mark(self,yes):
        if self.app.busy or self.data is None:return
        self.checked={r['ref'] for r in self.data['records'] if r['proposal']} if yes else set();self.refresh()

    def toggle(self,event):
        if self.app.busy or self.data is None or self.table.identify_column(event.x)!='#1':return
        row=self.table.identify_row(event.y)
        if not row:return
        rec=next(r for r in self.data['records'] if r['ref']==int(row))
        if rec['proposal']:self.checked.symmetric_difference_update({rec['ref']});self.refresh()

    def choose_type(self,kind):
        if self.app.busy or self.data is None:return
        selected={int(i) for i in self.table.selection()}
        for r in self.data['records']:
            if r['ref'] not in selected or S.has_existing(r['state']):continue
            if r['dim'].kind not in (K.KIND_OUTER,K.KIND_INNER):continue
            d=r['dim'];d.kind=kind;d.manual=True;d.reason='Тип указан вручную'
            r['proposal'],r['reason']=S.propose(d,r['state'],self.sources,self.grade,self.mode)
            if r['proposal']:self.checked.add(r['ref'])
            else:self.checked.discard(r['ref'])
        self.refresh()

    def edit(self,event):
        if self.app.busy or self.data is None or self.table.identify_column(event.x)=='#1':return
        row=self.table.identify_row(event.y)
        if not row:return
        r=next(r for r in self.data['records'] if r['ref']==int(row))
        if S.has_existing(r['state']):
            messagebox.showinfo('Допуск уже задан','Этот размер сохраняется без изменений.',parent=self);return
        if r['dim'].kind not in S.KINDS or r['dim'].limit or r['state'].get('Rectangle') or '*' in r['dim'].raw_text:
            messagebox.showinfo('Специальный размер','Этот размер не предназначен для автоматической расстановки допуска.',parent=self);return
        w=U.dialog(self,'Допуск размера эскиза',540,350)
        kind=tk.StringVar(value=r['dim'].kind)
        hi=tk.StringVar(value=T.fmt_num(r['proposal']['hi']) if r['proposal'] else '')
        lo=tk.StringVar(value=T.fmt_num(r['proposal']['lo']) if r['proposal'] else '')
        ttk.Label(w,text=S.preview_text(r['dim'],None)).grid(row=0,column=0,columnspan=2,padx=12,pady=8)
        for i,title in enumerate(('Тип','Верхнее отклонение','Нижнее отклонение'),1):
            ttk.Label(w,text=title).grid(row=i,column=0,padx=12,pady=6,sticky='w')
        kinds=(K.KIND_OUTER,K.KIND_INNER) if r['dim'].kind in (K.KIND_OUTER,K.KIND_INNER) else (r['dim'].kind,)
        ttk.Combobox(w,textvariable=kind,values=kinds,state='readonly').grid(row=1,column=1,padx=12)
        ttk.Entry(w,textvariable=hi).grid(row=2,column=1,padx=12)
        ttk.Entry(w,textvariable=lo).grid(row=3,column=1,padx=12)
        ttk.Label(w,text='Углы — в градусах. Нулевое отклонение: 0.').grid(row=4,column=0,columnspan=2,padx=12,pady=6)
        def calculate():
            d=copy.copy(r['dim']);d.kind=kind.get();d.manual=True;d.reason='Тип указан вручную'
            proposal,reason=S.propose(d,r['state'],self.sources,self.grade,self.mode)
            if not proposal:messagebox.showinfo('Расчёт',reason,parent=w);return
            hi.set(T.fmt_num(proposal['hi']));lo.set(T.fmt_num(proposal['lo']))
        def save():
            try:
                upper,lower=float(hi.get().replace(',','.')),float(lo.get().replace(',','.'))
                if not all(math.isfinite(v) for v in (upper,lower)) or upper<=lower:raise ValueError('Верхнее отклонение должно быть больше нижнего.')
                r['dim'].kind=kind.get();r['proposal']=dict(hi=upper,lo=lower,kind=kind.get());r['reason']='Уточнено вручную'
                self.checked.add(r['ref']);w.destroy();self.grab_set();self.refresh()
            except ValueError as exc:messagebox.showerror('Допуск',str(exc),parent=w)
        ttk.Button(w,text='Рассчитать для типа',command=calculate).grid(row=5,column=0,padx=12,pady=12)
        ttk.Button(w,text='Применить',command=save,style='Accent.TButton').grid(row=5,column=1,padx=12,pady=12)
        w.protocol('WM_DELETE_WINDOW',lambda:(w.destroy(),self.grab_set()))

    def write(self):
        if self.app.busy or not self.checked:return
        data=copy.deepcopy(self.data);selected=set(self.checked)
        self.send.configure(state='disabled');self.sheet.configure(state='disabled')
        self.info.set('Проставляю допуски и проверяю каждый размер…')
        self.app.run(lambda:S.write(self.path,data,selected),self.done,'Проставляю отклонения и проверяю каждый размер…',self.failed)
        self.after(100,self.unlock)

    def failed(self,error):
        self.data=None;self.checked=set();self.send.configure(state='disabled')
        self.info.set('Операция остановлена. Перечитайте лист. Подробности доступны в журнале отладки.')

    def done(self,count):
        self.data=None;self.checked=set();self.send.configure(state='disabled')
        self.info.set('Допуски проставлены: %d. Проверьте выбранный лист в КОМПАСе и сохраните ТП (Ctrl+S).'%count)
        self.app.status.set('Допуски на эскизе проставлены. Сохраните ТП после проверки.')
