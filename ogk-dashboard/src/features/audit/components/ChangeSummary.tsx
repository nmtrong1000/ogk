/*
 * Admin cannot see values, so entries without values show only the target type and id.
 */
import type { AuditEntry } from '../../../shared/types/audit.ts'
import { changes, targetLabel } from '../utils/format.ts'

export default function ChangeSummary({ entry }: { entry: AuditEntry }) {
  const items = changes(entry)
  if (items.length === 0) {
    return (
      <span className="text-ink-muted">
        {targetLabel(entry.target_type)} #{entry.target_id}
      </span>
    )
  }
  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-0.5">
      {items.map((c) => (
        <div key={c.field} className="contents">
          <dt className="text-ink-muted">{c.label}:</dt>
          <dd className="min-w-0 break-words">
            {c.before !== undefined && c.after !== undefined ? (
              <>
                <span className="text-ink-muted line-through decoration-rose-400/70">{c.before}</span>
                <span aria-label="đổi thành" className="mx-1.5 text-ink-muted">
                  →
                </span>
                <span className="font-medium">{c.after}</span>
              </>
            ) : c.after !== undefined ? (
              <span className="font-medium">{c.after}</span>
            ) : (
              <span className="text-ink-muted line-through decoration-rose-400/70">{c.before}</span>
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}
