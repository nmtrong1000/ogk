import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { commandsKey, listCommands, sendCommand, type CommandType } from '@/features/commands/api.ts'
import { Alert, Button } from '@/shared/components/index.ts'

const labels: Record<CommandType, string> = { lock: 'Khóa ngay', unlock: 'Mở khóa', add_time: 'Cộng 15 phút' }

export default function CommandControls({ deviceId, childId }: { deviceId: number; childId: number }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const commands = useQuery({
    queryKey: commandsKey(deviceId, childId),
    queryFn: () => listCommands(deviceId, childId),
    refetchInterval: 1500,
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
    <div className="mt-3 flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {(Object.keys(labels) as CommandType[]).map((type) => (
          <Button
            key={type}
            size="sm"
            variant={type === 'lock' ? 'danger' : 'secondary'}
            loading={send.isPending}
            onClick={() => send.mutate(type)}
          >
            {labels[type]}
          </Button>
        ))}
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {commands.data?.[0] && (
        <p aria-live="polite" className="text-xs text-ink-muted">
          Lệnh gần nhất: {labels[commands.data[0].type]} ·{' '}
          {commands.data[0].status === 'acknowledged' ? 'Đã xác nhận' : 'Đang chờ máy xác nhận'}
        </p>
      )}
    </div>
  )
}
