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
| `admin` | Lệnh `python -m app.cli create-admin <email>` trên máy chủ | Mở khóa tài khoản phụ huynh; không đọc dữ liệu của trẻ |
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
