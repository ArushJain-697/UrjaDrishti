import { useState } from 'react'
import { Monitor } from 'lucide-react'
import SystemStatus from './components/SystemStatus.jsx'
import PlantView from './pages/PlantView.jsx'
import ClusterView from './pages/ClusterView.jsx'
import EvaluationView from './pages/EvaluationView.jsx'
import WarRoomView from './pages/WarRoomView.jsx'
import ImpactCounters from './components/ImpactCounters.jsx'
import { useLanguage } from './context/LanguageContext.jsx'
import { useTheme } from './context/ThemeContext.jsx'

export default function App() {
  const [active, setActive] = useState('plant')
  const [warRoom, setWarRoom] = useState(false)
  const { lang, toggleLang, t } = useLanguage()
  const { theme, toggleTheme } = useTheme()

  const enterWarRoom = () => {
    document.documentElement.requestFullscreen?.().catch(() => {})
    setWarRoom(true)
  }
  const exitWarRoom = () => {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {})
    setWarRoom(false)
  }
  const tabs = [
    { id: 'plant', label: t('plantView') },
    { id: 'cluster', label: t('clusterView') },
    { id: 'evaluation', label: t('evaluation') },
  ]

  if (warRoom) return <WarRoomView onExit={exitWarRoom} />

  return (
    <div className="min-h-screen bg-base-bg text-main-text">
      <header className="sticky top-0 z-[100] bg-surface-bg">
        <div
          className="h-[3px] w-full"
          style={{
            background: 'linear-gradient(to right, #10b981, #34d399, #059669)',
          }}
          aria-hidden
        />
        <div className="mx-auto flex max-w-[1400px] flex-col gap-4 border-b border-line px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-1 items-start gap-3 lg:max-w-xs">
            <img
              src="/urja-logo.svg"
              alt=""
              width={40}
              height={40}
              className="h-10 w-10 shrink-0"
            />
            <div className="flex min-w-0 flex-col gap-1">
              <span className="text-lg font-medium tracking-tight text-[#10b981]">{t('appName')}</span>
              <span className="text-[12px] text-faint-text">{t('appSubtitle')}</span>
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
                    ? 'bg-hover-bg text-main-text'
                    : 'text-muted-text hover:bg-hover-bg/60 transition-all duration-300 hover:scale-[1.02] hover:text-main-text'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="flex flex-1 items-center justify-end gap-2">
            <button
              onClick={toggleTheme}
              title="Toggle Theme"
              className="flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-xs font-medium transition-colors hover:border-[#10b981] transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_10px_rgba(16,185,129,0.2)]"
              style={{ color: 'var(--muted-text)' }}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <button
              onClick={toggleLang}
              className="flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-xs font-medium transition-colors hover:border-[#10b981] transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_10px_rgba(16,185,129,0.2)]"
              style={{ color: 'var(--muted-text)' }}
            >
              <span style={{ color: lang === 'kn' ? '#10b981' : 'var(--muted-text)' }}>ಕ</span>
              <span style={{ color: 'var(--faint-text)' }}>/</span>
              <span style={{ color: lang === 'en' ? '#10b981' : 'var(--muted-text)' }}>A</span>
            </button>
            <ImpactCounters />
            <SystemStatus />
            <button
              onClick={enterWarRoom}
              title="Enter War Room — fullscreen grid monitor"
              className="flex items-center gap-1.5 rounded-md border border-[#ff3d0030] bg-[#ff3d0008] px-3 py-1.5 text-xs font-semibold transition-all duration-200 hover:border-[#ff3d00] hover:bg-[#ff3d0015] hover:shadow-[0_0_12px_rgba(255,61,0,0.3)]"
              style={{ color: '#ff5252' }}
            >
              <Monitor className="h-3.5 w-3.5" aria-hidden />
              War Room
            </button>
          </div>
        </div>
      </header>
      <main className="animate-fade-in">
        {active === 'plant' ? <PlantView /> : null}
        {active === 'cluster' ? <ClusterView /> : null}
        {active === 'evaluation' ? <EvaluationView /> : null}
      </main>
    </div>
  )
}
