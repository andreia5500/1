// Проверка на настоящих выписках: каждая PDF из папки FIN_PDF_DIR должна разобраться
// и сойтись с итогами в своей шапке. Сами выписки в репозиторий не добавляются.
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import { parseStatementPdf } from '../src/core/parsers';

const DIR = process.env.FIN_PDF_DIR ?? '';
const files = DIR && fs.existsSync(DIR) ? fs.readdirSync(DIR).filter(f => f.toLowerCase().endsWith('.pdf')) : [];

describe.runIf(files.length > 0)('реальные выписки', () => {
  for (const f of files) {
    it(f, async () => {
      const r = await parseStatementPdf(pdfjs as any, new Uint8Array(fs.readFileSync(path.join(DIR, f))));
      expect(r.txs.length).toBeGreaterThan(0);
      expect(r.meta.verified, `поступления ${r.meta.parsedIn}/${r.meta.totalIn}, списания ${r.meta.parsedOut}/${r.meta.totalOut}`).toBe(true);
      expect(new Set(r.txs.map(t => t.id)).size).toBe(r.txs.length);
    });
  }
});
