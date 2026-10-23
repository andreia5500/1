// Классификация операций: доход / расход / возврат / перевод между своими счетами + категория
import type { AppData, ClassifiedTx, RawTx, TxKind } from './types';
import { BANKS, TRANSFER_CATEGORY, detectBank } from './categories';
import { diffDays } from './util';

/** Ключ «продавца» для правил пользователя: без цифр, городов-префиксов не трогаем — они стабильны */
/** Читаемое имя получателя для экрана */
export function prettyName(desc: string): string {
  let d = desc;
  const mapp = d.match(/^MAPP_SBERBANK_ONL@IN_PAY\s*(?:Списание ДС по операции оплаты\s*)?(.*)$/i);
  if (mapp) d = mapp[1] ? 'Оплата ' + mapp[1] : 'Платёж в СберОнлайн';
  if (/^SBOL$/i.test(d)) d = 'Перевод через СберБанк Онлайн';
  d = d.replace(/^(MOSCOW|EKATERINBURG|SANKT-PETERBU\w*|g\. [\w-]+|Kosulino|Prokhladnyj|Verkhnyaya Py)\s+/i, '')
       .replace(/\s+(RUS|MOSCOW RUS)$/i, '')
       .replace(/^OOO\s+/i, '');
  return d.trim() || desc;
}

export function merchantKey(t: RawTx): string {
  return t.description
    .toLowerCase()
    .replace(/^(оплата услуг|оплата в|покупка в|оплата)\s+/, '')
    .replace(/\(сбп\)/g, ' ')
    .replace(/\+?\d[\d*]{3,}/g, ' ')     // номера карт, телефонов, счетов, касс
    .replace(/\b(rus|g\.)\b/g, ' ')
    .replace(/[«»"'().,]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

interface Base { kind: TxKind; category: string; transferNote?: string; needsReview?: boolean; transferLike?: boolean }

const EXPENSE_RULES: [RegExp, string][] = [
  [/взыскание|исполнительн|фссп/i, 'Взыскания и долги'],
  [/комиссия|плата за обслуживание|обслуживание карты|sms-информ|оповещени/i, 'Комиссии банка'],
  [/снятие наличных|выдача наличных|cash withdrawal|\batm\b/i, 'Наличные'],
  [/проценты по кредит|погашение процентов/i, 'Проценты по кредитам'],
  [/ozon|wildberries|вайлдберриз|\bwb\b|aliexpress|ym\*|yandex\s*market|яндекс маркет|megamarket|мегамаркет|lamoda|sbermegamarket/i, 'Маркетплейсы'],
  [/pitanie|shkol|школ|детск|kindergarten|детсад|образован/i, 'Дети и школа'],
  [/megafon|мегафон|\bmts\b|мтс|beeline|билайн|tele2|теле2|rostelecom|ростелеком|интернет|связи|motiv|мотив|dom\.ru|дом\.ру/i, 'Связь и интернет'],
  [/kion|\bivi\b|okko|kinopoisk|кинопоиск|yandex\s*plus|яндекс плюс|spotify|start\.ru|wink|premier|apple\.com|google\s*play|steam|\bvk\b.*(музык|combo)|vk combo/i, 'Подписки и развлечения'],
  [/gosuslugi|госуслуг|фнс|налог|штраф|гибдд|gibdd|пошлин/i, 'Госуслуги, налоги, штрафы'],
  [/жкх|ерц|энергосбыт|водоканал|газпром межрегионгаз|теплосет|капремонт|т плюс|эсплюс|квартплат|управляющ/i, 'ЖКХ'],
  [/gazprom.*(gpn|azs)|gpn|lukoil|лукойл|rosneft|роснефть|tatneft|татнефть|bashneft|\bazs\b|азс|shell|taxi|такси|yandex\s*go|metro|метро|транспорт|parking|парковк/i, 'Транспорт и АЗС'],
  [/apteka|аптек|pharm|farm|здрав|clinic|клиник|стоматолог|medic|медиц/i, 'Здоровье и аптеки'],
  [/pyaterochka|пят[её]рочк|magnit|магнит|monetka|монетка|perekrestok|перекр[её]сток|lenta|лента|auchan|ашан|dixy|дикси|krasnoe|красное|fixprice|fix price|ch6\d{3,}|чижик|chizhik|verny|верный|spar|kirovsk|кировск|elisey|елисей|vkusvill|вкусвилл|lavka|лавка/i, 'Продукты'],
  [/kfc|vkusno|вкусно|burger|бургер|mcdonald|coffee|кофе|cafe|кафе|restoran|ресторан|pizza|пицц|sushi|суши|delivery club|яндекс еда|eda\.yandex|додо|dodo/i, 'Кафе и доставка еды'],
  [/sportmaster|спортмастер|leroy|леруа|ikea|икеа|hoff|obi|castorama|zara|gloria|глория|ostin|остин|detskiy mir|детский мир|dns|мвидео|mvideo|eldorado|эльдорадо|ситилинк|citilink/i, 'Одежда и дом'],
];

const BANK_CATEGORY_MAP: [RegExp, string][] = [
  [/супермаркет|продукт/i, 'Продукты'],
  [/рестора|кафе|фастфуд/i, 'Кафе и доставка еды'],
  [/транспорт|автомобил|топлив|азс/i, 'Транспорт и АЗС'],
  [/здоровье|медицин|аптек/i, 'Здоровье и аптеки'],
  [/образован/i, 'Дети и школа'],
  [/отдых и развлечения|развлечен/i, 'Подписки и развлечения'],
  [/одежда|дом и ремонт|товары для дома/i, 'Одежда и дом'],
  [/коммунальн|жкх/i, 'ЖКХ'],
  [/связь|телеком/i, 'Связь и интернет'],
];

function expenseCategory(t: RawTx): Base {
  const d = t.description;
  if (/^MAPP_SBERBANK_ONL@IN_PAY/i.test(d)) {
    if (/интернет|связ|тв\b/i.test(d)) return { kind: 'expense', category: 'Связь и интернет' };
    if (/жкх|коммун|квартплат/i.test(d)) return { kind: 'expense', category: 'ЖКХ' };
    return { kind: 'expense', category: 'Платежи в СберОнлайн', needsReview: true };
  }
  for (const [re, cat] of EXPENSE_RULES) if (re.test(d)) return { kind: 'expense', category: cat };
  if (t.bankCategory) for (const [re, cat] of BANK_CATEGORY_MAP) if (re.test(t.bankCategory)) return { kind: 'expense', category: cat };
  return { kind: 'expense', category: 'Прочее' };
}

interface Ctx { ownCards: Set<string>; ownContracts: Set<string>; ownBanks: Set<string> }

function baseClassify(t: RawTx, ctx: Ctx): Base {
  const d = t.description;
  const bc = t.bankCategory ?? '';
  const inc = t.amount > 0;

  // 1. Явные переводы между своими счетами
  if (/VKLAD-KARTA|KARTA-VKLAD/i.test(d)) return { kind: 'transfer', category: TRANSFER_CATEGORY, transferNote: inc ? 'Со своего вклада в Сбере' : 'На свой вклад в Сбере' };
  if (/^Перевод себе/i.test(d)) return { kind: 'transfer', category: TRANSFER_CATEGORY, transferNote: 'Между своими счетами Т-Банка' };
  const contract = d.match(/Внутренний перевод (?:на|с) договор[а]?\s*(\d{6,})/i)?.[1];
  if (contract) {
    if (ctx.ownContracts.has(contract)) return { kind: 'transfer', category: TRANSFER_CATEGORY, transferNote: `Свой договор Т-Банка №…${contract.slice(-4)}` };
    return { kind: inc ? 'income' : 'expense', category: inc ? 'Входящие переводы' : 'Переводы другим людям', needsReview: true, transferLike: true };
  }
  const cardRef = d.match(/(?:С карты|На карту)\s+\d{4,6}\*+(\d{4})/i)?.[1];
  if (cardRef && ctx.ownCards.has(cardRef)) return { kind: 'transfer', category: TRANSFER_CATEGORY, transferNote: `${inc ? 'С' : 'На'} свою карту •${cardRef}` };

  // 2. СБП-переводы в/из банков
  if (/^Перевод СБП$/i.test(bc)) {
    const bank = detectBank(d);
    if (bank && ctx.ownBanks.has(bank.key)) return { kind: 'transfer', category: TRANSFER_CATEGORY, transferNote: `${inc ? 'Со своего счёта' : 'На свой счёт'} в ${bank.name}`, transferLike: true };
    if (!inc && bank?.key === 'wb') return { kind: 'expense', category: 'Маркетплейсы' };
    return { kind: inc ? 'income' : 'expense', category: inc ? 'Входящие переводы' : 'Переводы другим людям', transferLike: true };
  }

  // 3. Доходы и возвраты
  if (inc) {
    if (/возврат|отмена/i.test(bc) || /возврат покупки|отмена операции|отмена возврата|refund/i.test(d)) {
      return { kind: 'refund', category: expenseCategory(t).category };
    }
    if (/заработн|зарплат|аванс/i.test(d)) return { kind: 'income', category: 'Зарплата' };
    if (/отпускн/i.test(d)) return { kind: 'income', category: 'Отпускные' };
    if (/социальн|пособи|пенси|выплаты.*фонд|сфр|материнск/i.test(d)) return { kind: 'income', category: 'Соцвыплаты' };
    if (/кэшб[эе]к|cshbck|cashback|бонус/i.test(d)) return { kind: 'income', category: 'Кэшбэк' };
    if (/^Пополнение/i.test(d)) return { kind: 'income', category: 'Пополнения (источник неизвестен)', needsReview: true, transferLike: true };
    if (/перевод/i.test(bc + ' ' + d) || /^SBOL$/i.test(d)) return { kind: 'income', category: 'Входящие переводы', transferLike: true, needsReview: /^SBOL$/i.test(d) };
    return { kind: 'income', category: 'Прочие доходы' };
  }

  // 4. Исходящие переводы людям
  if (/Внешний перевод по номеру телефона|Внешний банковский перевод|перевод по номеру/i.test(d)) {
    return { kind: 'expense', category: 'Переводы другим людям', transferLike: true };
  }
  if (/^Перевод с карты$/i.test(bc) || /^SBOL$/i.test(d)) {
    return { kind: 'expense', category: 'Переводы другим людям', needsReview: true, transferLike: true };
  }
  return expenseCategory(t);
}

function ts(t: RawTx): number {
  return Date.parse(`${t.date}T${t.time ?? '12:00'}:00Z`);
}

export function classifyAll(data: AppData): ClassifiedTx[] {
  const ownCards = new Set(data.accounts.flatMap(a => a.cards));
  const ownContracts = new Set(data.accounts.map(a => a.number));
  const ownBanks = new Set<string>([...data.settings.ownBanks, ...data.accounts.map(a => a.bank)]);
  const ctx: Ctx = { ownCards, ownContracts, ownBanks };
  const rules = new Map(data.rules.map(r => [r.merchant, r]));

  const out: (ClassifiedTx & { transferLike?: boolean })[] = data.txs.map(t => {
    const b = baseClassify(t, ctx);
    return { ...t, ...b, transferLike: b.transferLike || b.kind === 'transfer', merchant: merchantKey(t) };
  });

  // Поиск пар «ушло с одного своего счёта — пришло на другой» среди импортированных счетов.
  // Вторая сторона уже распознанного перевода (например, «С карты …1234» в кредитке) тоже становится переводом.
  const cands = out.filter(t => t.transferLike);
  const used = new Set<string>();
  const accTitle = new Map(data.accounts.map(a => [a.id, a.title]));
  for (const a of cands) {
    if (used.has(a.id) || a.amount >= 0) continue;
    let best: typeof a | undefined;
    let bestDt = Infinity;
    for (const b of cands) {
      if (used.has(b.id) || b.accountId === a.accountId || b.amount !== -a.amount) continue;
      if (Math.abs(diffDays(a.date, b.date)) > 1) continue;
      const dt = Math.abs(ts(a) - ts(b));
      if (dt < bestDt) { best = b; bestDt = dt; }
    }
    if (best) {
      used.add(a.id); used.add(best.id);
      const pairId = a.id + '~' + best.id;
      Object.assign(a, { kind: 'transfer', category: TRANSFER_CATEGORY, needsReview: false, pairId, transferNote: `На свой счёт: ${accTitle.get(best.accountId)}` });
      Object.assign(best, { kind: 'transfer', category: TRANSFER_CATEGORY, needsReview: false, pairId, transferNote: `Со своего счёта: ${accTitle.get(a.accountId)}` });
    }
  }

  // Правила и ручные правки пользователя
  for (const t of out) {
    const r = rules.get(t.merchant);
    if (r) { t.category = r.category; if (r.kind) t.kind = r.kind; t.needsReview = false; t.overridden = true; }
    const o = data.overrides[t.id];
    if (o) {
      if (o.kind) t.kind = o.kind;
      if (o.category) t.category = o.category;
      if (o.kind === 'transfer' && !o.category) t.category = TRANSFER_CATEGORY;
      t.needsReview = false; t.overridden = true;
    }
    delete t.transferLike;
  }
  return out.sort((x, y) => (y.date + (y.time ?? '')).localeCompare(x.date + (x.time ?? '')));
}

export { BANKS };
