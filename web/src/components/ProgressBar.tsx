/** A thin bar for "how much of the goal". The bar stops at 100%; `percent` itself may be more. */
export function ProgressBar({ percent, label }: { percent: number; label: string }) {
  const filled = Math.min(100, Math.max(0, percent))
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(filled)}
      aria-valuetext={`${Math.round(percent)}%`}
      className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
    >
      <div className="h-full rounded-full bg-green-600" style={{ width: `${filled}%` }} />
    </div>
  )
}
