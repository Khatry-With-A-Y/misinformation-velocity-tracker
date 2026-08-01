type BrandMarkProps = {
  className?: string
}

/**
 * GuffGuard brand mark: a face with a finger over the lips ("shh").
 * Drawn inline in lucide style (24x24, currentColor stroke) so it renders
 * identically across platforms, unlike emoji.
 */
export function BrandMark({ className }: BrandMarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M9 9h.01" />
      <path d="M15 9h.01" />
      <path d="M8.5 15H10" />
      <path d="M14 15h1.5" />
      <path d="M12 21.5V13" />
    </svg>
  )
}
