// Извлечение текста из PDF построчно, с координатами X каждого фрагмента.
// pdf.js передаётся параметром, чтобы один и тот же код работал и в Node (тесты), и в приложении.

export interface TextItem { x: number; s: string }
export interface Line { page: number; y: number; items: TextItem[]; text: string }

// минимальный интерфейс pdf.js, который нам нужен
export interface PdfJsLike {
  getDocument(src: { data: Uint8Array; useSystemFonts?: boolean; isEvalSupported?: boolean }): { promise: Promise<any> };
}

export async function extractLines(pdfjs: PdfJsLike, data: Uint8Array): Promise<Line[]> {
  const doc = await pdfjs.getDocument({ data, useSystemFonts: true, isEvalSupported: false }).promise;
  const out: Line[] = [];
  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const tc = await page.getTextContent();
    const rows: { y: number; items: TextItem[] }[] = [];
    for (const it of tc.items as any[]) {
      const s: string = (it.str ?? '').replace(/ | /g, ' ');
      if (!s.trim()) continue;
      const x = it.transform[4];
      const y = it.transform[5];
      let row = rows.find(r => Math.abs(r.y - y) <= 2.5);
      if (!row) { row = { y, items: [] }; rows.push(row); }
      row.items.push({ x, s: s.trim() });
    }
    rows.sort((a, b) => b.y - a.y);
    for (const r of rows) {
      r.items.sort((a, b) => a.x - b.x);
      // склеиваем фрагменты, стоящие вплотную (pdf.js иногда режет слова)
      const merged: TextItem[] = [];
      for (const it of r.items) merged.push(it);
      out.push({ page: p, y: r.y, items: merged, text: merged.map(i => i.s).join(' ') });
    }
    page.cleanup?.();
  }
  await doc.destroy?.();
  return out;
}
