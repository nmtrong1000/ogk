import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Clock3, LockKeyhole, LockKeyholeOpen } from 'lucide-react'
import { commandsKey, listCommands, sendCommand, type CommandType } from '@/features/commands/api.ts'
import { Alert, Button } from '@/shared/components/index.ts'

const labels: Record<CommandType, string> = { lock: 'Khóa ngay', unlock: 'Mở khóa', add_time: 'Cộng 15 phút' }
const icons = { lock: LockKeyhole, unlock: LockKeyholeOpen, add_time: Clock3 }

export default function CommandControls({ deviceId, childId }: { deviceId: number; childId: number }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const commands = useQuery({
    queryKey: commandsKey(deviceId, childId),
    queryFn: () => listCommands(deviceId, childId),
    refetchInterval: (query) => (query.state.data?.some((command) => command.status === 'pending') ? 1500 : false),
  })
  const send = useMutation({
    mutationFn: (type: CommandType) => sendCommand(deviceId, childId, type),
    onSuccess: async () => {
      setError(null)
      await queryClient.invalidateQueries({ queryKey: commandsKey(deviceId, childId) })
    },
    onError: () => setError('Không gửi được lệnh. Vui lòng thử lại.'),
  })
  return (
    <div className="flex w-full flex-col items-end gap-2">
      <div className="flex flex-wrap justify-end gap-2">
        {(Object.keys(labels) as CommandType[]).map((type) => {
          const Icon = icons[type]
          return (
            <Button
              key={type}
              size="sm"
              variant={type === 'lock' ? 'danger' : 'secondary'}
              loading={send.isPending}
              className={type === 'unlock' ? 'bg-emerald-500 text-white shadow-sm hover:bg-emerald-600 hover:border-emerald-600' : ''}
              onClick={() => send.mutate(type)}
            >
              <Icon aria-hidden="true" className="size-4" />
              {labels[type]}
            </Button>
          )
        })}
      </div>
      {error && (
        <Alert tone="error" className="w-full text-left">
          {error}
        </Alert>
      )}
      {commands.data?.[0] && (
        <p aria-live="polite" className="text-xs text-ink-muted">
          Lệnh gần nhất: {labels[commands.data[0].type]} ·{' '}
          {commands.data[0].status === 'acknowledged' ? 'Đã xác nhận' : 'Đang chờ máy xác nhận'}
        </p>
      )}
    </div>
  )
}
