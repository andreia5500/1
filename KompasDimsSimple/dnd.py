"""Перетаскивание файлов из Проводника в окно Tk (Windows, без сторонних библиотек).

Окну разрешается приём файлов (DragAcceptFiles), а его оконная процедура
подменяется: WM_DROPFILES перехватывается, остальные сообщения уходят в
прежнюю процедуру Tk.

ВАЖНО (2.1.1): внутри оконной процедуры нельзя вызывать НИЧЕГО из tkinter
(даже after()). Процедура вызывается из глубины цикла событий Tk, когда
tkinter отпустил интерпретатор; вызов Tcl оттуда портит сохранённое
состояние потока tkinter, и Python падает с «Fatal Python error:
PyEval_RestoreThread … GIL is released». Поэтому процедура только
складывает пути в очередь, а забирает их таймер Tk (poll) — уже в обычном
контексте tkinter.

Отключить перетаскивание: создать пустой файл
%LOCALAPPDATA%\\KompasDimsSimple\\no_dnd
"""
import os
import sys
from pathlib import Path

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4
POLL_MS = 150
_KEEP = []   # процедуры и состояния живут до конца программы (иначе их соберёт сборщик мусора)


def disabled():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'KompasDimsSimple'
    return (base / 'no_dnd').exists()


def enable(widget, callback):
    """callback(list[str]) вызывается таймером Tk после отпускания файлов. True — если подключено."""
    if sys.platform != 'win32' or disabled():
        return False
    try:
        import ctypes
        from ctypes import wintypes as wt
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
        set_long = getattr(user32, 'SetWindowLongPtrW', None) or user32.SetWindowLongW
        set_long.restype = ctypes.c_void_p
        set_long.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_void_p]
        call_proc = user32.CallWindowProcW
        call_proc.restype = LRESULT
        call_proc.argtypes = [ctypes.c_void_p, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        query = shell32.DragQueryFileW
        query.restype = wt.UINT
        query.argtypes = [ctypes.c_void_p, wt.UINT, ctypes.c_wchar_p, wt.UINT]
        finish = shell32.DragFinish
        finish.argtypes = [ctypes.c_void_p]
        shell32.DragAcceptFiles.argtypes = [wt.HWND, wt.BOOL]

        widget.update_idletasks()
        hwnd = widget.winfo_id()
        state = dict(queue=[], old=None)

        def proc(h, msg, wp, lp):
            # Только чистый Python и WinAPI — никаких вызовов tkinter!
            if msg == WM_DROPFILES:
                files = []
                try:
                    count = query(wp, 0xFFFFFFFF, None, 0)
                    for i in range(count):
                        size = query(wp, i, None, 0) + 1
                        buf = ctypes.create_unicode_buffer(size)
                        query(wp, i, buf, size)
                        files.append(buf.value)
                finally:
                    finish(wp)
                if files:
                    state['queue'].append(files)
                return 0
            return call_proc(state['old'], h, msg, wp, lp)

        state['proc'] = WNDPROC(proc)
        _KEEP.append(state)
        shell32.DragAcceptFiles(hwnd, True)
        state['old'] = set_long(hwnd, GWLP_WNDPROC, ctypes.cast(state['proc'], ctypes.c_void_p))

        def poll():
            try:
                if not widget.winfo_exists():
                    return
            except Exception:
                return
            while state['queue']:
                files = state['queue'].pop(0)
                try:
                    callback(files)
                except Exception as exc:   # ошибка обработки не должна остановить таймер
                    try:
                        import debug_log as J
                        J.failure('Перетаскивание файлов', exc, files=files)
                    except Exception:
                        pass
            widget.after(POLL_MS, poll)
        widget.after(POLL_MS, poll)
        return True
    except Exception:
        return False
