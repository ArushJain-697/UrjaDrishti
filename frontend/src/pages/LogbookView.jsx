import { useState, useEffect } from 'react'
import { Printer, Trash2 } from 'lucide-react'
import { PLANTS } from '../api/client'
import { useLanguage } from '../context/LanguageContext'

const OFFICERS = ['R. Kumar', 'S. Patil', 'M. Hegde', 'A. Nair']

export default function LogbookView() {
  const { t } = useLanguage()
  const [entries, setEntries] = useState([])
  const [search, setSearch] = useState('')
  const [filterPlant, setFilterPlant] = useState('all')

  // Form state
  const [selectedPlant, setSelectedPlant] = useState('PVG_S1')
  const [selectedHour, setSelectedHour] = useState('12:00')
  const [noteText, setNoteText] = useState('')
  const [officerName, setOfficerName] = useState(OFFICERS[0])

  useEffect(() => {
    const saved = localStorage.getItem('urjadrishti_logbook')
    if (saved) {
      setEntries(JSON.parse(saved))
    } else {
      // Mock entries
      const mock = [
        {
          id: 1, timestamp: "2026-03-05T06:15:00.000Z", plant_id: "PVG_S1", hour: "06:00",
          note: "Morning shift started. Clear sky conditions. Forecast confidence high. Proceeding with scheduled draw.",
          officer: "R. Kumar", forecast_p50_at_hour: 12.3
        },
        {
          id: 2, timestamp: "2026-03-05T09:30:00.000Z", plant_id: "GAD_W1", hour: "09:00",
          note: "Wind speed picking up from northwest. Output tracking above forecast. No action required.",
          officer: "S. Patil", forecast_p50_at_hour: 45.2
        },
        {
          id: 3, timestamp: "2026-03-05T11:45:00.000Z", plant_id: "MIX_S1", hour: "11:00",
          note: "Cloud cover developing from west. Notified dispatch. Reduced scheduled draw by 10 MW as precaution.",
          officer: "R. Kumar", forecast_p50_at_hour: 67.8
        }
      ]
      setEntries(mock)
      localStorage.setItem('urjadrishti_logbook', JSON.stringify(mock))
    }
  }, [])

  const saveEntries = (newEntries) => {
    setEntries(newEntries)
    localStorage.setItem('urjadrishti_logbook', JSON.stringify(newEntries))
  }

  const handleAdd = (e) => {
    e.preventDefault()
    if (!noteText.trim()) return
    const newEntry = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      plant_id: selectedPlant,
      hour: selectedHour,
      note: noteText,
      officer: officerName,
      forecast_p50_at_hour: 0 // Mock value
    }
    saveEntries([newEntry, ...entries])
    setNoteText('')
  }

  const handleDelete = (id) => {
    saveEntries(entries.filter(e => e.id !== id))
  }

  const handlePrint = () => {
    window.print()
  }

  const filteredEntries = entries.filter(e => {
    const matchSearch = e.note.toLowerCase().includes(search.toLowerCase()) || 
                        e.officer.toLowerCase().includes(search.toLowerCase()) ||
                        e.plant_id.toLowerCase().includes(search.toLowerCase())
    const matchPlant = filterPlant === 'all' || e.plant_id === filterPlant
    return matchSearch && matchPlant
  })

  return (
    <div className="flex h-full w-full flex-col gap-6 lg:flex-row">
      
      {/* Left Column - Log Entries */}
      <div className="flex-1 flex flex-col rounded-xl border border-line bg-surface-bg p-6">
        <div className="no-print mb-6 flex flex-col gap-4 sm:flex-row sm:items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight text-main-text">Duty Officer Logbook</h2>
          <div className="flex gap-3">
            <input 
              type="text" 
              placeholder="Search logs..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-48 rounded-lg border border-line bg-base-bg px-3 py-1.5 text-sm text-main-text placeholder-muted-text outline-none focus:border-[#3b82f6]"
            />
            <select
              value={filterPlant}
              onChange={(e) => setFilterPlant(e.target.value)}
              className="rounded-lg border border-line bg-base-bg px-3 py-1.5 text-sm text-main-text outline-none focus:border-[#3b82f6]"
            >
              <option value="all">All Plants</option>
              {PLANTS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <button 
              onClick={handlePrint}
              className="flex items-center gap-2 rounded-lg bg-base-bg border border-line px-3 py-1.5 text-sm text-main-text hover:bg-hover-bg transition-colors"
            >
              <Printer className="h-4 w-4" /> Print
            </button>
          </div>
        </div>

        <div className="logbook-printable flex-1 flex flex-col gap-4 overflow-y-auto">
          {filteredEntries.map(e => (
            <div key={e.id} className="group relative flex flex-col gap-2 rounded-lg border border-line bg-base-bg p-4 hover:border-[#3b82f6]/50 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-main-text">{new Date(e.timestamp).toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</span>
                  <span className="rounded-md bg-[#3b82f6]/10 px-2 py-0.5 text-xs font-semibold text-[#3b82f6]">
                    {e.plant_id === 'general' ? 'General' : e.plant_id} • {e.hour}
                  </span>
                </div>
                <span className="text-xs text-muted-text">Officer: {e.officer}</span>
              </div>
              <p className="text-sm text-[#e2e8f0]">{e.note}</p>
              {e.forecast_p50_at_hour > 0 && (
                <p className="text-xs italic text-faint-text">Forecast at this hour was {e.forecast_p50_at_hour} MW</p>
              )}
              <button 
                onClick={() => handleDelete(e.id)}
                className="absolute right-4 bottom-4 text-faint-text hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity no-print"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
          {filteredEntries.length === 0 && (
            <div className="text-center text-muted-text py-10">No log entries found.</div>
          )}
        </div>
      </div>

      {/* Right Column - New Entry Form */}
      <div className="no-print w-full lg:w-80 flex-shrink-0 flex flex-col rounded-xl border border-line bg-surface-bg p-6">
        <h3 className="mb-4 text-lg font-medium text-main-text">New Entry</h3>
        <form onSubmit={handleAdd} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-text">Plant</label>
            <select
              value={selectedPlant}
              onChange={(e) => setSelectedPlant(e.target.value)}
              className="w-full rounded-lg border border-line bg-base-bg px-3 py-2 text-sm text-main-text outline-none focus:border-[#3b82f6]"
            >
              <option value="general">General / All Plants</option>
              {PLANTS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-text">Hour</label>
            <select
              value={selectedHour}
              onChange={(e) => setSelectedHour(e.target.value)}
              className="w-full rounded-lg border border-line bg-base-bg px-3 py-2 text-sm text-main-text outline-none focus:border-[#3b82f6]"
            >
              {Array.from({length: 24}).map((_, i) => {
                const hh = `${i.toString().padStart(2, '0')}:00`
                return <option key={hh} value={hh}>{hh}</option>
              })}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-text">Officer Name</label>
            <select
              value={officerName}
              onChange={(e) => setOfficerName(e.target.value)}
              className="w-full rounded-lg border border-line bg-base-bg px-3 py-2 text-sm text-main-text outline-none focus:border-[#3b82f6]"
            >
              {OFFICERS.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-text">Notes</label>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              rows={4}
              placeholder="Enter observation, action taken, or note..."
              className="w-full resize-none rounded-lg border border-line bg-base-bg p-3 text-sm text-main-text outline-none focus:border-[#3b82f6]"
            />
          </div>

          <button
            type="submit"
            disabled={!noteText.trim()}
            className="mt-2 w-full rounded-lg bg-[#3b82f6] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#2563eb] disabled:opacity-50"
          >
            Add to Logbook
          </button>
        </form>
      </div>

    </div>
  )
}
