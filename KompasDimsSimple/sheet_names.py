"""Read saved sheet captions from native CDW metadata, without changing the file."""
import re
import struct
import zipfile
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path

# 11/18/20/24 change meaning between the supplied libraries. Never guess
# a writable card from one of these numbers alone.
FALLBACK={1:'ТЛ',4:'КЭ ЧПУ',5:'КЭ ЧПУ — инструмент',
          19:'КЭ ЧПУ — эскиз',21:'МК — маршрутная карта',22:'МК — маршрутная карта (продолжение)'}


def saved(path):
    try:
        with zipfile.ZipFile(path) as z:
            sheets=ET.fromstring(z.read('MetaInfo').decode('utf-16')).findall('./sheets/sheet')
            expected=[(int(s.find('style').get('number')),s.find('style').get('absSource','')) for s in sheets]
            raw=z.read('Contents')
        candidates=[]
        pos=0
        while pos<len(raw)-2:
            i=raw.find(b'\x78',pos)
            if i<0:break
            pos=i+1
            try:
                dec=zlib.decompressobj();block=dec.decompress(raw[i:],16*1024*1024)
            except zlib.error:continue
            if not dec.eof:continue
            pos=len(raw)-len(dec.unused_data)
            names=[]
            for match in re.finditer(b'\x00\x7f\x0f',block):
                k=match.end()
                if k+4>len(block):continue
                n=struct.unpack_from('<I',block,k)[0]
                if not 1<=n<=200:continue
                try:name=block[k+4:k+4+2*n].decode('utf-16le').strip()
                except UnicodeError:continue
                end=k+4+2*n
                if end+8>len(block):continue
                native_style=struct.unpack_from('<d',block,end)[0]
                if not native_style.is_integer() or not 0<=native_style<=100000:continue
                if name and all(c.isprintable() for c in name):names.append((name,int(native_style)))
            if len(names)==len(expected):candidates.append(names)
        if len(candidates)!=1:return []
        if [s for _,s in candidates[0]]!=[s for s,_ in expected]:return []
        return [dict(style=s,library=l,name=n) for (s,l),(n,_) in zip(expected,candidates[0])]
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,ET.ParseError):return []


def short(name):
    n=name.upper().replace('_',' ')
    if 'МК ВО' in n:return 'МК ВО' + (' — продолжение' if 'Л2' in n or 'ПРОДОЛЖЕНИЕ' in n else '')
    if 'ОК' in n and 'ТК' in n:return 'ОК ТК — карта контроля'
    if n.startswith('МК'):return 'МК — маршрутная карта'+(' (продолжение)' if 'Ф1Б' in n or 'ПРОДОЛЖЕНИЕ' in n else '')
    if n.startswith('ВТД'):return 'ВТД'
    if n.startswith('ТЛ'):return 'ТЛ'
    if 'КЭ' in n:
        return 'КЭ ЧПУ — инструмент' if 'ИНСТР' in n or ' КИ' in n else ('КЭ ЧПУ — эскиз' if 'ЭСКИЗ' in n else 'КЭ ЧПУ' if 'ЧПУ' in n else 'КЭ')
    if n.startswith('ОК'):return 'ОК'
    return name


def library_key(path):
    return str(path).replace('/','\\').rstrip('\\').casefold()


def content_name(sh):
    """Resolve filled cards by their actual fields when saved metadata is stale."""
    def lines(cid):
        try:
            t=sh.Stamp.Text(cid)
            return [str(t.TextLine(j).Str or '') for j in range(int(t.Count))]
        except Exception:return []
    rows=lines(2000)
    groups={'мерительная','режущая','токарная','слесарная','селсарная','шлифовальная','приспособления','прочая оснастка'}
    if any(s.strip().rstrip(':').casefold() in groups for s in rows):return 'МК ВО'
    if any(re.match(r'^\s*[АБТABT](?:\s|\x01)+',s) for s in rows):return 'МК — маршрутная карта'
    return None


def describe(doc,path,at):
    meta=saved(path);result=[]
    by_signature={}
    for row in meta:
        by_signature.setdefault((row['style'],library_key(row['library'])),set()).add(short(row['name']))
    for i in range(doc.LayoutSheets.Count):
        sh=at(doc.LayoutSheets,i);style=int(sh.LayoutStyleNumber)
        sig=(style,library_key(sh.LayoutLibraryFileName))
        choices=by_signature.get(sig,set())
        valid=(i<len(meta) and (meta[i]['style'],library_key(meta[i]['library']))==sig)
        if valid:name=short(meta[i]['name'])
        elif len(choices)==1:name=next(iter(choices))
        else:name=content_name(sh) or FALLBACK.get(style,'Название не определено')
        result.append((i,style,name))
    return result


def label(sheet):
    return 'Лист %d · %s'%(sheet[0]+1,sheet[2] if len(sheet)>2 else FALLBACK.get(sheet[1],'Название не определено'))
