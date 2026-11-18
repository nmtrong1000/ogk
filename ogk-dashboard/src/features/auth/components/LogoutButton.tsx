import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../../shared/components/index.ts'
import { logout } from '../api.ts'
import { switchSession } from '../hooks/useMe.ts'

export default function LogoutButton() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: logout,
    // Phiên đã mất ở server hay chưa thì phía trình duyệt cũng coi như đã đăng xuất.
    onSettled: () => {
      switchSession(queryClient, null)
      navigate('/login', { replace: true })
    },
  })
  return (
    <Button variant="secondary" size="sm" loading={mutation.isPending} onClick={() => mutation.mutate()}>
      Đăng xuất
    </Button>
  )
}
