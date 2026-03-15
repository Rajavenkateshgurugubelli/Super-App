import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';
import { messages, SUPPORTED_LOCALES, DEFAULT_LOCALE } from './translations.js';

const I18nContext = createContext(null);

export const useI18n = () => {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return ctx;
};

const STORAGE_KEY = 'superapp.locale';

const resolveInitialLocale = () => {
  if (typeof window === 'undefined') return DEFAULT_LOCALE;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && messages[stored]) return stored;
  const browser = window.navigator.language || window.navigator.languages?.[0];
  const match = SUPPORTED_LOCALES.find((l) => l.code === browser);
  return match ? match.code : DEFAULT_LOCALE;
};

const I18nProvider = ({ children }) => {
  const [locale, setLocale] = useState(resolveInitialLocale);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, locale);
    }
  }, [locale]);

  const value = useMemo(() => {
    const dict = messages[locale] || messages[DEFAULT_LOCALE];
    const t = (path, fallback) => {
      const parts = path.split('.');
      let current = dict;
      for (const part of parts) {
        if (current && Object.prototype.hasOwnProperty.call(current, part)) {
          current = current[part];
        } else {
          return fallback ?? path;
        }
      }
      return typeof current === 'string' ? current : fallback ?? path;
    };

    const currentLocale = SUPPORTED_LOCALES.find((l) => l.code === locale) || SUPPORTED_LOCALES[0];

    return {
      locale,
      setLocale,
      t,
      messages: dict,
      supportedLocales: SUPPORTED_LOCALES,
      region: currentLocale.region,
    };
  }, [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export default I18nProvider;

