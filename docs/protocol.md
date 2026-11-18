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
| `device` | Ghép đôi bằng mã của phụ huynh (mục Thiết bị và ghép đôi) | Gọi API dưới `/api/device/` bằng access token thiết bị |
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
| `POST /api/pairing-codes` | 10 request |
| `POST /api/enroll` | 10 request |
| `POST /api/device/token/refresh` | 30 request |

### Phiên

- Phiên lưu ở bảng `sessions` của server; server chỉ lưu SHA-256 của token phiên.
- Cookie `ogk_session`: `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=43200`.
- Phiên hết hạn tuyệt đối sau 12 giờ kể từ lúc đăng nhập.
- Đăng nhập tạo token mới và xóa phiên cũ trong cookie nếu có. Đăng xuất xóa phiên ở server, cookie cũ không dùng lại được.

### CSRF

- Server đặt cookie `ogk_csrf` (`Secure; SameSite=Lax; Path=/`, không HttpOnly) cho mọi response khi request chưa có cookie này.
- Mọi request `POST`, `PUT`, `PATCH`, `DELETE` dưới `/api` phải có header `X-CSRF-Token` bằng giá trị cookie `ogk_csrf`, kể cả đăng nhập và đăng ký. Thiếu hoặc sai thì trả 403 `csrf_failed`.
- Đăng nhập, đăng ký và đăng xuất cấp giá trị `ogk_csrf` mới.
- Các đường của agent dùng token thiết bị, không dùng cookie, nên được miễn kiểm tra CSRF: mọi đường bắt đầu bằng `/api/enroll` hoặc `/api/device/`. Không đặt đường dùng cookie dưới hai tiền tố này. Các đường của phụ huynh như `/api/pairing-codes` và `/api/devices` vẫn cần CSRF.

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

Một phụ huynh có nhiều trẻ và nhiều thiết bị. Trẻ gắn với thiết bị qua tài khoản Windows: mỗi tài khoản Windows trên một thiết bị gán cho tối đa một trẻ. Vì vậy một trẻ dùng được nhiều thiết bị, và nhiều trẻ dùng chung được một thiết bị bằng tài khoản Windows riêng. API thiết bị và gán tài khoản Windows ở mục Thiết bị và ghép đôi.

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

### `GET /api/children/{id}/devices`

Các thiết bị còn dùng có ít nhất một tài khoản Windows gán cho trẻ này, sắp theo thời điểm ghép đôi. Mỗi thiết bị kèm mọi tài khoản Windows của nó, kể cả tài khoản của trẻ khác.

| HTTP | Body |
| :---- | :---- |
| 200 | `[Device]` |
| 404 | `not_found` |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

## Thiết bị và ghép đôi

### Luồng

```mermaid
sequenceDiagram
    actor P as Phụ huynh
    participant D as Dashboard
    participant S as OGK-Server
    participant A as Agent (quyền admin)

    P->>D: Tích đồng ý, bấm "Tạo mã"
    D->>S: POST /api/pairing-codes {consent: true}
    S-->>D: 201 {id, code "ABCD-EFGH", expires_in 600}
    Note over S: Lưu SHA-256 của mã, IP và thời điểm đồng ý; xóa mã cũ chưa dùng
    D->>P: Hiện mã và thời gian còn lại
    loop mỗi 3 giây tới khi dùng hoặc hết hạn
        D->>S: GET /api/pairing-codes/{id}
    end
    P->>A: ogk_service enroll, nhập mã
    A->>S: TLS, kiểm tra chứng chỉ bằng ca.crt
    A->>S: POST /api/enroll {code, fingerprint, device_secret, name, accounts}
    Note over S: Đánh dấu mã đã dùng, tạo thiết bị và tài khoản Windows,<br/>ghi bản ghi đồng ý và nhật ký kiểm toán, cấp token
    S-->>A: 201 {device_id, access_token, refresh_token, ...}
    Note over A: Ghim SHA-256 chứng chỉ server vừa thấy;<br/>lưu token và bí mật bằng DPAPI vào agent.db
    D->>S: GET /api/pairing-codes/{id} → used, device_id
    P->>D: Gán từng tài khoản Windows cho một trẻ
    D->>S: PUT /api/devices/{id}/accounts/{account_id}

    loop khi chạy
        A->>S: GET /api/device/me (Bearer access token)
        alt access token còn dưới 60 giây hoặc token_expired
            A->>S: POST /api/device/token/refresh
            S-->>A: cặp token mới, cặp cũ bị thu hồi
        end
    end

    P->>D: Gỡ thiết bị
    D->>S: DELETE /api/devices/{id}
    Note over S: Đặt devices.revoked_at, thu hồi mọi token
    A->>S: GET /api/device/me
    S-->>A: 401 device_revoked
    Note over A: Ghi revoked_at, log ERROR, ngừng gọi API
```

### Mã ghép đôi

- 8 ký tự Crockford base32 (`0-9`, `A-Z` bỏ `I`, `L`, `O`, `U`), hiển thị dạng `XXXX-XXXX`.
- Khi nhận mã, server chuyển chữ hoa, bỏ khoảng trắng và gạch nối, đổi `O` thành `0`, `I` và `L` thành `1`.
- Hết hạn sau 10 phút, dùng một lần. Tạo mã mới thì các mã chưa dùng trước đó của phụ huynh bị xóa.
- Server chỉ lưu SHA-256 của mã. Mã sai, đã dùng và hết hạn đều trả cùng mã lỗi `invalid_code` để không lộ mã nào tồn tại.

### Token thiết bị

| Loại | Thời hạn | Dùng để |
| :---- | :---- | :---- |
| Access token | 15 phút | Header `Authorization: Bearer <token>` cho mọi API dưới `/api/device/` |
| Refresh token | 30 ngày | Lấy cặp token mới qua `POST /api/device/token/refresh` |
| Bí mật thiết bị | Không hết hạn | Agent tự sinh lúc ghép đôi; bắt buộc khi làm mới token |

- Token là chuỗi ngẫu nhiên; server chỉ lưu SHA-256 của token, bí mật thiết bị và fingerprint.
- Mỗi lần làm mới, server thu hồi mọi token đang có của thiết bị rồi cấp cặp mới.
- Dùng lại một refresh token đã thu hồi thì server thu hồi mọi token của thiết bị; agent phải ghép đôi lại.

| HTTP | Mã | Ý nghĩa với agent |
| :---- | :---- | :---- |
| 401 | `invalid_token` | Thiếu, sai hoặc đã thu hồi access token; làm mới token rồi thử lại một lần |
| 401 | `token_expired` | Access token hết hạn; làm mới token rồi thử lại một lần |
| 401 | `device_revoked` | Phụ huynh đã gỡ thiết bị; ngừng gọi API |
| 401 | `invalid_refresh` | Refresh token hoặc bí mật thiết bị sai, hết hạn hoặc bị dùng lại; ngừng gọi API |

### Ghim chứng chỉ

- `config.json` của agent có `ca_cert`; mọi kết nối đều kiểm tra chứng chỉ server theo CA này.
- Lúc ghép đôi, agent lưu SHA-256 của chứng chỉ server (dạng DER) thấy trên kết nối đã qua kiểm tra CA.
- Sau đó mọi kết nối phải có đúng chứng chỉ đó. Kiểm tra chạy ngay sau bắt tay TLS, trước khi gửi byte HTTP nào, nên token không bao giờ tới server có chứng chỉ khác.
- Đổi chứng chỉ server (ví dụ chạy lại `gen_certs.sh`) thì agent từ chối kết nối và phải ghép đôi lại.

### Đồng ý của phụ huynh

Phụ huynh tích ô đồng ý trên dashboard trước khi tạo mã. Server lưu thời điểm và IP lúc tạo mã; khi ghép đôi thành công, server ghi một dòng `consent_records` gồm tài khoản phụ huynh, thiết bị, thời điểm, IP và phiên bản nội dung đồng ý.

### Nhật ký kiểm toán

| Thao tác | `action` | `target_type` | Giá trị ghi |
| :---- | :---- | :---- | :---- |
| Ghép đôi | `create` | `device` | `{name}` mới; người thực hiện là phụ huynh tạo mã, IP là IP của agent |
| Gán tài khoản Windows | `update` | `windows_account` | `{child_id}` cũ và mới; gán lại cùng trẻ không ghi |
| Gỡ thiết bị | `delete` | `device` | `{name}` cũ |

### Đối tượng PairingCode

```json
{ "id": 5, "code": "7KQ2-M9XD", "expires_at": "2026-11-18T10:25:00Z", "expires_in": 600 }
```

`expires_in` là số giây còn lại lúc tạo; dashboard đếm ngược từ giá trị này thay vì so `expires_at` với đồng hồ của trình duyệt.

### Đối tượng Device

```json
{
  "id": 4,
  "name": "PC-PHONG-KHACH",
  "created_at": "2026-11-18T10:16:00Z",
  "last_seen_at": "2026-11-18T10:30:00Z",
  "accounts": [{ "id": 9, "sid": "S-1-5-21-1-1001", "username": "an", "child_id": 3 }]
}
```

`last_seen_at` là `null` khi agent chưa gọi API lần nào. `accounts` sắp theo `username` không phân biệt hoa thường; `child_id` là `null` khi chưa gán. Thiết bị đã gỡ không xuất hiện trong mọi API của phụ huynh.

### `POST /api/pairing-codes`

Vai trò `parent`. Cần CSRF.

```json
{ "consent": true }
```

| HTTP | Body |
| :---- | :---- |
| 201 | PairingCode |
| 422 | `consent_required` |
| 401 | `not_authenticated` |
| 403 | `forbidden`, `csrf_failed` |
| 429 | `rate_limited` |

### `GET /api/pairing-codes/{id}`

Vai trò `parent`.

```json
{ "id": 5, "status": "used", "expires_at": "2026-11-18T10:25:00Z", "device_id": 4 }
```

`status` là `pending`, `used` hoặc `expired`. `device_id` chỉ có khi `used`.

| HTTP | Body |
| :---- | :---- |
| 200 | Trạng thái mã |
| 404 | `not_found` (không có, của phụ huynh khác, hoặc đã bị mã mới thay) |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

### `POST /api/enroll`

Agent gọi, không cần phiên hay CSRF.

```json
{
  "code": "7KQ2-M9XD",
  "fingerprint": "<SHA-256 hex của MachineGuid>",
  "device_secret": "<chuỗi ngẫu nhiên, 32 đến 128 ký tự>",
  "name": "PC-PHONG-KHACH",
  "accounts": [{ "sid": "S-1-5-21-1-1001", "username": "an" }]
}
```

`name` bị cắt còn 64 ký tự; rỗng thì dùng `Windows PC`. `accounts` tối đa 64 phần tử; SID trùng chỉ lấy lần đầu.

| HTTP | Body |
| :---- | :---- |
| 201 | `{ "device_id": 4, "access_token": "...", "access_expires_at": "...", "refresh_token": "...", "refresh_expires_at": "..." }` |
| 400 | `invalid_code` |
| 422 | Body sai kiểu hoặc sai độ dài (mặc định của FastAPI) |
| 429 | `rate_limited` |

### `POST /api/device/token/refresh`

```json
{ "device_id": 4, "refresh_token": "...", "device_secret": "..." }
```

| HTTP | Body |
| :---- | :---- |
| 200 | Giống 201 của `POST /api/enroll` |
| 401 | `invalid_refresh`, `device_revoked` |
| 429 | `rate_limited` |

### `GET /api/device/me`

Access token thiết bị. Dùng để kiểm tra token và cập nhật `last_seen_at`.

| HTTP | Body |
| :---- | :---- |
| 200 | `{ "id": 4, "name": "PC-PHONG-KHACH" }` |
| 401 | `invalid_token`, `token_expired`, `device_revoked` |

### `GET /api/devices`

Vai trò `parent`. Các thiết bị còn dùng của phụ huynh, sắp theo thời điểm ghép đôi.

| HTTP | Body |
| :---- | :---- |
| 200 | `[Device]` |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

### `PUT /api/devices/{id}/accounts/{account_id}`

Vai trò `parent`. Cần CSRF. Gán tài khoản Windows cho một trẻ, hoặc bỏ gán với `null`. Trẻ phải cùng phụ huynh với thiết bị.

```json
{ "child_id": 3 }
```

| HTTP | Body |
| :---- | :---- |
| 200 | `{ "id": 9, "sid": "...", "username": "an", "child_id": 3 }` |
| 404 | `not_found` (thiết bị không có, của người khác, đã gỡ, hoặc tài khoản không thuộc thiết bị), `child_not_found` |
| 401 | `not_authenticated` |
| 403 | `forbidden`, `csrf_failed` |

### `DELETE /api/devices/{id}`

Vai trò `parent`. Cần CSRF. Gỡ thiết bị: đặt `revoked_at`, thu hồi mọi token. Agent nhận `device_revoked` ở request tiếp theo.

| HTTP | Body |
| :---- | :---- |
| 204 | Không có |
| 404 | `not_found` (không có, của người khác, hoặc đã gỡ) |
| 401 | `not_authenticated` |
| 403 | `forbidden`, `csrf_failed` |
