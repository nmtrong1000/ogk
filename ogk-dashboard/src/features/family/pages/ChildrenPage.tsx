import { Plus } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Card,
  Dialog,
  Spinner,
  Table,
  TableBody,
  TableHead,
  TableRow,
  Td,
  Th,
} from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import { ToastMessage } from '@/shared/components/ToastProvider.tsx'
import type { Child } from '@/shared/types/family.ts'
import { childrenKey, createChild, deleteChild, listChildren } from '@/features/family/api.ts'
import ChildForm from '@/features/family/components/ChildForm.tsx'
import { errorMessage } from '@/features/family/utils/messages.ts'
import { ageFrom } from '@/features/family/utils/year.ts'

export default function ChildrenPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const showToast = useToast()
  const [formKey, setFormKey] = useState(0)
  const [adding, setAdding] = useState(false)
  const [confirming, setConfirming] = useState<Child | null>(null)
  const children = useQuery({ queryKey: childrenKey, queryFn: listChildren })

  const create = useMutation({
    mutationFn: createChild,
    onSuccess: (child) => {
      setAdding(false)
      setFormKey((key) => key + 1)
      showToast({ tone: 'success', message: `Đã thêm ${child.name}.` })
      queryClient.invalidateQueries({ queryKey: childrenKey })
    },
  })
  const remove = useMutation({
    mutationFn: deleteChild,
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: ['children', id] })
      queryClient.invalidateQueries({ queryKey: childrenKey })
      setConfirming(null)
    },
    onError: (error) => showToast({ tone: 'error', message: errorMessage(error) }),
  })

  function openChild(event: KeyboardEvent<HTMLTableRowElement>, childId: number) {
    if (event.target !== event.currentTarget || (event.key !== 'Enter' && event.key !== ' ')) return
    event.preventDefault()
    navigate(`/children/${childId}`)
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Các con</h1>
        <p className="mt-1 text-ink-muted">Thêm, sửa hoặc xóa thông tin của từng con.</p>
      </div>

      <Card
        title="Danh sách trẻ"
        actions={
          <Button onClick={() => setAdding(true)}>
            <Plus aria-hidden="true" className="size-4" />
            Thêm trẻ
          </Button>
        }
      >
        <div className="flex flex-col gap-4">
          {children.isPending && (
            <div className="grid place-items-center py-8">
              <Spinner />
            </div>
          )}
          {children.isError && <ToastMessage tone="error">{errorMessage(children.error)}</ToastMessage>}
          {children.data?.length === 0 && (
            <p className="py-8 text-center text-sm text-ink-muted">Chưa có trẻ nào. Nhấn “Thêm trẻ” để bắt đầu.</p>
          )}
          {children.data && children.data.length > 0 && (
            <Table>
              <TableHead>
                <tr>
                  <Th>Tên</Th>
                  <Th>Năm sinh</Th>
                  <Th>
                    <span className="sr-only">Thao tác</span>
                  </Th>
                </tr>
              </TableHead>
              <TableBody>
                {children.data.map((child) => (
                  <TableRow
                    key={child.id}
                    tabIndex={0}
                    aria-label={`Mở chi tiết ${child.name}`}
                    className="cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand-500"
                    onClick={() => navigate(`/children/${child.id}`)}
                    onKeyDown={(event) => openChild(event, child.id)}
                  >
                    <Td className="font-medium">{child.name}</Td>
                    <Td>
                      {child.birth_year} <span className="text-ink-muted">({ageFrom(child.birth_year)} tuổi)</span>
                    </Td>
                    <Td className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-rose-600 hover:bg-rose-50/60"
                        onClick={(event) => {
                          event.stopPropagation()
                          setConfirming(child)
                        }}
                      >
                        Xóa
                      </Button>
                    </Td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </Card>

      <Dialog open={adding} title="Thêm trẻ" onClose={() => !create.isPending && setAdding(false)} className="max-w-lg">
        <p className="text-sm text-ink-muted">Tên và năm sinh được mã hóa khi lưu trên server.</p>
        <div className="mt-5">
          <ChildForm
            key={formKey}
            submitLabel="Thêm trẻ"
            pending={create.isPending}
            error={create.error}
            inlineErrors
            onCancel={() => setAdding(false)}
            onSubmit={(body) => create.mutate(body)}
          />
        </div>
      </Dialog>

      <Dialog
        open={confirming !== null}
        title={`Xóa ${confirming?.name ?? 'trẻ'}?`}
        onClose={() => !remove.isPending && setConfirming(null)}
        actions={
          <>
            <Button variant="ghost" disabled={remove.isPending} onClick={() => setConfirming(null)}>
              Hủy
            </Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() => confirming && remove.mutate(confirming.id)}
            >
              Xóa
            </Button>
          </>
        }
      >
        <p>Thông tin của {confirming?.name ?? 'trẻ'} sẽ bị xóa khỏi tài khoản và không thể khôi phục.</p>
      </Dialog>
    </div>
  )
}
