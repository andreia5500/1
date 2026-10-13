"""Append-only diagnostics shared by the UI and COM workers (no COM imports)."""
import json
import os
import platform
import sys
import threading
import time
import traceback
import uuid
import zipfile
from collections import deque
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

VERSION='1.4.7'
_lock=threading.RLock()
_local=threading.local()
_memory=deque(maxlen=5000)
_io_error=None


def folder():
    path=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'KompasDimsSimple'
    path.mkdir(parents=True,exist_ok=True)
    return path


def log_path():
    return folder()/('debug_'+datetime.now().strftime('%Y%m%d')+'.log')


def operation_id():return getattr(_local,'operation','—')


def new_id():return datetime.now().strftime('%H%M%S_')+uuid.uuid4().hex[:8]


def event(event_name,level='INFO',**details):
    global _io_error
    record=dict(time=datetime.now().astimezone().isoformat(timespec='milliseconds'),
                level=level,operation=operation_id(),version=VERSION,
                thread=threading.current_thread().name,event=event_name,details=details)
    encoded=json.dumps(record,ensure_ascii=False,default=repr)
    with _lock:
        _memory.append(record)
        try:
            with log_path().open('a',encoding='utf-8') as stream:stream.write(encoded+'\n')
            _io_error=None
        except OSError as exc:_io_error=str(exc)
    return record


def failure(message,exc,level='ERROR',**details):
    details.update(exception=type(exc).__name__,message=str(exc),args=exc.args,
                   traceback=''.join(traceback.format_exception(type(exc),exc,exc.__traceback__)))
    for name in ('hresult','excepinfo','argerror','strerror'):
        if hasattr(exc,name):details[name]=getattr(exc,name)
    if hasattr(exc,'hresult'):details['hresult_hex']='0x%08X'%(exc.hresult&0xffffffff)
    chain=[];current=exc.__cause__ or exc.__context__;seen={id(exc)}
    while current is not None and id(current) not in seen:
        seen.add(id(current));cause=dict(exception=type(current).__name__,message=str(current),args=current.args)
        for name in ('hresult','excepinfo','argerror','strerror'):
            if hasattr(current,name):cause[name]=getattr(current,name)
        chain.append(cause);current=current.__cause__ or current.__context__
    if chain:details['causes']=chain
    return event(message,level,**details)


@contextmanager
def operation(label,op_id=None,**details):
    previous=operation_id();_local.operation=op_id or new_id();started=time.monotonic()
    event('Начало операции',label=label,**details)
    try:
        yield _local.operation
    except Exception as exc:
        failure('Операция завершилась ошибкой',exc,label=label,seconds=round(time.monotonic()-started,3))
        raise
    else:event('Операция завершена',label=label,seconds=round(time.monotonic()-started,3))
    finally:_local.operation=previous


def call(name,fn,*args,require_result=False,**context):
    event('Вызов '+name,**context)
    try:
        result=fn(*args)
        # API5 stamp methods return a flag/reference, never a void result.
        if require_result and (result is None or result==0):
            raise RuntimeError('%s не подтвердил выполнение: %r'%(name,result))
    except Exception as exc:
        failure('Ошибка '+name,exc,**context)
        raise
    event('Результат '+name,result=result if isinstance(result,(str,int,float,bool,type(None))) else repr(result),**context)
    return result


def require_storage():
    event('Проверка записи журнала')
    if _io_error:raise RuntimeError('Не удалось сохранить журнал отладки: '+_io_error)


def runtime():
    return dict(python=sys.version,platform=platform.platform(),executable=sys.executable,
                program=str(Path(__file__).resolve().parent),process=os.getpid())


def view_text():
    with _lock:
        try:
            with log_path().open('rb') as stream:
                stream.seek(0,2);size=stream.tell();stream.seek(max(0,size-2*1024*1024))
                if size>2*1024*1024:stream.readline()
                lines=stream.read().decode('utf-8',errors='replace').splitlines()[-2000:]
            records=[json.loads(s) for s in lines if s.strip()]
        except (OSError,ValueError):records=list(_memory)
        result=[]
        if _io_error:result.append('НЕ УДАЛОСЬ СОХРАНИТЬ ЖУРНАЛ: '+_io_error+'\n')
        for r in records:
            result.append('%s %s [%s] %s\n%s'%(r['time'],r['level'],r['operation'],r['event'],
                          json.dumps(r['details'],ensure_ascii=False,indent=2,default=repr)))
        return '\n\n'.join(result)


def export_bundle(path):
    require_storage()
    with _lock,zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
        for pattern in ('debug_*.log','*.json','error.log','reading_warnings.txt'):
            for file in sorted(folder().glob(pattern)):archive.write(file,file.name)


def show_window(parent):
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    from tkinter.scrolledtext import ScrolledText
    import ui as U
    window=tk.Toplevel(parent);window._is_debug_window=True
    U.window(window,'Журнал отладки · '+VERSION,1100,760,850,550);window.transient(parent)
    had_grab=parent.grab_current()==parent
    if had_grab:window.grab_set()
    U.header(window,'Журнал отладки','Последние записи за сегодня. Полная история и отчёты сохраняются автоматически.')
    ttk.Label(window,text=str(log_path()),wraplength=1040,style='Muted.TLabel').pack(anchor='w',padx=16)
    text=ScrolledText(window,wrap='none',font=('Consolas',10));text.pack(fill='both',expand=True,padx=10,pady=8)
    auto=tk.BooleanVar(value=True);last=[''];timer=[None]
    def refresh():
        value=view_text()
        if value!=last[0]:
            at_end=text.yview()[1]>=0.99
            text.configure(state='normal');text.delete('1.0','end');text.insert('1.0',value);text.configure(state='disabled')
            if at_end:text.see('end')
            last[0]=value
    def poll():
        if not window.winfo_exists():return
        if auto.get():refresh()
        timer[0]=window.after(1000,poll)
    def save():
        path=filedialog.asksaveasfilename(parent=window,title='Сохранить журнал и подробные отчёты',
            defaultextension='.zip',initialfile='KompasDimsSimple_debug_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip',filetypes=[('Архив журнала','*.zip')])
        if not path:return
        try:export_bundle(path)
        except Exception as exc:
            failure('Ошибка сохранения архива журнала',exc)
            messagebox.showerror('Журнал',str(exc),parent=window)
        else:messagebox.showinfo('Журнал','Сохранено: '+path,parent=window)
    def close():
        if timer[0] is not None:window.after_cancel(timer[0])
        window.destroy()
        if had_grab and parent.winfo_exists():parent.grab_set()
    bar=ttk.Frame(window);bar.pack(fill='x',padx=10,pady=8)
    ttk.Checkbutton(bar,text='Обновлять автоматически',variable=auto).pack(side='left')
    ttk.Button(bar,text='Сохранить журнал…',command=save,style='Accent.TButton').pack(side='left',padx=10)
    ttk.Button(bar,text='Закрыть',command=close).pack(side='right')
    window.protocol('WM_DELETE_WINDOW',close);refresh();timer[0]=window.after(1000,poll)
