/*
 * Children list with add and delete. The add form is remounted (key bump) after a success to clear its inputs.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Card, Spinner, Table, TableBody, TableHead, TableRow, Td, Th } from '@/shared/components/index.ts'
import { childrenKey, createChild, deleteChild, listChildren } from '@/features/family/api.ts'
import ChildForm from '@/features/family/components/ChildForm.tsx'
import ConfirmDelete from '@/features/family/components/ConfirmDelete.tsx'
import { errorMessage } from '@/features/family/utils/messages.ts'
import { ageFrom } from '@/features/family/utils/year.ts'

export default function ChildrenPage() {
  const queryClient = useQueryClient()
  const [formKey, setFormKey] = useState(0)
  const [added, setAdded] = useState<string | null>(null)
  const children = useQuery({ queryKey: childrenKey, queryFn: listChildren })

  const create = useMutation({
    mutationFn: createChild,
    onSuccess: (child) => {
      setAdded(child.name)
      setFormKey((k) => k + 1)
      queryClient.invalidateQueries({ queryKey: childrenKey })
    },
  })
  const remove = useMutation({
    mutationFn: deleteChild,
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: ['children', id] })
      queryClient.invalidateQueries({ queryKey: childrenKey })
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Các con</h1>
        <p className="mt-1 text-ink-muted">Thêm, sửa hoặc xóa thông tin của từng con.</p>
      </div>

      <Card title="Danh sách">
        <div className="flex flex-col gap-4">
          {remove.isError && <Alert tone="error">{errorMessage(remove.error)}</Alert>}
          {children.isPending && (
            <div className="grid place-items-center py-8">
              <Spinner />
            </div>
          )}
          {children.isError && <Alert tone="error">{errorMessage(children.error)}</Alert>}
          {children.data?.length === 0 && (
            <p className="py-8 text-center text-sm text-ink-muted">Chưa có con nào. Thêm con ở bên dưới.</p>
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
                  <TableRow key={child.id}>
                    <Td className="font-medium">
                      <Link to={`/children/${child.id}`}>{child.name}</Link>
                    </Td>
                    <Td>
                      {child.birth_year} <span className="text-ink-muted">({ageFrom(child.birth_year)} tuổi)</span>
                    </Td>
                    <Td className="text-right">
                      <div className="flex flex-wrap items-center justify-end gap-1">
                        <Link
                          to={`/children/${child.id}`}
                          className="rounded-control px-3 py-1.5 text-sm font-semibold no-underline hover:bg-white/50"
                        >
                          Sửa
                        </Link>
                        <ConfirmDelete
                          name={child.name}
                          pending={remove.isPending && remove.variables === child.id}
                          onConfirm={() => remove.mutate(child.id)}
                        />
                      </div>
                    </Td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </Card>

      <Card title="Thêm con" description="Tên và năm sinh được mã hóa khi lưu trên server.">
        <div className="flex flex-col gap-4">
          {added && !create.isError && <Alert tone="success">Đã thêm {added}.</Alert>}
          <ChildForm
            key={formKey}
            submitLabel="Thêm"
            pending={create.isPending}
            error={create.error}
            onSubmit={(body) => {
              setAdded(null)
              create.mutate(body)
            }}
          />
        </div>
      </Card>
    </div>
  )
}
