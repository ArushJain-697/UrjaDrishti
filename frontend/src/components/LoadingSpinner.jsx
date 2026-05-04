export default function LoadingSpinner({ size = 40, className = '' }) {
  const s = typeof size === 'number' ? `${size}px` : size
  return (
    <div
      className={`inline-block rounded-full border-2 border-line border-t-[#10b981] animate-spin ${className}`}
      style={{ width: s, height: s }}
      role="status"
      aria-label="Loading"
    />
  )
}
