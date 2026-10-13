API5_GUID = '{0422828C-F174-495E-AC5D-D31014DBBE87}'
_api5_cache = {}
class OctkError(Exception):
    pass

def _connect5():
    import pythoncom
    from win32com.client import Dispatch, gencache
    mod5 = gencache.EnsureModule(API5_GUID, 0, 1, 0)
    if mod5 is None:
        raise OctkError('Не удалось подключиться к API5 КОМПАСа (не собралось описание типов KOMPAS.Application.5).')
    try:
        raw = Dispatch('KOMPAS.Application.5')
        kompas5 = mod5.KompasObject(raw._oleobj_.QueryInterface(mod5.KompasObject.CLSID, pythoncom.IID_IDispatch))
        kompas5.Visible = True
    except Exception as e:
        raise OctkError('Не удалось подключиться к API5 КОМПАСа: %s' % e)
    return (mod5, kompas5)

def _text_item_param(kompas5):
    cached_const = _api5_cache.get('param_const')
    if cached_const is not None:
        try:
            par = kompas5.GetParamStruct(cached_const)
            if par is not None and hasattr(par, 's') and hasattr(par, 'type'):
                return par
        except Exception:
            pass
    for c in range(0, 300):
        try:
            par = kompas5.GetParamStruct(c)
        except Exception:
            continue
        if par is not None and hasattr(par, 's') and hasattr(par, 'type'):
            _api5_cache['param_const'] = c
            return par
    raise OctkError('Не удалось найти структуру параметра текста графы (аналог ksTextItemParam) среди GetParamStruct(0..299) в API5.')
