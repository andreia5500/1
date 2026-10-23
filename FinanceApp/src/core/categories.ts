// Справочник категорий и банков

export interface CategoryInfo {
  name: string;
  color: string;
  /** повседневные траты — по ним считается прогноз «сколько ещё уйдёт до конца месяца» */
  everyday?: boolean;
  /** регулярные обязательные платежи — кандидаты в план платежей */
  regular?: boolean;
}

export const EXPENSE_CATEGORIES: CategoryInfo[] = [
  { name: 'Продукты', color: '#2E9E5B', everyday: true },
  { name: 'Маркетплейсы', color: '#7B4FD6', everyday: true },
  { name: 'Кафе и доставка еды', color: '#E0752D', everyday: true },
  { name: 'Транспорт и АЗС', color: '#2F7BD8', everyday: true },
  { name: 'Здоровье и аптеки', color: '#D6457A', everyday: true },
  { name: 'Одежда и дом', color: '#A0663A', everyday: true },
  { name: 'Наличные', color: '#6F8A2E', everyday: true },
  { name: 'Дети и школа', color: '#E3A21A', regular: true },
  { name: 'Связь и интернет', color: '#1F9AA8', regular: true },
  { name: 'Подписки и развлечения', color: '#C2410C', regular: true },
  { name: 'ЖКХ', color: '#4B6584', regular: true },
  { name: 'Госуслуги, налоги, штрафы', color: '#64748B' },
  { name: 'Комиссии банка', color: '#B91C1C' },
  { name: 'Проценты по кредитам', color: '#991B1B' },
  { name: 'Переводы другим людям', color: '#A64D79' },
  { name: 'Взыскания и долги', color: '#7F1D1D' },
  { name: 'Платежи в СберОнлайн', color: '#94A3B8' },
  { name: 'Прочее', color: '#9CA3AF', everyday: true },
];

export const INCOME_CATEGORIES: CategoryInfo[] = [
  { name: 'Зарплата', color: '#16A34A' },
  { name: 'Отпускные', color: '#22C55E' },
  { name: 'Соцвыплаты', color: '#0EA5E9' },
  { name: 'Кэшбэк', color: '#EAB308' },
  { name: 'Входящие переводы', color: '#6366F1' },
  { name: 'Пополнения (источник неизвестен)', color: '#94A3B8' },
  { name: 'Прочие доходы', color: '#9CA3AF' },
];

export const TRANSFER_CATEGORY = 'Свои переводы';

const all = new Map([...EXPENSE_CATEGORIES, ...INCOME_CATEGORIES].map(c => [c.name, c]));
export function catInfo(name: string): CategoryInfo {
  return all.get(name) ?? { name, color: '#9CA3AF', everyday: true };
}

export interface BankInfo { key: string; name: string; re: RegExp }

export const BANKS: BankInfo[] = [
  { key: 'sber', name: 'Сбербанк', re: /сбер|sber/i },
  { key: 'tbank', name: 'Т-Банк', re: /т-банк|тинькофф|tinkoff|t-bank/i },
  { key: 'ozon', name: 'Озон Банк', re: /озон банк|ozon bank|\(ozon\)/i },
  { key: 'yandex', name: 'Яндекс Банк', re: /^яндекс(?! маркет)|yandex bank/i },
  { key: 'vtb', name: 'ВТБ', re: /втб|vtb/i },
  { key: 'alfa', name: 'Альфа-Банк', re: /альфа|alfa/i },
  { key: 'wb', name: 'Вайлдберриз Банк', re: /вайлдберриз|wildberries/i },
  { key: 'gpb', name: 'Газпромбанк', re: /газпромбанк/i },
  { key: 'ubrir', name: 'УБРиР', re: /убрир|ubrir/i },
  { key: 'pochta', name: 'Почта Банк', re: /почта банк/i },
  { key: 'mts', name: 'МТС Банк', re: /мтс банк|mts bank/i },
  { key: 'raif', name: 'Райффайзен', re: /райффайзен|raiffeisen/i },
  { key: 'sovcom', name: 'Совкомбанк', re: /совкомбанк|sovcom/i },
  { key: 'psb', name: 'ПСБ', re: /^псб|промсвязьбанк/i },
  { key: 'rshb', name: 'Россельхозбанк', re: /россельхоз/i },
];

export function detectBank(text: string): BankInfo | undefined {
  return BANKS.find(b => b.re.test(text));
}
