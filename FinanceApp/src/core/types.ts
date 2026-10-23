// Общие типы данных приложения

export type BankId = 'sber' | 'tbank';
export type AccountKind = 'debit' | 'credit';

export interface Account {
  id: string;            // 'sber:<номер счёта>' / 'tbank:<номер договора>'
  bank: BankId;
  kind: AccountKind;
  title: string;         // «Сбер дебетовая •1234»
  number: string;        // номер счёта / договора
  cards: string[];       // последние 4 цифры карт
  creditLimit?: number;
  rate?: number;         // % годовых
  graceDays?: number;
  debt?: number;         // задолженность по последней выписке (положительное число)
  debtDate?: string;
  minPayment?: number;
  minPaymentDue?: string; // YYYY-MM-DD
  balance?: number;      // остаток собственных средств (для дебетовых)
  balanceDate?: string;
}

export interface StatementMeta {
  id: string;
  accountId: string;
  fileName: string;
  periodFrom: string;    // YYYY-MM-DD
  periodTo: string;
  opening?: number;
  closing?: number;
  totalIn: number;       // по шапке выписки
  totalOut: number;      // по шапке выписки (положительное число)
  parsedIn: number;      // сумма разобранных поступлений
  parsedOut: number;     // сумма разобранных списаний
  verified: boolean;     // разобранное совпало с итогами шапки
  importedAt: string;
  txCount: number;
}

/** Операция «как в выписке», без нашей классификации */
export interface RawTx {
  id: string;
  accountId: string;
  date: string;          // YYYY-MM-DD
  time?: string;         // HH:MM
  amount: number;        // со знаком: + поступление, − списание
  bankCategory?: string;
  description: string;
  card?: string;
  authCode?: string;
}

export type TxKind = 'expense' | 'income' | 'transfer' | 'refund';

export interface ClassifiedTx extends RawTx {
  kind: TxKind;
  category: string;
  /** пояснение, почему операция считается переводом между своими счетами */
  transferNote?: string;
  pairId?: string;
  needsReview?: boolean;
  merchant: string;      // нормализованное имя для правил
  overridden?: boolean;
}

export interface ParsedStatement {
  account: Account;
  meta: Omit<StatementMeta, 'id' | 'importedAt' | 'fileName'>;
  txs: RawTx[];
}

export interface Rule {
  merchant: string;
  category: string;
  kind?: TxKind;
}

export interface TxOverride {
  category?: string;
  kind?: TxKind;
}

export interface Goal {
  id: string;
  title: string;
  target: number;
  saved: number;
  deadline?: string;     // YYYY-MM-DD
}

export interface Planned {
  id: string;
  title: string;
  type: 'income' | 'payment';
  amount: number;
  day: number;           // день месяца
  enabled: boolean;
  auto?: boolean;
  key?: string;          // ключ автоопределения, чтобы не дублировать
}

export interface ManualDebt {
  id: string;
  title: string;
  debt: number;
  rate: number;
  minPayment: number;
}

export interface Settings {
  ownBanks: string[];            // ключи банков из BANKS (кроме тех, чьи выписки загружены)
  limits: Record<string, number>; // месячные лимиты по категориям
  goals: Goal[];
  planned: Planned[];
  plannedDismissed: string[];     // ключи автопредложений, удалённых пользователем
  debtOverrides: Record<string, { rate?: number; minPayment?: number; dueDay?: number }>;
  manualDebts: ManualDebt[];
  debtBudget?: number;            // сколько в месяц готов отдавать на долги
}

export interface AppData {
  version: 1;
  accounts: Account[];
  statements: StatementMeta[];
  txs: RawTx[];
  rules: Rule[];
  overrides: Record<string, TxOverride>;
  settings: Settings;
}

export function emptyData(): AppData {
  return {
    version: 1,
    accounts: [],
    statements: [],
    txs: [],
    rules: [],
    overrides: {},
    settings: {
      ownBanks: ['ozon', 'yandex'],
      limits: {},
      goals: [],
      planned: [],
      plannedDismissed: [],
      debtOverrides: {},
      manualDebts: [],
    },
  };
}
