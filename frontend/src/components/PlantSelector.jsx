import { useEffect, useId, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { PLANTS, plantDisplayName } from '../api/client'
import { useLanguage } from '../context/LanguageContext.jsx'

function Dot({ type }) {
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${
        type === 'solar' ? 'bg-[#10b981]' : 'bg-[#34d399]'
      }`}
      aria-hidden
    />
  )
}

export default function PlantSelector({ value, onChange, className = '' }) {
  const { lang, t } = useLanguage()
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const listId = useId()
  const selected = PLANTS.find((p) => p.id === value) || PLANTS[0]

  useEffect(() => {
    function onDoc(e) {
      if (!rootRef.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const groups = [
    { key: 'A', label: t('clusterA'), items: PLANTS.filter((p) => p.cluster === 'A') },
    { key: 'B', label: t('clusterB'), items: PLANTS.filter((p) => p.cluster === 'B') },
  ]

  return (
    <div ref={rootRef} className={`relative min-w-[280px] ${className}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 rounded-lg border border-line bg-hover-bg px-3 py-2 text-left text-sm text-main-text outline-none transition hover:border-[#10b981] transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_10px_rgba(16,185,129,0.2)]/40 focus:border-[#10b981]"
      >
        <span className="flex min-w-0 items-center gap-2">
          <Dot type={selected.type} />
          <span className="truncate">
            {selected.id} — {plantDisplayName(selected, lang)} — {selected.capacityMw.toFixed(1)} MW
          </span>
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted-text transition ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-line bg-surface-bg py-1 shadow-xl"
        >
          {groups.map((g) => (
            <li key={g.key} className="px-2 py-1">
              <div className="px-2 py-1 text-[11px] font-medium uppercase tracking-[0.06em] text-faint-text">
                {g.label}
              </div>
              <ul role="presentation">
                {g.items.map((p) => {
                  const active = p.id === value
                  return (
                    <li key={p.id} role="presentation">
                      <button
                        type="button"
                        role="option"
                        aria-selected={active}
                        onClick={() => {
                          onChange(p.id)
                          setOpen(false)
                        }}
                        className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition hover:bg-hover-bg ${
                          active ? 'bg-hover-bg text-[#60a5fa]' : 'text-main-text'
                        }`}
                      >
                        <Dot type={p.type} />
                        <span className="truncate">
                          {p.id} — {plantDisplayName(p, lang)} — {p.capacityMw.toFixed(1)} MW
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
