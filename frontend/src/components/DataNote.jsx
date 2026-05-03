import { useLanguage } from '../context/LanguageContext.jsx'

export default function DataNote() {
  const { t } = useLanguage()
  return (
    <p className="mt-8 border-t border-[#2a2d3e] pt-4 text-center text-[11px] leading-relaxed text-[#5a5d72]">
      {t('footerText')} 🔒
    </p>
  )
}
