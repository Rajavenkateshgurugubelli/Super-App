export const CURRENCIES = {
  USD: {
    id: 1,
    code: 'USD',
    symbol: '$',
    flag: '🇺🇸',
    locale: 'en-US',
    region: 'US',
    minAmount: 0.01,
  },
  INR: {
    id: 2,
    code: 'INR',
    symbol: '₹',
    flag: '🇮🇳',
    locale: 'hi-IN',
    region: 'IN',
    minAmount: 1,
  },
  EUR: {
    id: 3,
    code: 'EUR',
    symbol: '€',
    flag: '🇪🇺',
    locale: 'de-DE',
    region: 'EU',
    minAmount: 0.01,
  },
};

export const CURRENCY_BY_ID = Object.fromEntries(
  Object.values(CURRENCIES).map((c) => [c.id, c]),
);

export const ALL_CURRENCIES = Object.values(CURRENCIES);

export const formatMoney = (amount, currencyCode) => {
  const config = CURRENCIES[currencyCode] || CURRENCIES.USD;
  const { locale, code } = config;
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: code,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount ?? 0);
  } catch {
    return `${config.symbol}${(amount ?? 0).toFixed(2)}`;
  }
};

