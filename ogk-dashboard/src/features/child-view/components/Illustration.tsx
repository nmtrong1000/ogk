export default function Illustration({ mood }: { mood: 'happy' | 'calm' | 'rest' }) {
  const mouth =
    mood === 'happy' ? 'M84 96 Q100 110 116 96' : mood === 'calm' ? 'M86 100 H114' : 'M86 104 Q100 94 114 104'
  return (
    <svg
      viewBox="0 0 200 160"
      className="h-32 w-auto sm:h-40"
      role="img"
      aria-label="Hình chiếc máy tính đang mỉm cười"
    >
      <circle cx="160" cy="34" r="18" fill="#fcd34d" />
      <rect x="40" y="30" width="120" height="86" rx="14" fill="var(--color-brand-500)" />
      <rect x="50" y="40" width="100" height="66" rx="8" fill="#ffffff" />
      <circle cx="84" cy="70" r="6" fill="var(--color-brand-700)" />
      <circle cx="116" cy="70" r="6" fill="var(--color-brand-700)" />
      <path d={mouth} stroke="var(--color-brand-700)" strokeWidth="5" fill="none" strokeLinecap="round" />
      <rect x="88" y="116" width="24" height="16" fill="var(--color-brand-400)" />
      <rect x="62" y="130" width="76" height="10" rx="5" fill="var(--color-brand-300)" />
    </svg>
  )
}
