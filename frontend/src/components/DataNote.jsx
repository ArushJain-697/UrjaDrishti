import { useLanguage } from '../context/LanguageContext.jsx'

export default function DataNote() {
  const { t } = useLanguage()
  return (
    <p className="mt-8 border-t border-line pt-4 text-center text-[11px] leading-relaxed text-faint-text">
      {t('footerText')} 🔒
    </p>
  )
}
