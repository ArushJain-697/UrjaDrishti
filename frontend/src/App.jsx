import { useState } from 'react'
import SystemStatus from './components/SystemStatus.jsx'
import PlantView from './pages/PlantView.jsx'
import ClusterView from './pages/ClusterView.jsx'
import EvaluationView from './pages/EvaluationView.jsx'
import { useLanguage } from './context/LanguageContext.jsx'

export default function App() {
  const [active, setActive] = useState('plant')
  const { lang, toggleLang, t } = useLanguage()
  const tabs = [
    { id: 'plant', label: t('plantView') },
    { id: 'cluster', label: t('clusterView') },
    { id: 'evaluation', label: t('evaluation') },
  ]

  return (
    <div className="min-h-screen bg-[#0f1117] text-[#e8eaf0]">
      <header className="sticky top-0 z-[100] bg-[#1a1d27]">
        <div
          className="h-[3px] w-full"
          style={{
            background: 'linear-gradient(to right, #3b82f6, #a78bfa, #14b8a6)',
          }}
          aria-hidden
        />
        <div className="mx-auto flex max-w-[1400px] flex-col gap-4 border-b border-[#2a2d3e] px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-1 items-start gap-3 lg:max-w-xs">
            <img
              src="/urja-logo.svg"
              alt=""
              width={40}
              height={40}
              className="h-10 w-10 shrink-0"
            />
            <div className="flex min-w-0 flex-col gap-1">
              <span className="text-lg font-medium tracking-tight text-[#3b82f6]">{t('appName')}</span>
              <span className="text-[12px] text-[#5a5d72]">{t('appSubtitle')}</span>
            </div>
          </div>
          <nav
            className="flex flex-1 justify-center gap-1 sm:gap-2"
            aria-label="Primary"
          >
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActive(tab.id)}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active === tab.id
                    ? 'bg-[#1e2130] text-[#e8eaf0]'
                    : 'text-[#8b8fa8] hover:bg-[#1e2130]/60 hover:text-[#e8eaf0]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="flex flex-1 items-center justify-end gap-2">
            <button
              onClick={toggleLang}
              className="flex items-center gap-1.5 rounded-md border border-[#2a2d3e] px-3 py-1.5 text-xs font-medium transition-colors hover:border-[#3b82f6]"
              style={{ color: '#8b8fa8' }}
            >
              <span style={{ color: lang === 'kn' ? '#3b82f6' : '#8b8fa8' }}>ಕ</span>
              <span style={{ color: '#5a5d72' }}>/</span>
              <span style={{ color: lang === 'en' ? '#3b82f6' : '#8b8fa8' }}>A</span>
            </button>
            <SystemStatus />
          </div>
        </div>
      </header>
      <main>
        {active === 'plant' ? <PlantView /> : null}
        {active === 'cluster' ? <ClusterView /> : null}
        {active === 'evaluation' ? <EvaluationView /> : null}
      </main>
    </div>
  )
}
