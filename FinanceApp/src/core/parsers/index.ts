import { extractLines, type PdfJsLike } from '../pdf';
import type { ParsedStatement } from '../types';
import { isSber, parseSber } from './sber';
import { isTbank, parseTbank } from './tbank';

export class UnsupportedStatementError extends Error {}

export async function parseStatementPdf(pdfjs: PdfJsLike, data: Uint8Array): Promise<ParsedStatement> {
  const lines = await extractLines(pdfjs, data);
  if (!lines.length) throw new UnsupportedStatementError('В PDF нет текста (возможно, это скан). Нужна выписка, скачанная из приложения банка.');
  if (isSber(lines)) return parseSber(lines);
  if (isTbank(lines)) return parseTbank(lines);
  throw new UnsupportedStatementError('Этот формат выписки пока не поддерживается. Сейчас умею: СберБанк (дебетовая и кредитная карта) и Т-Банк (выписка по договору).');
}
