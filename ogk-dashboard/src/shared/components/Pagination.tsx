import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/shared/utils/cn.ts'

type PageItem = number | 'ellipsis-start' | 'ellipsis-end'

type Props = {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  disabled?: boolean
  previousLabel?: string
  nextLabel?: string
  ariaLabel?: string
}

function getPageItems(page: number, totalPages: number): PageItem[] {
  if (totalPages <= 5) return Array.from({ length: totalPages }, (_, index) => index + 1)
  if (page <= 3) return [1, 2, 3, 'ellipsis-end', totalPages]
  if (page >= totalPages - 2) return [1, 'ellipsis-start', totalPages - 2, totalPages - 1, totalPages]
  return [1, 'ellipsis-start', page - 1, page, page + 1, 'ellipsis-end', totalPages]
}

export function Pagination({
  page,
  totalPages,
  onPageChange,
  disabled = false,
  previousLabel = 'Trang trước',
  nextLabel = 'Trang sau',
  ariaLabel = 'Phân trang',
}: Props) {
  if (totalPages <= 1) return null

  const items = getPageItems(page, totalPages)
  const buttonClass =
    'grid size-9 shrink-0 cursor-pointer place-items-center rounded-lg text-sm font-semibold transition duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-45'
  const inactiveClass = 'glass-input text-brand-700 hover:bg-white/90 hover:shadow-control'
  const activeClass = 'bg-linear-to-r from-brand-500 to-brand-400 text-white shadow-control'

  return (
    <nav aria-label={ariaLabel} className="flex justify-end">
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label={previousLabel}
          className={cn(buttonClass, inactiveClass)}
          disabled={disabled || page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft aria-hidden="true" className="size-4" />
        </button>
        {items.map((item) =>
          typeof item === 'number' ? (
            <button
              key={item}
              type="button"
              aria-label={`Trang ${item}`}
              aria-current={item === page ? 'page' : undefined}
              className={cn(
                buttonClass,
                item !== page && item !== 1 && item !== totalPages && 'hidden sm:grid',
                item === page ? activeClass : inactiveClass,
              )}
              disabled={disabled}
              onClick={() => onPageChange(item)}
            >
              {item}
            </button>
          ) : (
            <span key={item} aria-hidden="true" className="grid size-9 shrink-0 place-items-center text-ink-subtle">
              …
            </span>
          ),
        )}
        <button
          type="button"
          aria-label={nextLabel}
          className={cn(buttonClass, inactiveClass)}
          disabled={disabled || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight aria-hidden="true" className="size-4" />
        </button>
      </div>
    </nav>
  )
}
