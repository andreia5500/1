import tkinter as tk
from tkinter import ttk,messagebox
import numbering as P
import ui as U


class NumberingWindow(tk.Toplevel):
    def __init__(self,app,path,data):
        super().__init__(app);self.app,self.path,self.data=app,path,data
        U.window(self,'Нумерация листов',1000,700,850,500);self.transient(app);self.grab_set()
        U.header(self,'Номер листа в документе',path,icon='pages')
        bar=ttk.Frame(self);bar.pack(side='bottom',fill='x',padx=16,pady=(8,12))
        self.send=ttk.Button(bar,text='Записать номера',command=self.write,style='Accent.TButton');self.send.pack(side='right')
        ttk.Button(bar,text='Закрыть',command=self.destroy).pack(side='right',padx=10)
        U.journal_button(bar,self).pack(side='left')
        self.status=tk.StringVar()
        ttk.Label(self,textvariable=self.status,style='Muted.TLabel',wraplength=950).pack(side='bottom',fill='x',padx=16)
        ttk.Label(self,text='Номер ставится в ячейку сверху справа на листах-продолжениях; на главном листе его выводит оформление. '
                  'Проверьте разбиение на документы перед записью.',style='Muted.TLabel',wraplength=950).pack(fill='x',padx=16,pady=(0,8))
        frame=ttk.Frame(self);frame.pack(fill='both',expand=True,padx=16)
        self.table=ttk.Treeview(frame,columns=('sheet','name','doc','page','old','action'),show='headings')
        for c,title,w in [('sheet','Лист ТП',70),('name','Лист',290),('doc','Документ',80),('page','Номер',70),('old','Сейчас',70),('action','Действие',360)]:
            self.table.heading(c,text=title);self.table.column(c,width=w,stretch=c in ('name','action'),anchor='w' if c in ('name','action') else 'center')
        U.table_scroll(self.table)
        self.table.tag_configure('write',foreground='#0a5f68')
        for r in data['rows']:
            old=r['old']['text'].strip() if r.get('old') else ''
            self.table.insert('','end',values=(r['index']+1,r['name'],r['doc'],r['page'],old,r['action']),tags=('write',) if r['action']=='записать' else ())
        todo=sum(r['action']=='записать' for r in data['rows'])
        self.status.set('К записи: %d лист(ов). ТП не сохраняется автоматически.'%todo)
        if not todo:self.send.configure(state='disabled')

    def write(self):
        if self.app.busy:return
        self.send.configure(state='disabled')
        def done(result):
            count,note=result
            self.status.set('Записано и проверено: %d номер(ов). Проверьте листы и сохраните ТП (Ctrl+S).'%count)
            if note:messagebox.showwarning('Проверьте листы',note,parent=self)
        def failed(error):
            self.status.set('Нумерация остановлена. Подробности в журнале; перечитайте ТП.')
        self.app.run(lambda:P.write(self.path,self.data),done,'Записываю номера листов…',failed)
