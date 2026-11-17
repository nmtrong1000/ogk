import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { logout } from './api.ts'
import { switchSession } from './useMe.ts'

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
    <button type="button" className="button button-link" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
      Đăng xuất
    </button>
  )
}
