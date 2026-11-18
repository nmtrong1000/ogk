/*
 * Logout button. The browser treats the user as logged out whether or not the server session still existed.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/shared/components/index.ts'
import { logout } from '@/features/auth/api.ts'
import { switchSession } from '@/features/auth/hooks/useMe.ts'

export default function LogoutButton() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: logout,
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
