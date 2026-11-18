# Giao thức OGK

Đặc tả API giữa OGK-Server, dashboard và agent. Mọi API nằm dưới `/api`, chỉ phục vụ qua HTTPS. Body request và response là JSON.

## Quy ước chung

### Lỗi

Mọi lỗi trả về body dạng:

```json
{ "detail": "<mã lỗi>" }
```

Một số lỗi có thêm trường riêng, ghi ở từng endpoint. `detail` là mã máy đọc được; dashboard tự dịch sang tiếng Việt.

| HTTP | Mã | Ý nghĩa |
| :---- | :---- | :---- |
| 401 | `not_authenticated` | Không có phiên, phiên hết hạn hoặc đã đăng xuất |
| 403 | `csrf_failed` | Request ghi thiếu hoặc sai CSRF token |
| 403 | `forbidden` | Đúng phiên nhưng sai vai trò |
| 404 | `not_found` | Không có đối tượng, hoặc đối tượng không thuộc người gọi |
| 429 | `rate_limited` | Vượt giới hạn tần suất theo IP; có header `Retry-After` (giây) |

Đối tượng của người khác luôn trả 404, không trả 403, để không lộ việc đối tượng tồn tại.

### Thời gian

Mọi mốc thời gian là chuỗi ISO 8601 theo UTC, ví dụ `2026-11-17T10:15:00Z`.

## Xác thực

### Vai trò

| Vai trò | Cách tạo | Quyền |
| :---- | :---- | :---- |
| `parent` | Tự đăng ký trên dashboard | Quản lý dữ liệu của chính mình |
| `admin` | Lệnh `python -m app.cli create-admin <email>` trên máy chủ | Mở khóa tài khoản phụ huynh; không đọc dữ liệu của trẻ (mọi API `/api/children` trả 403) |
| `child-view` | Token thiết bị (P18) | Chỉ đọc dữ liệu của trẻ đang đăng nhập Windows |

### Mật khẩu và khóa tài khoản

- Mật khẩu dài 10 đến 256 ký tự, băm bằng Argon2id.
- Email được bỏ khoảng trắng hai đầu và chuyển về chữ thường.
- Sai mật khẩu 5 lần liên tiếp thì tài khoản bị khóa 15 phút. Trong thời gian khóa, đăng nhập đúng mật khẩu vẫn bị từ chối.
- Đăng nhập đúng thì bộ đếm sai về 0. Admin mở khóa thì bộ đếm về 0 và hết khóa ngay.

### Giới hạn tần suất

Đếm theo IP trong cửa sổ trượt 60 giây, tính cả request thành công.

| Endpoint | Giới hạn |
| :---- | :---- |
| `POST /api/auth/login` | 10 request |
| `POST /api/auth/register` | 5 request |

### Phiên

- Phiên lưu ở bảng `sessions` của server; server chỉ lưu SHA-256 của token phiên.
- Cookie `ogk_session`: `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=43200`.
- Phiên hết hạn tuyệt đối sau 12 giờ kể từ lúc đăng nhập.
- Đăng nhập tạo token mới và xóa phiên cũ trong cookie nếu có. Đăng xuất xóa phiên ở server, cookie cũ không dùng lại được.

### CSRF

- Server đặt cookie `ogk_csrf` (`Secure; SameSite=Lax; Path=/`, không HttpOnly) cho mọi response khi request chưa có cookie này.
- Mọi request `POST`, `PUT`, `PATCH`, `DELETE` dưới `/api` phải có header `X-CSRF-Token` bằng giá trị cookie `ogk_csrf`, kể cả đăng nhập và đăng ký. Thiếu hoặc sai thì trả 403 `csrf_failed`.
- Đăng nhập, đăng ký và đăng xuất cấp giá trị `ogk_csrf` mới.
- Các đường của agent dùng token thiết bị, không dùng cookie, được miễn kiểm tra CSRF (thêm ở P8).

### Đối tượng Account

```json
{ "id": 1, "email": "me@example.com", "role": "parent" }
```

### `POST /api/auth/register`

Tạo tài khoản `parent` và đăng nhập luôn.

Request:

```json
{ "email": "me@example.com", "password": "mat-khau-dai" }
```

| HTTP | Body |
| :---- | :---- |
| 201 | Account; đặt cookie `ogk_session` và `ogk_csrf` mới |
| 409 | `email_taken` |
| 422 | `invalid_email`, `password_too_short`, `password_too_long` |
| 403 | `csrf_failed` |
| 429 | `rate_limited` |

### `POST /api/auth/login`

Request giống đăng ký.

| HTTP | Body |
| :---- | :---- |
| 200 | Account; đặt cookie `ogk_session` và `ogk_csrf` mới |
| 401 | `invalid_credentials` (sai email hoặc mật khẩu, không phân biệt) |
| 423 | `account_locked`, kèm `"locked_until": "<thời điểm>"`; trả ngay ở lần sai thứ 5 |
| 403 | `csrf_failed` |
| 429 | `rate_limited` |

### `POST /api/auth/logout`

Không có body.

| HTTP | Body |
| :---- | :---- |
| 204 | Không có; xóa cookie `ogk_session`, đặt `ogk_csrf` mới |
| 401 | `not_authenticated` |
| 403 | `csrf_failed` |

### `GET /api/auth/me`

| HTTP | Body |
| :---- | :---- |
| 200 | Account |
| 401 | `not_authenticated` |

## Admin

Mọi endpoint dưới `/api/admin` cần phiên vai trò `admin`: không có phiên trả 401, sai vai trò trả 403 `forbidden`.

### Đối tượng AdminAccount

```json
{ "id": 2, "email": "me@example.com", "failed_attempts": 0, "locked_until": "2026-11-17T10:15:00Z" }
```

`locked_until` là `null` khi không bị khóa.

### `GET /api/admin/accounts?locked=true`

Danh sách tài khoản `parent`, sắp theo email. `locked=true` chỉ lấy tài khoản đang bị khóa; mặc định `false` lấy tất cả.

| HTTP | Body |
| :---- | :---- |
| 200 | `[AdminAccount]` |

### `POST /api/admin/accounts/{id}/unlock`

Mở khóa tài khoản `parent`.

| HTTP | Body |
| :---- | :---- |
| 200 | AdminAccount sau khi mở khóa |
| 404 | `not_found` (không có hoặc không phải tài khoản `parent`) |
| 403 | `csrf_failed`, `forbidden` |

## Gia đình

### Mô hình dữ liệu

Một phụ huynh có nhiều trẻ và nhiều thiết bị. Trẻ gắn với thiết bị qua tài khoản Windows: mỗi tài khoản Windows trên một thiết bị gán cho tối đa một trẻ. Vì vậy một trẻ dùng được nhiều thiết bị, và nhiều trẻ dùng chung được một thiết bị bằng tài khoản Windows riêng. API thiết bị và gán tài khoản Windows có ở P8.

| Bảng | Cột chính |
| :---- | :---- |
| `children` | `owner_id` (phụ huynh), `name`, `birth_year` |
| `devices` | `owner_id` (phụ huynh), `name` |
| `windows_accounts` | `device_id`, `child_id` (có thể rỗng), `sid`, `username` |

Xóa trẻ thì tài khoản Windows đang gán cho trẻ được bỏ gán (`child_id` về rỗng), thiết bị giữ nguyên.

### Mã hóa khi lưu

- `children.name`, `children.birth_year`, `windows_accounts.username` được mã hóa AES-256-GCM trước khi ghi DB.
- Mỗi giá trị lưu dạng `0x01 (phiên bản) || nonce 12 byte ngẫu nhiên || bản mã kèm tag 16 byte`. AAD là `<bảng>.<cột>` nên không chép được bản mã từ cột này sang cột khác.
- Khóa 32 byte đọc từ biến môi trường `OGK_DATA_KEY` (base64url), sinh bằng `python -m app.cli gen-data-key`. Thiếu hoặc sai độ dài thì server không khởi động. Khóa không nằm trong mã nguồn hay DB; mất khóa thì không đọc lại được các trường trên.

### Quyền

- Mọi endpoint dưới `/api/children` cần phiên vai trò `parent`: không có phiên trả 401, vai trò `admin` trả 403 `forbidden`.
- Truy vấn luôn lọc theo phụ huynh đang đăng nhập. Trẻ của phụ huynh khác trả 404 `not_found`, giống trẻ không tồn tại.
- Request ghi cần header `X-CSRF-Token` như mọi API khác.

### Đối tượng Child

```json
{
  "id": 3,
  "name": "Bé An",
  "birth_year": 2017,
  "created_at": "2026-11-17T10:15:00Z",
  "updated_at": "2026-11-17T10:15:00Z"
}
```

| Trường | Ràng buộc |
| :---- | :---- |
| `name` | Bỏ khoảng trắng hai đầu, dài 1 đến 64 ký tự; sai thì 422 `invalid_name` |
| `birth_year` | Số nguyên từ 2000 đến năm hiện tại (UTC); sai thì 422 `invalid_birth_year` |

Body sai kiểu (ví dụ `birth_year` không phải số) trả 422 với `detail` dạng mảng theo mặc định của FastAPI.

### `GET /api/children`

Danh sách trẻ của phụ huynh, sắp theo tên không phân biệt hoa thường.

| HTTP | Body |
| :---- | :---- |
| 200 | `[Child]` |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

### `POST /api/children`

Request:

```json
{ "name": "Bé An", "birth_year": 2017 }
```

| HTTP | Body |
| :---- | :---- |
| 201 | Child |
| 422 | `invalid_name`, `invalid_birth_year` |
| 401 | `not_authenticated` |
| 403 | `forbidden`, `csrf_failed` |

### `GET /api/children/{id}`

| HTTP | Body |
| :---- | :---- |
| 200 | Child |
| 404 | `not_found` |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

### `PATCH /api/children/{id}`

Sửa một phần; trường không gửi giữ nguyên. `updated_at` luôn được cập nhật.

```json
{ "name": "An Nhiên" }
```

| HTTP | Body |
| :---- | :---- |
| 200 | Child sau khi sửa |
| 404 | `not_found` |
| 422 | `invalid_name`, `invalid_birth_year` |
| 401 | `not_authenticated` |
| 403 | `forbidden`, `csrf_failed` |

### `DELETE /api/children/{id}`

| HTTP | Body |
| :---- | :---- |
| 204 | Không có |
| 404 | `not_found` |
| 401 | `not_authenticated` |
| 403 | `forbidden`, `csrf_failed` |
