import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, CheckCircle, Activity, BarChart, ShieldAlert } from 'lucide-react'
import LoadingSpinner from './LoadingSpinner'
import { client, fetchFleetHardware, fetchSystemCalibration, PLANTS } from '../api/client'

export default function ModelHealthPanel() {
  const [data, setData] = useState({ hardware: null, calibration: null })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch 100% REAL historical sample data from the ML backend test set
      const response = await client.get('/api/evaluation/historical_sample?date=2024-01-15')
      const res = response.data
      if (res.status === 'success' && res.plant_data) {
        const plantData = res.plant_data
        
        // Now feed the REAL data into the ML audit endpoints
        const [hwRes, calRes] = await Promise.all([
          fetchFleetHardware(plantData),
          fetchSystemCalibration(plantData)
        ])

        setData({
          hardware: hwRes.data,
          calibration: calRes.data
        })
      }
    } catch (err) {
      console.error('Failed to load health data:', err)
      setError('Failed to connect to monitoring services')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  const { hardware, calibration } = data
  const hwResult = hardware?.result || {}
  const calResult = calibration?.result || {}
  const calAnalysis = calibration?.analysis

  const hwPlants = hwResult.plants || {}
  const calPlants = calResult.plants || {}

  const sysStatus = hwResult.summary?.system_status || hwResult.system_status || 'UNKNOWN';
  const calStatus = calResult.summary?.status || calResult.status || 'UNKNOWN';

  return (
    <div className="mt-8 space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className={`p-5 rounded-xl border ${sysStatus?.includes('HEALTHY') ? 'bg-[#22c55e]/10 border-[#22c55e]/20' : 'bg-red-500/10 border-red-500/20'}`}>
          <div className="flex items-center gap-3 mb-2">
            <Activity className={sysStatus?.includes('HEALTHY') ? 'text-[#22c55e]' : 'text-red-500'} />
            <h3 className="text-lg font-medium text-main-text">Hardware Fleet Status</h3>
          </div>
          <p className="text-2xl font-bold mb-1" style={{ color: sysStatus?.includes('HEALTHY') ? '#22c55e' : '#ef4444' }}>
            {sysStatus}
          </p>
          <p className="text-sm text-muted-text">Monitoring via CQR Violations</p>
        </div>

        <div className={`p-5 rounded-xl border ${calStatus?.includes('CALIBRATED') ? 'bg-[#22c55e]/10 border-[#22c55e]/20' : 'bg-[#fbbf24]/10 border-[#fbbf24]/20'}`}>
          <div className="flex items-center gap-3 mb-2">
            <BarChart className={calStatus?.includes('CALIBRATED') ? 'text-[#22c55e]' : 'text-[#fbbf24]'} />
            <h3 className="text-lg font-medium text-main-text">System Calibration</h3>
          </div>
          <p className="text-2xl font-bold mb-1" style={{ color: calStatus?.includes('CALIBRATED') ? '#22c55e' : '#fbbf24' }}>
            {calStatus}
          </p>
          <p className="text-sm text-muted-text">Model uncertainty bounds validation</p>
        </div>
      </div>

      {/* Detailed Plant Grid */}
      <div className="mt-8 overflow-x-auto rounded-xl border border-line bg-hover-bg">
        <table className="w-full min-w-[700px] border-collapse text-sm">
          <thead>
            <tr className="bg-surface-bg text-left text-[11px] font-medium uppercase tracking-[0.06em] text-faint-text">
              <th className="border-b border-line px-4 py-3">Plant</th>
              <th className="border-b border-line px-4 py-3">Hardware Diagnostics</th>
              <th className="border-b border-line px-4 py-3">Calibration Status</th>
            </tr>
          </thead>
          <tbody>
            {PLANTS.map(p => {
              const hp = hwPlants[p.id]
              const cp = calPlants[p.id]
              
              return (
                <tr key={p.id} className="border-b border-line hover:bg-surface-bg transition-colors">
                  <td className="px-4 py-3 font-medium text-main-text">{p.name}</td>
                  
                  <td className="px-4 py-3">
                    {hp ? (
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-1.5">
                          {hp.anomaly ? <ShieldAlert className="w-4 h-4 text-red-500" /> : <CheckCircle className="w-4 h-4 text-[#22c55e]" />}
                          <span className={hp.anomaly ? 'text-red-500 font-medium' : 'text-[#22c55e]'}>
                            {hp.severity === 'none' ? 'Normal' : hp.severity.toUpperCase()}
                          </span>
                        </div>
                        <span className="text-[11px] text-muted-text">{hp.recommendation}</span>
                      </div>
                    ) : '—'}
                  </td>

                  <td className="px-4 py-3">
                    {cp ? (
                      <div className="flex flex-col gap-1">
                        <span className={cp.is_calibrated ? 'text-[#22c55e] font-medium' : 'text-[#fbbf24] font-medium'}>
                          {cp.calibration_status}
                        </span>
                        {cp.calibration_results && cp.calibration_results['0.5'] && (
                          <span className="text-[11px] text-muted-text">
                            P50 Cov: {Math.round(cp.calibration_results['0.5'].observed_coverage * 100)}%
                          </span>
                        )}
                      </div>
                    ) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
