export default function LoadingSpinner({ size = 40, className = '' }) {
  const s = typeof size === 'number' ? `${size}px` : size
  return (
    <div
      className={`inline-block rounded-full border-2 border-[#2a2d3e] border-t-[#3b82f6] animate-spin ${className}`}
      style={{ width: s, height: s }}
      role="status"
      aria-label="Loading"
    />
  )
}
