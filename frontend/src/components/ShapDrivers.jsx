import { useLanguage } from '../context/LanguageContext.jsx'

export default function ShapDrivers({ alerts }) {
  const { t } = useLanguage()
  const localizedFeature = (featureKey) => {
    const featureMap = t('features') || {}
    if (featureMap[featureKey]) return featureMap[featureKey]
    const aliases = {
      CMF: 'cloud_modification_factor',
      temperature: 'temperature_c',
      hour_sin: 'hour_sin',
      hour_cos: 'hour_cos',
    }
    const aliasKey = aliases[featureKey]
    if (aliasKey && featureMap[aliasKey]) return featureMap[aliasKey]
    return featureKey.replace(/_/g, ' ')
  }
  
  if (!alerts || alerts.length === 0) return null
  
  // Pick the alert with the most significant drivers, or just the first one
  const alertWithDrivers = alerts.find(a => a.top_drivers && a.top_drivers.length > 0)
  if (!alertWithDrivers) return null

  const maxShap = Math.max(...alertWithDrivers.top_drivers.map(d => Math.abs(d.shap_value)))
  
  return (
    <div className="mt-4 rounded-xl border border-line bg-surface-bg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium tracking-tight text-main-text">
          {t('shapDriversTitle') || `Key Forecast Drivers (${String(alertWithDrivers.hour).padStart(2, '0')}:00)`}
        </h3>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-faint-text">{t('shapValues') || 'SHAP Values'}</span>
      </div>
      
      <div className="flex flex-col gap-3">
        {alertWithDrivers.top_drivers.map((d, i) => {
          const isPositive = d.shap_value > 0
          // Normalize width relative to the max absolute SHAP value for visual balance
          const widthPct = maxShap > 0 ? (Math.abs(d.shap_value) / maxShap) * 100 : 0
          
          return (
            <div key={`${d.feature}-${i}`} className="flex items-center gap-3 text-xs">
              <span className="w-28 truncate text-right font-medium text-muted-text" title={d.feature}>
                {localizedFeature(d.feature)}
              </span>
              
              <div className="relative flex h-5 flex-1 items-center bg-hover-bg/50 rounded-sm">
                {/* Center zero line */}
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-line z-10" />
                
                {isPositive ? (
                  <>
                    <div className="w-1/2" />
                    <div className="w-1/2 flex items-center h-full">
                      <div 
                        className="h-3/4 rounded-r-sm bg-emerald-500/80 transition-all duration-500" 
                        style={{ width: `${widthPct}%` }} 
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-1/2 flex justify-end items-center h-full">
                      <div 
                        className="h-3/4 rounded-l-sm bg-red-500/80 transition-all duration-500" 
                        style={{ width: `${widthPct}%` }} 
                      />
                    </div>
                    <div className="w-1/2" />
                  </>
                )}
              </div>
              
              <span className={`w-12 text-right tabular-nums font-medium ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
                {isPositive ? '+' : ''}{d.shap_value.toFixed(3)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
