import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../shared/api/client.ts'
import type { Health } from '../shared/types/health.ts'

export default function HomePage() {
  const { data, error, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<Health>('/api/health'),
  })

  let status = 'Đang kiểm tra...'
  if (error) status = `Lỗi: ${error.message}`
  else if (!isPending) status = data.status

  return (
    <section>
      <h1>Trạng thái server</h1>
      <p>{status}</p>
    </section>
  )
}
