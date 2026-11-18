import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Dialog,
  Select,
  Spinner,
  Table,
  TableBody,
  TableHead,
  TableRow,
  Td,
  Th,
  TextField,
} from '@/shared/components/index.ts'


const BRAND = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900']
const INK = [
  ['ink', 'Chữ chính'],
  ['ink-muted', 'Chữ phụ'],
  ['ink-subtle', 'Placeholder'],
]

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card title={title}>
      <div className="flex flex-col gap-4">{children}</div>
    </Card>
  )
}

export default function DesignSystemPage() {
  const [checked, setChecked] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Design system</h1>
        <p className="mt-1 text-ink-muted">Kính mờ, tông xanh dương nhạt. Chỉ hiện khi chạy dev.</p>
      </div>

      <Section title="Màu">
        <div className="grid grid-cols-5 gap-2 sm:grid-cols-10">
          {BRAND.map((step) => (
            <div key={step} className="flex flex-col items-center gap-1">
              <div
                className="h-12 w-full rounded-lg ring-1 ring-black/5"
                style={{ background: `var(--color-brand-${step})` }}
              />
              <span className="text-xs text-ink-muted">{step}</span>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-4">
          {INK.map(([name, label]) => (
            <div key={name} className="flex items-center gap-2">
              <span className="size-6 rounded-full" style={{ background: `var(--color-${name})` }} />
              <span className="text-sm">
                <code>{name}</code> · {label}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Bề mặt kính">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="glass rounded-glass p-5 text-sm">
            <code>glass</code>: thẻ, header
          </div>
          <div className="glass-strong rounded-glass p-5 text-sm">
            <code>glass-strong</code>: form, khối cần đọc kỹ
          </div>
          <div className="glass-input rounded-control p-5 text-sm">
            <code>glass-input</code>: ô nhập, nút phụ
          </div>
        </div>
      </Section>

      <Section title="Nút">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button loading>Đang lưu</Button>
          <Button disabled>Disabled</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </div>
      </Section>

      <Section title="Form">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Email" placeholder="ban@example.com" />
          <TextField label="Mật khẩu" type="password" hint="Ít nhất 10 ký tự." />
          <TextField label="Có lỗi" defaultValue="abc" error="Email không hợp lệ" />
          <TextField label="Disabled" disabled defaultValue="Không sửa được" />
          <Select
            label="Năm sinh"
            placeholder="Chọn năm"
            defaultValue=""
            options={['2018', '2017', '2016'].map((y) => ({ value: y, label: y }))}
          />
        </div>
        <Checkbox label="Chỉ tài khoản đang khóa" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
      </Section>

      <Section title="Hộp thoại">
        <div>
          <Button variant="danger" onClick={() => setDialogOpen(true)}>
            Mở hộp thoại xác nhận
          </Button>
        </div>
        <Dialog
          open={dialogOpen}
          title="Xóa Bé An?"
          onClose={() => setDialogOpen(false)}
          actions={
            <>
              <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                Hủy
              </Button>
              <Button variant="danger" onClick={() => setDialogOpen(false)}>
                Xóa
              </Button>
            </>
          }
        >
          Thông tin của con sẽ bị xóa khỏi tài khoản và không thể khôi phục.
        </Dialog>
      </Section>

      <Section title="Thông báo và nhãn">
        <Alert tone="info">Chính sách mới sẽ có hiệu lực trong 60 giây.</Alert>
        <Alert tone="success" title="Đã lưu">
          Quota của con đã được cập nhật.
        </Alert>
        <Alert tone="warning">Thiết bị chưa gửi heartbeat 10 phút.</Alert>
        <Alert tone="error">Email hoặc mật khẩu không đúng.</Alert>
        <div className="flex flex-wrap gap-2">
          <Badge>Neutral</Badge>
          <Badge tone="brand">Brand</Badge>
          <Badge tone="success">Hoạt động</Badge>
          <Badge tone="warning">Sắp hết giờ</Badge>
          <Badge tone="danger">Đang khóa</Badge>
        </div>
        <div className="flex items-center gap-4">
          <Spinner size="sm" />
          <Spinner />
          <Spinner size="lg" />
        </div>
      </Section>

      <Card title="Bảng" description="Card có tiêu đề, mô tả và vùng thao tác." actions={<Button size="sm">Thêm</Button>}>
        <Table>
          <TableHead>
            <tr>
              <Th>Tên</Th>
              <Th>Trạng thái</Th>
              <Th className="text-right">Đã dùng</Th>
            </tr>
          </TableHead>
          <TableBody>
            <TableRow>
              <Td className="font-medium">An</Td>
              <Td>
                <Badge tone="success">Đang dùng</Badge>
              </Td>
              <Td className="text-right">1 giờ 20 phút</Td>
            </TableRow>
            <TableRow>
              <Td className="font-medium">Bình</Td>
              <Td>
                <Badge tone="danger">Hết giờ</Badge>
              </Td>
              <Td className="text-right">3 giờ</Td>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
