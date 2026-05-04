import { useEffect, useState } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'

/** Shown when API failed but mock data loaded; auto-hides after 4s. */
export default function CachedDataNotice() {
  const [visible, setVisible] = useState(true)
  const { t } = useLanguage()

  useEffect(() => {
    const t = window.setTimeout(() => setVisible(false), 4000)
    return () => window.clearTimeout(t)
  }, [])

  if (!visible) return null

  return (
    <div
      className="mb-4 rounded-lg border border-line bg-surface-bg px-3 py-2 text-[13px] text-faint-text"
      role="status"
    >
      {t('cachedData')}
    </div>
  )
}
