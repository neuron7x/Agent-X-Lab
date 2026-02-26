/* eslint-disable @typescript-eslint/no-empty-object-type */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { Lang } from '@/lib/i18n';
import { t as translate, type TranslationKey } from '@/lib/i18n';

interface LanguageContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const stored = localStorage.getItem('axl_lang');
    return (stored === 'en' || stored === 'ua') ? stored : 'ua';
  });

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    localStorage.setItem('axl_lang', l);
  }, []);

  const t = useCallback((key: TranslationKey) => translate(key, lang), [lang]);

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
