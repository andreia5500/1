import copy
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import sheet_names as N
import tooling as V
import debug_log as J
import ui as U


class ToolingWindow(tk.Toplevel):
    def __init__(self,app,path,sheets):
        super().__init__(app);self.app,self.path,self.sheets=app,path,sheets
        self.data=None;self.entries=[];self.checked=set();self.planned=None
        U.window(self,'Ведомость оснастки · МК ВО',1240,850,960,680);self.transient(app);self.grab_set()
        self.protocol('WM_DELETE_WINDOW',self.close)
        U.header(self,'Ведомость оснастки',path)
        # Reserve the action/status area before the resizable middle panes.
        bar=ttk.Frame(self);bar.pack(side='bottom',fill='x',padx=16,pady=(8,12))
        self.send=ttk.Button(bar,text='Записать в МК ВО',command=self.write,state='disabled',style='Accent.TButton');self.send.pack(side='right')
        ttk.Button(bar,text='Закрыть',command=self.close).pack(side='right',padx=10)
        U.journal_button(bar,self).pack(side='left')
        self.check_button=ttk.Button(bar,text='Проверить листы ТП',command=self.diagnose,state='disabled');self.check_button.pack(side='left',padx=8)
        self.status=tk.StringVar(value='Выберите листы ведомости справа. Затем нажмите «Собрать со всех листов».')
        status=ttk.Label(self,textvariable=self.status,wraplength=1180,style='Muted.TLabel')
        status.pack(side='bottom',fill='x',padx=16,pady=(6,0))
        self.bind('<Configure>',lambda e:status.configure(wraplength=max(300,self.winfo_width()-32)) if e.widget==self else None)
        selectors=ttk.Frame(self);selectors.pack(fill='x',padx=12,pady=(4,0))
        self.sources=self.listbox(selectors,'1. Источники · МК, ОК ТК, КЭ ЧПУ',sheets,'sources')
        self.targets=self.listbox(selectors,'2. Листы ведомости · МК ВО',sheets,'targets')
        bar=ttk.Frame(self);bar.pack(fill='x',padx=16,pady=10)
        self.collect_all=ttk.Button(bar,text='Собрать со всех листов',command=lambda:self.load(True),style='Accent.TButton',state='disabled');self.collect_all.pack(side='left')
        self.collect_selected=ttk.Button(bar,text='Собрать выбранные',command=self.load,state='disabled');self.collect_selected.pack(side='left',padx=8)
        ttk.Label(bar,text='Несколько листов — Ctrl + щелчок',style='Muted.TLabel').pack(side='right')
        panes=ttk.Panedwindow(self,orient='vertical');panes.pack(fill='both',expand=True,padx=16)
        list_panel=ttk.Frame(panes);panes.add(list_panel,weight=3)
        bar=ttk.Frame(list_panel);bar.pack(fill='x',pady=(4,8))
        ttk.Label(bar,text='3. Инструмент для записи',style='Heading.TLabel').pack(side='left')
        self.manual_button=ttk.Button(bar,text='Добавить вручную',command=self.add,state='disabled');self.manual_button.pack(side='right')
        self.unmark_button=ttk.Button(bar,text='Снять отметки',command=lambda:self.mark(False),state='disabled');self.unmark_button.pack(side='right',padx=8)
        self.mark_button=ttk.Button(bar,text='Отметить всё',command=lambda:self.mark(True),state='disabled');self.mark_button.pack(side='right')
        ttk.Label(list_panel,text='Двойной щелчок — изменить группу или наименование. Одинаковые позиции объединяются.',style='Muted.TLabel').pack(anchor='w',pady=(0,6))
        frame=ttk.Frame(list_panel);frame.pack(fill='both',expand=True)
        self.table=ttk.Treeview(frame,columns=('use','group','text','source'),show='headings',height=8)
        for c,title,w in [('use','✓',30),('group','Группа',145),('text','Инструмент / меритель',690),('source','Листы',90)]:
            self.table.heading(c,text=title);self.table.column(c,width=w,stretch=c=='text',anchor='center' if c in ('use','source') else 'w')
        U.table_scroll(self.table)
        self.table.bind('<Button-1>',self.toggle);self.table.bind('<Double-1>',self.edit)
        preview_panel=ttk.Frame(panes);panes.add(preview_panel,weight=1)
        ttk.Label(preview_panel,text='Предварительный просмотр',style='Heading.TLabel').pack(anchor='w',pady=(10,4))
        ttk.Label(preview_panel,text='Содержимое выбранных листов ведомости будет заменено. Проверьте план перед записью.',style='Muted.TLabel').pack(anchor='w',pady=(0,6))
        frame=ttk.Frame(preview_panel);frame.pack(fill='both',expand=True)
        self.preview=tk.Text(frame,height=6,wrap='word',state='disabled',font=('Segoe UI',10),padx=10,pady=8)
        scroll=ttk.Scrollbar(frame,command=self.preview.yview);self.preview.configure(yscrollcommand=scroll.set)
        self.preview.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.targets.focus_set()

    def listbox(self,parent,title,sheets,role):
        box=ttk.Frame(parent);box.pack(side='left',fill='both',expand=True,padx=4)
        ttk.Label(box,text=title,style='Heading.TLabel').pack(anchor='w',pady=(0,6))
        lb=tk.Listbox(box,selectmode='extended',exportselection=False,height=6)
        lb._role=role;self.fill_list(lb,sheets)
        lb.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(box,command=lb.yview);scroll.pack(side='right',fill='y');lb.configure(yscrollcommand=scroll.set)
        lb.bind('<<ListboxSelect>>',self.invalidate)
        return lb

    def fill_list(self,lb,sheets):
        allowed=set(V.source_indices(sheets))
        lb._sheets=[s for s in sheets if s[0] in allowed] if lb._role=='sources' else [s for s in sheets if s[2].startswith('МК ВО')]
        lb.delete(0,'end')
        for sheet in lb._sheets:lb.insert('end',N.label(sheet))

    def invalidate(self,event=None):
        self.data=None
        ready=bool(self.targets.curselection())
        if hasattr(self,'collect_all'):
            self.collect_all.configure(state='normal' if ready else 'disabled')
            self.collect_selected.configure(state='normal' if ready and self.sources.curselection() else 'disabled')
            self.check_button.configure(state='normal' if ready else 'disabled')
        if hasattr(self,'preview'):
            self.entries=[];self.checked=set();self.refresh()
        if hasattr(self,'send'):self.send.configure(state='disabled')
        if hasattr(self,'status'):self.status.set('Листы выбраны. Нажмите «Собрать со всех листов» или «Собрать выбранные».' if ready else 'Выберите справа листы МК ВО, в которые нужно записать инструмент.')

    def close(self):
        if not self.app.busy:self.destroy()

    def load(self,all_sources=False):
        if self.app.busy:return
        src=None if all_sources else [self.sources._sheets[i][0] for i in self.sources.curselection()]
        dst=[self.targets._sheets[i][0] for i in self.targets.curselection()]
        self.data=None;self.entries=[];self.checked=set();self.refresh()
        self.status.set('Собираю инструмент и читаю оформление ведомости…')
        self.sources.configure(state='disabled');self.targets.configure(state='disabled')
        self.app.run(lambda:V.read(self.path,src,dst),self.loaded,'Собираю инструмент и оформление ведомости…',self.failed)
        self.after(100,self.unlock)

    def unlock(self):
        if not self.winfo_exists():return
        if self.app.busy:self.after(100,self.unlock)
        else:
            self.sources.configure(state='normal');self.targets.configure(state='normal')
            ready=bool(self.targets.curselection())
            self.collect_all.configure(state='normal' if ready else 'disabled')
            self.collect_selected.configure(state='normal' if ready and self.sources.curselection() else 'disabled')
            self.check_button.configure(state='normal' if ready else 'disabled')
            for button in (self.manual_button,self.unmark_button,self.mark_button):button.configure(state='normal' if self.data else 'disabled')

    def failed(self,error):
        self.data=None;self.planned=None;self.send.configure(state='disabled')
        self.status.set('Операция остановлена. Подробности в журнале; перед записью соберите инструмент заново.')

    def loaded(self,data):
        if 'descriptions' in data:
            self.sheets=data['descriptions']
            for lb in (self.sources,self.targets):
                lb.configure(state='normal');self.fill_list(lb,self.sheets)
            for lb,records in ((self.sources,data['sources']),(self.targets,data['pages'])):
                selected={r['index'] for r in records}
                for pos,sheet in enumerate(lb._sheets):
                    if sheet[0] in selected:lb.selection_set(pos)
        self.data=data;self.entries=data['entries'];self.checked=set(range(len(self.entries)));self.refresh()
        if data['warnings']:messagebox.showwarning('Проверьте источники','\n'.join(data['warnings']),parent=self)

    def selected(self):return [copy.deepcopy(e) for i,e in enumerate(self.entries) if i in self.checked]

    def refresh(self):
        self.table.delete(*self.table.get_children());self.send.configure(state='disabled');self.planned=None
        for button in (self.manual_button,self.unmark_button,self.mark_button):button.configure(state='normal' if self.data else 'disabled')
        for i,e in enumerate(self.entries):self.table.insert('','end',iid=str(i),tags=('stripe',) if i%2 else (),values=('✓' if i in self.checked else '',e['group'],V.X.display(e['text']),', '.join(map(str,e['source']))))
        result=''
        if self.data:
            try:
                self.planned=V.plan(self.data,self.selected())
                for page,rows in zip(self.data['pages'],self.planned):
                    result+='Лист %d · МК ВО — %d/%d строк\n'%(page['index']+1,len(rows),page['capacity'])
                    result+='\n'.join(('  ' if r['heading'] else '')+V.X.display(r['text']) for r in rows)+'\n\n'
                self.send.configure(state='normal');self.status.set('Найдено: %d. Выбрано: %d. Сохранение ТП вручную после проверки.'%(len(self.entries),len(self.checked)))
            except ValueError as exc:
                self.status.set(str(exc));result=str(exc)
                J.failure('Предварительный просмотр МК ВО остановлен',exc,path=self.path)
        self.preview.configure(state='normal');self.preview.delete('1.0','end');self.preview.insert('1.0',result);self.preview.configure(state='disabled')

    def mark(self,yes):
        if self.app.busy or self.data is None:return
        self.checked=set(range(len(self.entries))) if yes else set();self.refresh()

    def toggle(self,event):
        if self.app.busy or self.data is None or self.table.identify_column(event.x)!='#1':return
        row=self.table.identify_row(event.y)
        if row:self.checked.symmetric_difference_update({int(row)});self.refresh()

    def edit(self,event=None,index=None):
        if self.app.busy or self.data is None:return
        if event:
            row=self.table.identify_row(event.y)
            if not row or self.table.identify_column(event.x)=='#1':return
            index=int(row)
        e=self.entries[index] if index is not None else dict(text='',group=V.GROUPS[0],source=[])
        w=U.dialog(self,'Инструмент',860,265)
        group=tk.StringVar(value=e['group']);text=tk.StringVar(value=e['text'])
        ttk.Label(w,text='Группа',style='Heading.TLabel').pack(anchor='w',padx=16,pady=(16,4))
        ttk.Combobox(w,values=V.GROUPS,textvariable=group,state='readonly',width=35).pack(anchor='w',padx=16)
        ttk.Label(w,text='Наименование',style='Heading.TLabel').pack(anchor='w',padx=16,pady=(12,4))
        entry=ttk.Entry(w,textvariable=text);entry.pack(fill='x',padx=16);entry.focus_set()
        def save():
            if not text.get().strip():return
            e.update(text=text.get().strip(),group=group.get())
            if index is None:self.entries.append(e);self.checked.add(len(self.entries)-1)
            w.destroy();self.grab_set();self.refresh()
        bar=ttk.Frame(w);bar.pack(fill='x',padx=16,pady=16)
        ttk.Button(bar,text='Применить',command=save,style='Accent.TButton').pack(side='right')
        ttk.Button(bar,text='Отмена',command=w._close).pack(side='right',padx=8)
        w.protocol('WM_DELETE_WINDOW',lambda:(w.destroy(),self.grab_set()))

    def add(self):self.edit()

    def write(self):
        if self.app.busy or self.data is None or self.planned is None:return
        data=copy.deepcopy(self.data);entries=self.selected();self.send.configure(state='disabled')
        self.sources.configure(state='disabled');self.targets.configure(state='disabled')
        self.status.set('Записываю ведомость, читаю результат и обновляю окно ТП…')
        self.app.run(lambda:V.write(self.path,data,entries),self.done,'Заполняю выбранные листы ведомости…',self.failed)
        self.after(100,self.unlock)

    def done(self,count):
        self.data=None;self.send.configure(state='disabled')
        self.status.set('Записано и проверено обратным чтением: %d позиций. Окно ТП обновлено. Проверьте вид листов и сохраните ТП (Ctrl+S).'%count)

    def diagnose(self):
        if self.app.busy:return
        indices=[self.targets._sheets[i][0] for i in self.targets.curselection()]
        self.sources.configure(state='disabled');self.targets.configure(state='disabled')
        def done(result):
            self.status.set('Проверка листов сохранена в журнале.')
            messagebox.showinfo('Проверка ТП',result,parent=self)
        self.status.set('Проверяю графы выбранных листов ТП…')
        self.app.run(lambda:V.diagnose(self.path,indices),done,'Читаю все графы выбранных листов через API5 и API7…',self.failed)
        self.after(100,self.unlock)
