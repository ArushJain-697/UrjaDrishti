export default function StatCard({
  title,
  value,
  subtitle,
  className = '',
  valueClassName = '',
  icon: Icon,
}) {
  return (
    <div
      className={`rounded-xl border border-[#2a2d3e] bg-[#1e2130] p-4 ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#5a5d72]">
          {title}
        </p>
        {Icon ? <Icon className="h-4 w-4 shrink-0 text-[#22c55e]" aria-hidden /> : null}
      </div>
      <p className={`mt-2 text-2xl font-medium tracking-tight ${valueClassName}`}>{value}</p>
      {subtitle ? (
        <p className="mt-1 text-[13px] leading-snug text-[#8b8fa8]">{subtitle}</p>
      ) : null}
    </div>
  )
}
