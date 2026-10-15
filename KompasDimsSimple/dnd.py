"""Перетаскивание файлов из Проводника в окно Tk (Windows, без сторонних библиотек).

Окну разрешается приём файлов (DragAcceptFiles), а его оконная процедура
подменяется: WM_DROPFILES перехватывается, остальные сообщения уходят в
прежнюю процедуру Tk. Проводник доставляет WM_DROPFILES ближайшему предку
под курсором, который принимает файлы, поэтому достаточно подключить
верхнее окно — перетаскивать можно в любое место окна.
На других ОС функция ничего не делает (остаётся кнопка «Добавить файлы…»).
"""
import sys

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4


def enable(widget, callback):
    """callback(list[str]) вызывается в потоке Tk после отпускания файлов. True — если подключено."""
    if sys.platform != 'win32':
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
        user32.CallWindowProcW.restype = LRESULT
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        shell32.DragQueryFileW.restype = wt.UINT
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wt.UINT, ctypes.c_wchar_p, wt.UINT]
        shell32.DragFinish.argtypes = [ctypes.c_void_p]
        shell32.DragAcceptFiles.argtypes = [wt.HWND, wt.BOOL]

        widget.update_idletasks()
        hwnd = widget.winfo_id()
        state = {}

        def proc(h, msg, wp, lp):
            if msg == WM_DROPFILES:
                files = []
                try:
                    count = shell32.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                    for i in range(count):
                        size = shell32.DragQueryFileW(wp, i, None, 0) + 1
                        buf = ctypes.create_unicode_buffer(size)
                        shell32.DragQueryFileW(wp, i, buf, size)
                        files.append(buf.value)
                finally:
                    shell32.DragFinish(wp)
                if files:
                    widget.after(0, callback, files)
                return 0
            return user32.CallWindowProcW(state['old'], h, msg, wp, lp)

        state['proc'] = WNDPROC(proc)
        shell32.DragAcceptFiles(hwnd, True)
        state['old'] = set_long(hwnd, GWLP_WNDPROC, ctypes.cast(state['proc'], ctypes.c_void_p))
        widget._dnd_state = state   # держим ссылку, иначе процедуру соберёт сборщик мусора
        return True
    except Exception:
        return False
