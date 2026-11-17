# Design system của OGK Dashboard

Phong cách kính mờ (glassmorphism), tông xanh dương nhạt. Viết bằng Tailwind CSS v4, không dùng thư viện UI.

Xem toàn bộ component: `npm run dev` rồi mở `/design`. Trang này không có trong bản build.

## Tệp

| Tệp | Nội dung |
| :---- | :---- |
| `src/shared/styles/tokens.css` | Token trong `@theme` và các lớp bề mặt kính |
| `src/app/index.css` | Nạp Tailwind, nền gradient, style gốc |
| `src/shared/components/` | Component dùng chung, import qua `index.ts` |
| `src/shared/utils/cn.ts` | Ghép class có điều kiện |

## Token

Mỗi biến trong `@theme` sinh class Tailwind cùng tên, ví dụ `--color-brand-500` thành `bg-brand-500`, `text-brand-500`.

| Nhóm | Token | Dùng cho |
| :---- | :---- | :---- |
| Màu chính | `brand-50` đến `brand-900` | Nút chính, link, focus, viền nhấn |
| Chữ | `ink`, `ink-muted`, `ink-subtle` | Chữ chính, chữ phụ, placeholder |
| Trạng thái | `emerald`, `amber`, `rose` của Tailwind | Thành công, cảnh báo, lỗi |
| Bo góc | `rounded-glass` (20px), `rounded-control` (12px) | Thẻ; nút và ô nhập |
| Bóng | `shadow-glass`, `shadow-control`, `shadow-control-hover` | Thẻ kính; nút chính |

## Bề mặt kính

| Lớp | Dùng cho |
| :---- | :---- |
| `glass` | Thẻ, header |
| `glass-strong` | Form đăng nhập, khối cần đọc kỹ |
| `glass-input` | Ô nhập, nút phụ |

Trình duyệt không hỗ trợ `backdrop-filter`, hoặc người dùng bật giảm trong suốt (`prefers-reduced-transparency`), thì các lớp này chuyển sang nền trắng gần đục để chữ vẫn đủ tương phản.

## Component

| Component | Props chính |
| :---- | :---- |
| `Button` | `variant`: primary, secondary, ghost, danger; `size`: sm, md, lg; `loading`; `block` |
| `TextField` | `label`, `hint`, `error`; còn lại như `<input>` |
| `Checkbox` | `label`; còn lại như `<input type="checkbox">` |
| `Card` | `title`, `description`, `actions`, `strong` |
| `Alert` | `tone`: info, success, warning, error; `title` |
| `Badge` | `tone`: neutral, brand, success, warning, danger |
| `Table`, `TableHead`, `TableBody`, `TableRow`, `Th`, `Td` | Bảng cuộn ngang trên điện thoại |
| `Spinner` | `size`: sm, md, lg; `label` cho trình đọc màn hình |

## Quy tắc

- Feature chỉ dùng component trong `shared/components`, không tự viết lại nút hay ô nhập.
- Trang gồm tiêu đề `h1` (`text-2xl font-bold tracking-tight text-ink sm:text-3xl`), mô tả `text-ink-muted`, rồi các `Card`.
- Chữ trên kính dùng `ink` hoặc `ink-muted`; không dùng chữ nhạt hơn `ink-subtle`.
- Bố cục phải dùng được ở chiều rộng 375px.
