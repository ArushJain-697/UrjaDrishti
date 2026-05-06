import { createContext, useContext, useEffect, useState } from 'react'
import { translations } from '../i18n/translations'

const LanguageContext = createContext()
const STORAGE_KEY = 'urjadrishti_language'

function getInitialLanguage() {
  if (typeof window === 'undefined') return 'en'
  const saved = window.localStorage.getItem(STORAGE_KEY)
  return saved === 'kn' ? 'kn' : 'en'
}

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(getInitialLanguage)
  const t = (key, params = {}) => {
    let str = translations[lang][key] || translations.en[key] || key
    Object.entries(params).forEach(([k, v]) => {
      str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), v)
    })
    return str
  }
  const toggleLang = () => setLang((l) => (l === 'en' ? 'kn' : 'en'))

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, lang)
    }
  }, [lang])

  return <LanguageContext.Provider value={{ lang, toggleLang, t }}>{children}</LanguageContext.Provider>
}

export const useLanguage = () => useContext(LanguageContext)
