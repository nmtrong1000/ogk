import { Card, Table, TableBody, TableHead, TableRow, Td, Th } from '@/shared/components/index.ts'
import { formatDateTime } from '@/shared/utils/dateTime.ts'
import type { PolicyVersion } from '@/shared/types/policy.ts'
import { formatMinutes, openHours } from '@/shared/utils/schedule.ts'
import { setterLabel } from '@/features/policy/utils/messages.ts'

export default function VersionHistory({ versions }: { versions: PolicyVersion[] }) {
  return (
    <Card title="Lịch sử phiên bản" description="Tối đa 50 phiên bản gần nhất, mới nhất ở trên.">
      <Table>
        <TableHead>
          <TableRow>
            <Th>Phiên bản</Th>
            <Th>Thời điểm</Th>
            <Th>Người đặt</Th>
            <Th>Ngày thường</Th>
            <Th>Cuối tuần</Th>
            <Th>Giờ cho phép/tuần</Th>
            <Th>Luật ứng dụng</Th>
          </TableRow>
        </TableHead>
        <TableBody>
          {versions.map((v) => (
            <TableRow key={v.policy_version}>
              <Td className="font-semibold">{v.policy_version}</Td>
              <Td className="whitespace-nowrap">{formatDateTime(v.created_at)}</Td>
              <Td>{setterLabel(v.set_by)}</Td>
              <Td className="whitespace-nowrap">{formatMinutes(v.weekday_quota_minutes)}</Td>
              <Td className="whitespace-nowrap">{formatMinutes(v.weekend_quota_minutes)}</Td>
              <Td>{openHours(v.weekly_schedule)}</Td>
              <Td>{v.app_rules.length}</Td>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}
