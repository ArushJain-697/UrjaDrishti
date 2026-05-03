import { useState } from 'react'
import SystemStatus from './components/SystemStatus.jsx'
import PlantView from './pages/PlantView.jsx'
import ClusterView from './pages/ClusterView.jsx'
import EvaluationView from './pages/EvaluationView.jsx'

const TABS = [
  { id: 'plant', label: 'Plant View' },
  { id: 'cluster', label: 'Cluster View' },
  { id: 'evaluation', label: 'Evaluation' },
]

export default function App() {
  const [active, setActive] = useState('plant')

  return (
    <div className="min-h-screen bg-[#0f1117] text-[#e8eaf0]">
      <div
        className="fixed left-0 right-0 top-0 z-[200] h-[2px] w-full bg-[linear-gradient(90deg,#3b82f6_0%,#a78bfa_50%,#14b8a6_100%)]"
        aria-hidden
      />
      <header className="sticky top-0 z-[100] border-b border-[#2a2d3e] bg-[#1a1d27]">
        <div className="mx-auto flex max-w-[1400px] flex-col gap-4 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-1 items-start gap-3 lg:max-w-xs">
            <img
              src="/urja-logo.svg"
              alt=""
              width={40}
              height={40}
              className="h-10 w-10 shrink-0"
            />
            <div className="flex min-w-0 flex-col gap-1">
              <span className="text-lg font-medium tracking-tight text-[#3b82f6]">UrjaDrishti</span>
              <span className="text-[12px] text-[#5a5d72]">Karnataka Renewable Forecasting</span>
            </div>
          </div>
          <nav
            className="flex flex-1 justify-center gap-1 sm:gap-2"
            aria-label="Primary"
          >
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setActive(t.id)}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active === t.id
                    ? 'bg-[#1e2130] text-[#e8eaf0]'
                    : 'text-[#8b8fa8] hover:bg-[#1e2130]/60 hover:text-[#e8eaf0]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
          <div className="flex flex-1 justify-end">
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
