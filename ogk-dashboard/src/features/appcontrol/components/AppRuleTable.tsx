import { Badge, Button, Table, TableBody, TableHead, TableRow, Td, Th } from '@/shared/components/index.ts'
import type { AppRule } from '@/shared/types/policy.ts'
import { ACTION_LABELS } from '@/features/appcontrol/utils/messages.ts'

type Props = {
  rules: AppRule[]
  pending: boolean
  onRemove: (rule: AppRule) => void
}

function shortSha(sha: string | null): string {
  return sha ? `${sha.slice(0, 8)}…${sha.slice(-8)}` : 'Không có'
}

export default function AppRuleTable({ rules, pending, onRemove }: Props) {
  if (rules.length === 0) {
    return <p className="text-ink-muted">Chưa có luật nào. Mọi ứng dụng đều được chạy.</p>
  }
  return (
    <Table>
      <TableHead>
        <TableRow>
          <Th>Ứng dụng</Th>
          <Th>SHA-256</Th>
          <Th>Hành động</Th>
          <Th>
            <span className="sr-only">Xóa</span>
          </Th>
        </TableRow>
      </TableHead>
      <TableBody>
        {rules.map((rule) => (
          <TableRow key={`${rule.name}-${rule.sha256 ?? ''}`}>
            <Td className="font-medium text-ink">{rule.name}</Td>
            <Td>
              <span className="font-mono text-sm" title={rule.sha256 ?? undefined}>
                {shortSha(rule.sha256)}
              </span>
            </Td>
            <Td>
              <Badge tone={rule.action === 'block' ? 'danger' : 'success'}>{ACTION_LABELS[rule.action]}</Badge>
            </Td>
            <Td className="text-right">
              <Button variant="ghost" size="sm" disabled={pending} onClick={() => onRemove(rule)}>
                Xóa
              </Button>
            </Td>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
