'use client';

import { createContext, useContext, useEffect, useState } from 'react';

type Lang = 'en' | 'pt';

const LangContext = createContext<{ lang: Lang; toggle: () => void }>({
  lang: 'en',
  toggle: () => {},
});

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>('en');

  useEffect(() => {
    const stored = localStorage.getItem('vigia_lang') as Lang | null;
    if (stored === 'pt' || stored === 'en') {
      setLang(stored);
    } else {
      const browser = navigator.language.toLowerCase().startsWith('pt') ? 'pt' : 'en';
      setLang(browser);
    }
  }, []);

  function toggle() {
    setLang((prev) => {
      const next = prev === 'en' ? 'pt' : 'en';
      localStorage.setItem('vigia_lang', next);
      return next;
    });
  }

  return <LangContext.Provider value={{ lang, toggle }}>{children}</LangContext.Provider>;
}

export function useLang() {
  return useContext(LangContext);
}
