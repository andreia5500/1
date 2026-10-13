"""Small shared light theme and consistent window/table helpers."""
import tkinter as tk
from tkinter import ttk,font

BG='#F4F6F9'
PAPER='#FFFFFF'
TEXT='#202B3B'
MUTED='#637084'
LINE='#D9E1EC'
BLUE='#245BCB'


def theme(root):
    style=ttk.Style(root);style.theme_use('clam')
    for name in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont'):
        font.nametofont(name).configure(family='Segoe UI',size=10)
    root.configure(background=BG)
    root.option_add('*background',BG)
    root.option_add('*foreground',TEXT)
    root.option_add('*Listbox.background',PAPER)
    root.option_add('*Listbox.selectBackground','#DCE8FC')
    root.option_add('*Listbox.selectForeground',TEXT)
    root.option_add('*Listbox.highlightThickness',1)
    root.option_add('*Listbox.highlightBackground',LINE)
    root.option_add('*Listbox.relief','flat')
    root.option_add('*Text.background',PAPER)
    root.option_add('*Text.highlightThickness',1)
    root.option_add('*Text.highlightBackground',LINE)
    root.option_add('*Text.relief','flat')
    root.option_add('*TCombobox*Listbox.background',PAPER)
    style.configure('.',background=BG,foreground=TEXT,font=('Segoe UI',10))
    style.configure('TFrame',background=BG)
    style.configure('TLabel',background=BG,foreground=TEXT)
    style.configure('Title.TLabel',font=('Segoe UI',18,'bold'))
    style.configure('Heading.TLabel',font=('Segoe UI',11,'bold'))
    style.configure('Muted.TLabel',foreground=MUTED)
    style.configure('TLabelframe',bordercolor=LINE,relief='solid',borderwidth=1)
    style.configure('TLabelframe.Label',font=('Segoe UI',10,'bold'),foreground=TEXT)
    style.configure('TButton',padding=(12,7),background=PAPER,bordercolor=LINE,
                    lightcolor=PAPER,darkcolor=PAPER,relief='flat',focuscolor=BLUE)
    style.map('TButton',background=[('disabled','#EDF0F4'),('pressed','#DCE8FC'),('active','#EAF0FB')],
              foreground=[('disabled','#98A2B0')],bordercolor=[('focus',BLUE),('active','#AEC1E0')])
    style.configure('Accent.TButton',background=BLUE,foreground=PAPER,bordercolor=BLUE,
                    lightcolor=BLUE,darkcolor=BLUE,font=('Segoe UI',10,'bold'))
    style.map('Accent.TButton',background=[('disabled','#E3E8F0'),('pressed','#18449E'),('active','#316CDF')],
              foreground=[('disabled','#8A97AB'),('!disabled',PAPER)],bordercolor=[('!disabled',BLUE)])
    style.configure('TEntry',fieldbackground=PAPER,padding=5,bordercolor=LINE)
    style.configure('TCombobox',fieldbackground=PAPER,background=PAPER,padding=5,bordercolor=LINE,
                    arrowcolor=MUTED,arrowsize=14)
    style.map('TCombobox',fieldbackground=[('readonly',PAPER),('disabled','#EDF0F4')],
              foreground=[('disabled','#98A2B0'),('readonly',TEXT)],selectbackground=[('readonly',PAPER)],selectforeground=[('readonly',TEXT)])
    style.configure('Treeview',background=PAPER,fieldbackground=PAPER,foreground=TEXT,
                    rowheight=max(29,font.nametofont('TkDefaultFont').metrics('linespace')+10),
                    bordercolor=LINE,borderwidth=1,font=('Segoe UI',10))
    style.configure('Treeview.Heading',background='#EAF0F7',foreground=TEXT,
                    font=('Segoe UI',10,'bold'),padding=(8,9),relief='flat')
    style.map('Treeview',background=[('selected','#DCE8FC')],foreground=[('selected','#153C7A')])
    style.map('Treeview.Heading',background=[('active','#DDE7F5')])
    style.configure('TScrollbar',background='#CBD5E2',troughcolor=BG,arrowcolor=MUTED,
                    bordercolor=BG,lightcolor=BG,darkcolor=BG,arrowsize=13)
    style.configure('TProgressbar',background=BLUE,troughcolor='#E6ECF4',bordercolor=BG)
    return style


def window(win,title,width,height,min_width=850,min_height=550):
    win.title(title);win.configure(background=BG)
    sw,sh=win.winfo_screenwidth(),win.winfo_screenheight()
    width=min(width,sw-60);height=min(height,sh-100)
    win.minsize(min(min_width,width),min(min_height,height))
    win.geometry('%dx%d+%d+%d'%(width,height,max(0,(sw-width)//2),max(0,(sh-height)//2-20)))


def header(parent,title,subtitle=None):
    frame=ttk.Frame(parent,padding=(16,12,16,8));frame.pack(fill='x')
    row=ttk.Frame(frame);row.pack(fill='x')
    ttk.Label(row,text=title,style='Title.TLabel').pack(side='left')
    if subtitle:
        label=ttk.Label(frame,text=subtitle,style='Muted.TLabel',wraplength=900)
        label.pack(anchor='w',pady=(4,0))
        frame.bind('<Configure>',lambda e:label.configure(wraplength=max(300,e.width-32)))
    return row


def dialog(parent,title,width=520,height=330):
    win=tk.Toplevel(parent);had_grab=parent.grab_current()==parent
    window(win,title,width,height,min_width=width,min_height=height)
    win.transient(parent);win.grab_set();win.resizable(False,False)
    def close():
        win.destroy()
        if had_grab and parent.winfo_exists():parent.grab_set()
    win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:close())
    win._close=close
    def fit():
        if win.winfo_exists():
            window(win,title,max(width,win.winfo_reqwidth()+20),max(height,win.winfo_reqheight()+20),width,height)
    win.after_idle(fit)
    return win


def table_scroll(table):
    parent=table.master;parent.columnconfigure(0,weight=1);parent.rowconfigure(0,weight=1)
    vertical=ttk.Scrollbar(parent,orient='vertical',command=table.yview)
    horizontal=ttk.Scrollbar(parent,orient='horizontal',command=table.xview)
    table.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
    table.grid(row=0,column=0,sticky='nsew');vertical.grid(row=0,column=1,sticky='ns')
    horizontal.grid(row=1,column=0,sticky='ew')
    table.tag_configure('stripe',background='#F7F9FC')


def journal_button(parent,owner):
    import debug_log as J
    button=ttk.Button(parent,text='Журнал отладки',command=lambda:J.show_window(owner))
    button._allow_busy=True
    return button


def busy(root,yes):
    if yes:
        saved=[]
        def visit(widget):
            if getattr(widget,'_is_debug_window',False):return
            if not getattr(widget,'_allow_busy',False) and widget.winfo_class() in ('TButton','TCombobox','TCheckbutton','Listbox'):
                saved.append((widget,widget.cget('state')));widget.configure(state='disabled')
            for child in widget.winfo_children():visit(child)
        visit(root);root._busy_widgets=saved
    else:
        for widget,state in getattr(root,'_busy_widgets',[]):
            if widget.winfo_exists():widget.configure(state=state)
        root._busy_widgets=[]
