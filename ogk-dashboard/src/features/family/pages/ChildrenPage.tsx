import { Pencil, Plus } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Card,
  Dialog,
  EmptyState,
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
import type { Child, ChildInput } from '@/shared/types/family.ts'
import { childKey, childrenKey, createChild, deleteChild, listChildren, updateChild } from '@/features/family/api.ts'
import ChildForm from '@/features/family/components/ChildForm.tsx'
import { errorMessage } from '@/features/family/utils/messages.ts'
import { ageFrom } from '@/features/family/utils/year.ts'

export default function ChildrenPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const showToast = useToast()
  const [formKey, setFormKey] = useState(0)
  const [adding, setAdding] = useState(false)
  const [editing, setEditing] = useState<Child | null>(null)
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
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: ChildInput }) => updateChild(id, body),
    onSuccess: (child) => {
      setEditing(null)
      showToast({ tone: 'success', message: `Đã cập nhật ${child.name}.` })
      queryClient.setQueryData(childKey(child.id), child)
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
          <Button
            onClick={() => {
              create.reset()
              setAdding(true)
            }}
          >
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
            <EmptyState message="Chưa có trẻ nào." description="Nhấn “Thêm trẻ” để bắt đầu." />
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
                      <div className="flex flex-wrap justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(event) => {
                            event.stopPropagation()
                            update.reset()
                            setEditing(child)
                          }}
                        >
                          <Pencil aria-hidden="true" className="size-3.5" />
                          Sửa
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-rose-600 hover:bg-rose-50/60"
                          onClick={(event) => {
                            event.stopPropagation()
                            remove.reset()
                            setConfirming(child)
                          }}
                        >
                          Xóa
                        </Button>
                      </div>
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
        open={editing !== null}
        title={`Sửa ${editing?.name ?? 'trẻ'}`}
        onClose={() => !update.isPending && setEditing(null)}
        className="max-w-lg"
      >
        {editing && (
          <>
            <p className="text-sm text-ink-muted">Tên và năm sinh được mã hóa khi lưu trên server.</p>
            <div className="mt-5">
              <ChildForm
                key={`${editing.id}-${editing.updated_at}`}
                initial={{ name: editing.name, birth_year: editing.birth_year }}
                submitLabel="Lưu thay đổi"
                pending={update.isPending}
                error={update.error}
                inlineErrors
                onCancel={() => setEditing(null)}
                onSubmit={(body) => update.mutate({ id: editing.id, body })}
              />
            </div>
          </>
        )}
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
        {remove.isError && (
          <p role="alert" className="mt-4 text-sm text-rose-700">
            {errorMessage(remove.error)}
          </p>
        )}
      </Dialog>
    </div>
  )
}
