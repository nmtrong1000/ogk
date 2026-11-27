const CURRENT_YEAR = new Date().getFullYear()

export default function AppFooter() {
  return (
    <footer className="flex h-9 shrink-0 items-center justify-center border-t border-white/60 bg-white/70 px-3 text-xs text-ink-muted backdrop-blur-md">
      © {CURRENT_YEAR} by Nguyễn Minh Trọng
    </footer>
  )
}
