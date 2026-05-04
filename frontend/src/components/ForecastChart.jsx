import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { plantMeta } from '../api/client'

function ChartTooltip({ active, payload, label, lineColor = '#10b981', showYesterday }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  const { p50, p10, p90, yForecast, yActual } = row
  const w = p90 - p10
  const h = Number(label)
  const hh = String(h).padStart(2, '0')

  return (
    <div className="rounded-lg border border-line bg-hover-bg px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-medium text-main-text">
        {hh}:00 <span className="text-faint-text">IST</span>
      </p>
      <p style={{ color: lineColor }}>P50: {p50.toFixed(1)} MW</p>
      <p className="text-muted-text">P10: {p10.toFixed(1)} MW</p>
      <p className="text-muted-text">P90: {p90.toFixed(1)} MW</p>
      <p className="mt-1 text-[11px] text-faint-text">Interval width: {w.toFixed(1)} MW</p>
      {showYesterday && yForecast != null && (
        <div className="mt-1 border-t border-line pt-1">
          <p className="text-[11px] text-[#5a5d72]">Yesterday forecast: {yForecast.toFixed(1)} MW</p>
          {yActual != null && (
            <p className="text-[11px] text-[#22c55e]">Yesterday actual: {yActual.toFixed(1)} MW</p>
          )}
        </div>
      )}
    </div>
  )
}

/** Compute mean absolute percentage error between two arrays */
function mape(forecast, actuals) {
  let sum = 0, count = 0
  for (let i = 0; i < forecast.length; i++) {
    if (forecast[i] > 0) {
      sum += Math.abs((actuals[i] - forecast[i]) / forecast[i])
      count++
    }
  }
  return count > 0 ? (sum / count) * 100 : 0
}

export default function ForecastChart({
  forecast,
  plantId,
  intradayNowHour,
  yesterdayForecast = null,
  yesterdayActuals = null,
  className = '',
}) {
  const meta = plantMeta(plantId)
  const lineColor = meta.type === 'wind' ? '#34d399' : '#10b981'
  const bandFill =
    meta.type === 'wind' ? 'rgba(167, 139, 250, 0.18)' : 'rgba(59, 130, 246, 0.18)'
  const chartBg = 'var(--hover-bg)'
  const showYesterday = !!yesterdayForecast && !!yesterdayActuals

  const data = forecast.hours.map((h, i) => ({
    hour: h,
    p50: forecast.p50[i],
    p10: forecast.p10[i],
    p90: forecast.p90[i],
    ...(showYesterday ? {
      yForecast: yesterdayForecast[i],
      yActual: yesterdayActuals[i],
    } : {}),
  }))

  // Accuracy stats for legend
  const accuracy = showYesterday
    ? (100 - mape(yesterdayForecast, yesterdayActuals)).toFixed(1)
    : null
  const peakHour = showYesterday
    ? yesterdayForecast.indexOf(Math.max(...yesterdayForecast))
    : null
  const peakErr = showYesterday
    ? Math.abs(yesterdayActuals[peakHour] - yesterdayForecast[peakHour]).toFixed(1)
    : null

  return (
    <div className={`w-full rounded-xl border border-line bg-hover-bg ${className}`}>
      <div className="h-[320px] w-full p-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
            <CartesianGrid stroke="var(--line)" strokeOpacity={0.5} vertical={false} />
            <XAxis
              dataKey="hour"
              tickFormatter={(v) => `${String(v).padStart(2, '0')}:00`}
              stroke="var(--line)"
              tick={{ fill: 'var(--muted-text)', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'var(--line)' }}
            />
            <YAxis
              stroke="var(--line)"
              tick={{ fill: 'var(--muted-text)', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'var(--line)' }}
              width={44}
              label={{
                value: 'MW',
                angle: -90,
                position: 'insideLeft',
                fill: 'var(--faint-text)',
                fontSize: 11,
              }}
            />
            <Tooltip
              content={(tipProps) => (
                <ChartTooltip {...tipProps} lineColor={lineColor} showYesterday={showYesterday} />
              )}
              cursor={{ stroke: 'var(--line)', strokeOpacity: 0.6 }}
            />

            {/* Today's P10-P90 band */}
            <Area
              type="monotone"
              dataKey="p90"
              stroke="none"
              fill={bandFill}
              isAnimationActive
              animationDuration={800}
            />
            <Area
              type="monotone"
              dataKey="p10"
              stroke="none"
              fill={chartBg}
              isAnimationActive
              animationDuration={800}
            />

            {/* Yesterday's forecast — dashed grey */}
            {showYesterday && (
              <Line
                type="monotone"
                dataKey="yForecast"
                stroke="#5a5d72"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                opacity={0.7}
                isAnimationActive
                animationDuration={600}
              />
            )}
            {/* Yesterday's actuals — dotted green */}
            {showYesterday && (
              <Line
                type="monotone"
                dataKey="yActual"
                stroke="#22c55e"
                strokeWidth={1.5}
                strokeDasharray="2 4"
                dot={false}
                opacity={0.8}
                isAnimationActive
                animationDuration={700}
              />
            )}

            {/* Today's P50 on top */}
            <Line
              type="monotone"
              dataKey="p50"
              stroke={lineColor}
              strokeWidth={2}
              dot={false}
              isAnimationActive
              animationDuration={800}
            />

            {typeof intradayNowHour === 'number' ? (
              <ReferenceLine
                x={intradayNowHour}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                label={{
                  value: 'Now',
                  position: 'top',
                  fill: '#f59e0b',
                  fontSize: 11,
                }}
              />
            ) : null}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Yesterday legend — only visible when overlay is active */}
      {showYesterday && (
        <div className="border-t border-line px-4 py-2.5">
          <div className="flex flex-wrap items-center gap-4 text-[11px]">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-5 rounded" style={{ background: lineColor }} />
              <span className="text-muted-text">Today P50</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block h-0.5 w-5 rounded"
                style={{ background: '#5a5d72', borderTop: '2px dashed #5a5d72', height: 0 }}
              />
              <svg width="20" height="4"><line x1="0" y1="2" x2="20" y2="2" stroke="#5a5d72" strokeWidth="2" strokeDasharray="4 4"/></svg>
              <span className="text-muted-text">Yesterday forecast</span>
            </span>
            <span className="flex items-center gap-1.5">
              <svg width="20" height="4"><line x1="0" y1="2" x2="20" y2="2" stroke="#22c55e" strokeWidth="2" strokeDasharray="2 4"/></svg>
              <span className="text-muted-text">Yesterday actuals</span>
            </span>
            {accuracy && (
              <span
                className="ml-auto rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
                style={{ background: 'rgba(34,197,94,0.12)', color: '#22c55e' }}
              >
                Yesterday: {accuracy}% accurate — {peakErr} MW off at peak
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
