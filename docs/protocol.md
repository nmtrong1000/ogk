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

## Chính sách

Mỗi trẻ có một chính sách. Server ký chính sách bằng Ed25519; agent chỉ áp dụng chính sách có chữ ký đúng. Từ P12, `rules` có quota ngày thường, quota cuối tuần và lịch tuần; từ P13 có thêm luật ứng dụng; các phase sau thêm luật vào `rules`.

### Tài liệu chính sách

Tài liệu được dựng riêng cho từng thiết bị vì `accounts` chỉ chứa SID trên thiết bị đó.

```json
{
  "accounts": ["S-1-5-21-1004336348-1177238915-682003330-1001"],
  "child_id": 7,
  "format": 1,
  "issued_at": "2026-11-18T08:00:00Z",
  "policy_version": 3,
  "rules": {
    "weekday_quota_minutes": 120,
    "weekend_quota_minutes": 180,
    "weekly_schedule": ["000000000000001111111111111111111111111111000000", "... đủ 7 chuỗi ..."],
    "app_rules": [
      { "action": "block", "name": "game.exe", "sha256": null },
      { "action": "block", "name": "notepad.exe", "sha256": "abab...ab (64 ký tự hex)" }
    ],
    "web_allowlist": ["school.edu.vn"],
    "web_blocklist": ["example.com"],
    "blocked_categories": ["adult", "social"],
    "category_domains": {"adult": ["adult.example"]}
  },
  "set_by": "parent@example.com"
}
```

| Trường | Ý nghĩa |
| :---- | :---- |
| `accounts` | SID các tài khoản Windows trên thiết bị đang gán cho trẻ, sắp tăng dần. Agent dùng để biết phiên đang đăng nhập là của trẻ nào; SID không có trong chính sách nào thì không bị áp luật |
| `child_id` | Trẻ được áp chính sách |
| `format` | Phiên bản định dạng tài liệu, hiện là `1` |
| `issued_at` | Thời điểm tạo hoặc đổi chính sách gần nhất; cùng version luôn cùng giá trị nên cùng chữ ký |
| `policy_version` | Bắt đầu từ 1, tăng đúng 1 mỗi lần luật đổi giá trị hoặc danh sách tài khoản gán cho trẻ đổi |
| `rules.weekday_quota_minutes` | Số phút dùng máy mỗi ngày từ thứ Hai đến thứ Sáu, 0 đến 1440, mặc định 120 |
| `rules.weekend_quota_minutes` | Số phút dùng máy mỗi ngày thứ Bảy và Chủ nhật, 0 đến 1440, mặc định 120 |
| `rules.weekly_schedule` | Lịch tuần: mảng 7 chuỗi, chuỗi 0 là thứ Hai, chuỗi 6 là Chủ nhật. Mỗi chuỗi 48 ký tự; ký tự thứ k là ô 30 phút [k x 30 phút, (k + 1) x 30 phút) theo giờ địa phương của máy trẻ; `1` là được dùng, `0` là khóa. Mặc định 07:00 đến 21:00 mỗi ngày |
| `rules.app_rules` | Luật ứng dụng: mảng tối đa 200 object, sắp theo `name`, rồi `sha256` (null trước), rồi `action`. `name` là tên tệp thực thi chữ thường, 1 đến 255 ký tự, không chứa `/` hay `\`; `sha256` là SHA-256 của tệp thực thi dạng 64 ký tự hex chữ thường, hoặc `null` nếu chỉ so theo tên; `action` là `block` hoặc `allow`. Mỗi cặp (`name`, `sha256`) có tối đa một luật. Mặc định `[]`. Cách áp xem [Kiểm soát ứng dụng](#kiểm-soát-ứng-dụng) |
| `rules.web_allowlist` | Danh sách tên miền miễn chặn của gia đình; khớp chính xác hoặc mọi tên miền con. Danh sách này luôn thắng luật chặn. Mặc định `[]`. |
| `rules.web_blocklist` | Danh sách tên miền bị chặn của gia đình; khớp chính xác hoặc mọi tên miền con. Mặc định `[]`. |
| `rules.blocked_categories` | Các nhóm bị chặn: `education`, `entertainment`, `social`, `games`, `adult`, `unclassified`. Mặc định cho trẻ 6 đến 11 tuổi là `adult` và `social`. |
| `rules.category_domains` | Bảng phân loại dùng chung được ký cùng chính sách; khóa là tên nhóm, giá trị là mảng tên miền chuẩn hóa. Thay đổi bảng phân loại làm tăng version chính sách. |
| `set_by` | Email phụ huynh sửa chính sách gần nhất, hiện trên Tray UI khi khóa hoặc chặn ứng dụng; chuỗi rỗng nếu tài khoản đã bị xóa |

Ngày thường hay cuối tuần và ô của lịch tính theo giờ tin cậy của agent (xem [Quản lý thời gian](#quản-lý-thời-gian)), không theo giờ hệ thống.

### JSON chuẩn hóa

Chữ ký tính trên bytes của tài liệu ở dạng chuẩn hóa:

- Khóa của mọi object sắp xếp tăng dần theo code point.
- Không có khoảng trắng: phân cách là `,` và `:`.
- Chuỗi giữ nguyên ký tự ngoài ASCII; chỉ escape `"`, `\` và ký tự điều khiển theo JSON.
- Chỉ có số nguyên, chuỗi, `true`, `false`, `null`, mảng và object. Số thực bị từ chối vì mỗi thư viện in số thực khác nhau.
- Mã hóa UTF-8.

Trong Python, cách chuẩn hóa này tương đương `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()` cộng với bước từ chối số thực. Tài liệu ở ví dụ trên (đủ 7 chuỗi lịch giống nhau, `sha256` là `ab` lặp 32 lần) chuẩn hóa thành:

```text
{"accounts":["S-1-5-21-1004336348-1177238915-682003330-1001"],"child_id":7,"format":1,"issued_at":"2026-11-18T08:00:00Z","policy_version":3,"rules":{"app_rules":[{"action":"block","name":"game.exe","sha256":null},{"action":"block","name":"notepad.exe","sha256":"abab...ab"}],"weekday_quota_minutes":120,"weekend_quota_minutes":180,"weekly_schedule":["000000000000001111111111111111111111111111000000",...]},"set_by":"parent@example.com"}
```

Dạng đầy đủ là `valid[0].canonical` trong `docs/test_vectors.json`.

### Chữ ký và khóa

- Chữ ký là Ed25519 trên bytes chuẩn hóa, mã hóa base64url không có `=`.
- `key_id` là 16 ký tự hex đầu của SHA-256 trên 32 byte khóa công khai thô. Agent dùng nó để ghi log, không dùng để chọn khóa.
- Khóa bí mật là tệp PEM PKCS8 do `python -m app.cli gen-policy-key` tạo, đường dẫn trong `OGK_POLICY_SIGNING_KEY`. Server từ chối khởi động nếu thiếu tệp hoặc nhóm và người khác đọc được tệp (cần `chmod 600`).
- Khóa công khai `policy_public.pem` đi cùng bộ cài agent: `install.ps1 -PolicyPublicKey` chép vào thư mục dữ liệu và ghi `policy_public_key` trong `config.json`.
- `docs/test_vectors.json` có khóa chỉ dùng cho test, tài liệu mẫu, dạng chuẩn hóa và chữ ký đúng, các ca sai chữ ký (`invalid`) và các ca đúng chữ ký nhưng sai luật (`invalid_rules`). Test của server và agent cùng đọc tệp này. Với khóa test, tài liệu ở ví dụ trên có chữ ký `-5r2Fsh0Om0X4CA5UIis5S5-PwEewAdPuil1kSRyRWAiYWBcD_t38_O8MThuPWaY6Pu7hj_NYa0mDC6e-qK1Bw`.

### Agent kiểm tra và lưu

- Agent kiểm tra chữ ký từng chính sách trước khi lưu. Một chính sách sai chữ ký làm cả lô bị từ chối, agent giữ bản đang có.
- Chữ ký đúng nhưng `accounts` không phải mảng chuỗi, `set_by` không phải chuỗi, quota ngoài 0 đến 1440, lịch không đúng 7 x 48 ký tự `0`/`1`, hoặc `app_rules` không phải mảng hay có luật sai định dạng ở trên cũng làm cả lô bị từ chối. Thiếu `app_rules` thì agent hiểu là `[]`: chính sách ký từ trước P13 không có trường này, vẫn nạp được và giữ nguyên quota cùng lịch; vector `pre_p13_without_app_rules` kiểm tra trường hợp này.
- Agent từ chối chính sách có `policy_version` thấp hơn bản đang giữ của cùng trẻ.
- Agent lưu tài liệu chuẩn hóa và chữ ký trong DB cục bộ, kiểm tra lại chữ ký mỗi lần nạp. Dòng bị sửa thì bị bỏ qua và ghi log.
- Trẻ không còn trong response thì agent xóa chính sách của trẻ đó.

### Nhật ký kiểm toán chính sách

| Thao tác | `action` | `target_type` | Giá trị ghi |
| :---- | :---- | :---- | :---- |
| Sửa chính sách | `update` | `policy` | Các trường luật đã đổi cộng `policy_version`, cũ và mới; `weekly_schedule` ghi dạng 336 ký tự liền; `app_rules` ghi cả danh sách cũ và mới. `target_id` là id của trẻ; sửa mà giá trị không đổi thì không ghi |

Gán hoặc bỏ gán tài khoản Windows tăng version chính sách của trẻ bị ảnh hưởng nhưng chỉ ghi nhật ký `windows_account` như trước.

### Đối tượng Policy

```json
{
  "child_id": 7,
  "policy_version": 3,
  "weekday_quota_minutes": 120,
  "weekend_quota_minutes": 180,
  "weekly_schedule": ["000000000000001111111111111111111111111111000000", "... đủ 7 chuỗi ..."],
  "app_rules": [{ "action": "block", "name": "game.exe", "sha256": null }],
  "web_allowlist": [],
  "web_blocklist": [],
  "blocked_categories": ["adult", "social"],
  "set_by": "parent@example.com",
  "updated_at": "2026-11-18T08:00:00Z"
}
```

`set_by` là `null` nếu tài khoản đã bị xóa.

### `GET /api/children/{id}/policy`

Vai trò `parent`. Trẻ chưa có chính sách thì server tạo chính sách mặc định, version 1, người đặt là chủ của trẻ.

| HTTP | Body |
| :---- | :---- |
| 200 | Policy |
| 404 | `not_found` |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

### `PATCH /api/children/{id}/policy`

Vai trò `parent`. Mọi trường đều tùy chọn; trường bỏ trống giữ nguyên. Có ít nhất một giá trị khác hiện tại thì version tăng 1, có một ảnh chụp version mới và một dòng nhật ký kiểm toán. Một trường sai thì cả request bị từ chối.

```json
{
  "weekday_quota_minutes": 90,
  "weekend_quota_minutes": 150,
  "weekly_schedule": ["000000000000001111111111111111111111111111000000", "... đủ 7 chuỗi ..."],
  "app_rules": [{ "name": "Game.exe", "sha256": null, "action": "block" }],
  "web_allowlist": ["school.edu.vn"],
  "web_blocklist": ["example.com"],
  "blocked_categories": ["adult", "social"]
}
```

`app_rules` thay cả danh sách; gửi `[]` để xóa hết. Server bỏ khoảng trắng hai đầu, đổi `name` và `sha256` sang chữ thường rồi sắp xếp, nên danh sách chỉ khác thứ tự hoặc hoa thường không làm tăng version. `sha256` bỏ trống được coi là `null`.

`web_allowlist` và `web_blocklist` thay toàn bộ danh sách tương ứng. Tên miền được đổi về chữ thường, bỏ dấu chấm cuối và sắp xếp; tối đa 1000 tên miền hợp lệ. Luật khớp cả tên miền con. Luật miễn chặn luôn thắng luật chặn. `blocked_categories` thay toàn bộ nhóm bị chặn; tên miền trong nhóm bị chặn đều chịu luật này.

| HTTP | Body |
| :---- | :---- |
| 200 | Policy sau khi sửa |
| 404 | `not_found` |
| 422 | `invalid_quota`, `invalid_schedule`, `invalid_app_rules`, `invalid_domain_rules`, `invalid_blocked_categories` |
| 401 | `not_authenticated` |
| 403 | `forbidden`, `csrf_failed` |

### `GET /api/children/{id}/policy/versions`

Vai trò `parent`. Trả tối đa 50 version gần nhất, mới nhất trước.

### `GET /api/children/{id}/webfilter/categories`

Vai trò `parent`. Xác nhận trẻ thuộc phụ huynh gọi API rồi trả danh sách sáu nhóm phân loại.

### API admin sửa bảng phân loại

`GET /api/admin/webfilter/catalog` trả danh sách tên miền và nhóm. `PUT /api/admin/webfilter/catalog/{domain}` nhận `{"category":"education"}` để thêm hoặc đổi nhóm, hoặc `{"category":null}` để xóa. Vai trò `admin` bắt buộc; sửa đổi được ghi nhật ký kiểm toán và tăng version các chính sách đã tạo. Bảng không được giảm xuống dưới 200 tên miền.

```json
[
  {
    "policy_version": 3,
    "weekday_quota_minutes": 120,
    "weekend_quota_minutes": 180,
    "weekly_schedule": ["... 7 chuỗi ..."],
    "app_rules": [],
    "set_by": "parent@example.com",
    "created_at": "2026-11-18T08:00:00Z"
  }
]
```

| HTTP | Body |
| :---- | :---- |
| 200 | Như trên |
| 404 | `not_found` |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

### `GET /api/device/policy`

Access token thiết bị. Trả chính sách đã ký của mọi trẻ được gán cho ít nhất một tài khoản Windows trên thiết bị, mỗi trẻ một lần, sắp theo `child_id`. Thiết bị chưa gán trẻ nào nhận danh sách rỗng.

```json
{
  "policies": [
    {
      "policy": { "accounts": ["..."], "child_id": 7, "format": 1, "...": "như tài liệu chính sách" },
      "signature": "-5r2Fsh0Om0X4CA5UIis5S5-PwEewAdPuil1kSRyRWAiYWBcD_t38_O8MThuPWaY6Pu7hj_NYa0mDC6e-qK1Bw",
      "key_id": "1bf6796e61f6125c"
    }
  ]
}
```

| HTTP | Body |
| :---- | :---- |
| 200 | Như trên |
| 401 | `invalid_token`, `token_expired`, `device_revoked` |

## Đồng bộ

Agent gọi heartbeat mỗi 60 giây. Heartbeat mang trạng thái thiết bị và cảnh báo; server trả `policy_version` mới nhất của từng trẻ, lệnh chờ và giờ server. Version nào trên server cao hơn bản agent đang giữ, hoặc có trẻ mới, thì agent gọi `GET /api/device/policy`. Sự kiện đi riêng qua `POST /api/device/events` theo lô.

### Sự kiện

Mỗi sự kiện có đúng 7 trường. Thiếu trường, thừa trường hoặc sai kiểu thì cả lô bị từ chối.

```json
{
  "ts": "2026-11-19T08:00:00Z",
  "device_id": 3,
  "child_id": 7,
  "type": "blocked_domain",
  "subject": "youtube.com",
  "duration_sec": 0,
  "policy_id": 4
}
```

| Trường | Ý nghĩa |
| :---- | :---- |
| `ts` | Thời điểm xảy ra, dạng `YYYY-MM-DDTHH:MM:SSZ` |
| `device_id` | Thiết bị ghi sự kiện; phải là thiết bị đang gọi |
| `child_id` | Trẻ đang dùng máy; phải là trẻ của cùng phụ huynh sở hữu thiết bị |
| `type` | Một trong 9 loại ở bảng dưới |
| `subject` | Tên ứng dụng hoặc tên miền cấp hai, không phải URL đầy đủ; 0 đến 255 ký tự, không chứa `/` hay `\`. Với `domain_query` và `blocked_domain` phải là tên miền chữ thường có ít nhất hai nhãn, không có cổng |
| `duration_sec` | Số giây, số nguyên từ 0 đến 86400; sự kiện tức thời ghi 0 |
| `policy_id` | `policy_version` của chính sách đang áp cho trẻ lúc xảy ra; `0` là chính sách mặc định khi mất kết nối |

`device_id`, `child_id`, `duration_sec` và `policy_id` là số nguyên JSON; `true`/`false` không được coi là số.

| `type` | Khi nào |
| :---- | :---- |
| `app_start` | Ứng dụng lên cửa sổ trước; `subject` là tên tệp thực thi chữ thường |
| `app_stop` | Ứng dụng rời cửa sổ trước; `duration_sec` là thời gian ở cửa sổ trước |
| `domain_query` | Trẻ truy cập một tên miền |
| `blocked_app` | Ứng dụng bị chặn và bị kết thúc; `subject` là tên tệp thực thi chữ thường |
| `blocked_domain` | Tên miền bị chặn |
| `quota_warning` | Cảnh báo sắp hết giờ; `subject` là số phút còn lại `"10"`, `"5"` hoặc `"1"`; `duration_sec` là số giây đã dùng hôm nay |
| `locked` | Máy bị khóa; `subject` là `"quota"` (hết quota) hoặc `"schedule"` (ngoài lịch); `duration_sec` là số giây đã dùng hôm nay |
| `unlock_request` | Trẻ xin thêm thời gian |
| `override_granted` | Phụ huynh cho thêm thời gian |

### Cảnh báo thiết bị

Cảnh báo thiết bị không phải sự kiện và không nằm trong bảng sự kiện. Agent gửi cảnh báo đang còn hiệu lực trong mỗi heartbeat.

| `type` | Ý nghĩa |
| :---- | :---- |
| `enforcement_disabled` | Service đã tắt cưỡng chế; `detail` là lý do, ví dụ `tray_unavailable` |
| `clock_tampered` | Giờ hệ thống lệch quá 2 phút so với giờ tin cậy của agent; `detail` là `backward` (lùi) hoặc `forward` (tiến) |

Server giữ tối đa một cảnh báo đang mở cho mỗi cặp thiết bị và loại. Heartbeat có cảnh báo cùng loại thì server cập nhật `last_seen_at` và `detail`; heartbeat không còn loại đó thì server đóng cảnh báo bằng `resolved_at`. Lần sau xuất hiện lại thì mở cảnh báo mới.

### Đối tượng Alert

```json
{
  "id": 12,
  "device_id": 3,
  "device_name": "PC phòng khách",
  "type": "enforcement_disabled",
  "detail": "tray_unavailable",
  "first_seen_at": "2026-11-19T08:00:00Z",
  "last_seen_at": "2026-11-19T08:05:00Z",
  "resolved_at": null
}
```

### `POST /api/device/heartbeat`

Access token thiết bị. Khóa của `quota_used` và `policy_versions` là `child_id` dạng chuỗi. `quota_used` là số giây trẻ đã dùng hôm nay theo bộ đếm của agent; trẻ chưa dùng trên máy này hôm nay có giá trị 0. `alerts` là danh sách cảnh báo đang còn hiệu lực, mỗi loại một lần; danh sách rỗng nghĩa là mọi cảnh báo đã hết.

```json
{
  "status": {
    "uptime": 3600.5,
    "enforcement": { "enabled": false, "reason": "tray_unavailable", "since": "2026-11-19T08:00:00Z" },
    "policy_mode": "cached"
  },
  "quota_used": { "7": 0 },
  "policy_versions": { "7": 3 },
  "alerts": [{ "type": "enforcement_disabled", "detail": "tray_unavailable", "ts": "2026-11-19T08:00:00Z" }]
}
```

Response 200:

```json
{
  "policy_versions": { "7": 4 },
  "commands": [],
  "server_time": "2026-11-19T08:05:00Z"
}
```

`policy_versions` gồm mọi trẻ được gán cho thiết bị, giống danh sách của `GET /api/device/policy`. `commands` luôn rỗng cho tới khi có kênh lệnh. `server_time` là mốc agent dùng để đo thời gian mất kết nối.

| HTTP | Body |
| :---- | :---- |
| 200 | Như trên |
| 422 | Body sai lược đồ (lỗi kiểm tra mặc định của FastAPI) |
| 401 | `invalid_token`, `token_expired`, `device_revoked` |

### `POST /api/device/events`

Access token thiết bị. Header `Idempotency-Key` bắt buộc, 1 đến 64 ký tự `A-Z a-z 0-9 - _`; agent dùng UUID4. Body có 1 đến 500 sự kiện:

```json
{ "events": [ { "ts": "2026-11-19T08:00:00Z", "device_id": 3, "child_id": 7, "type": "app_start", "subject": "minecraft.exe", "duration_sec": 0, "policy_id": 4 } ] }
```

Server lưu khóa đã nhận theo thiết bị cùng cả lô trong một giao dịch. Gửi lại lô với khóa đã nhận thì server không lưu gì và trả `duplicate: true`, nên agent gửi lại sau lỗi mạng không làm sự kiện bị đếm hai lần. Khóa thuộc riêng từng thiết bị.

| HTTP | Body |
| :---- | :---- |
| 200 | `{ "accepted": 1, "duplicate": false }`; lô trùng: `{ "accepted": 0, "duplicate": true }` |
| 400 | `invalid_idempotency_key` (thiếu hoặc sai định dạng) |
| 422 | `invalid_batch` (body không phải object chỉ có `events`, hoặc số sự kiện ngoài 1 đến 500) |
| 422 | `invalid_event`, kèm `index` (vị trí trong lô) và `field` (trường sai; `null` nếu sự kiện không phải object; tên trường lạ nếu thừa trường) |
| 401 | `invalid_token`, `token_expired`, `device_revoked` |

### `GET /api/alerts?device_id=`

Vai trò `parent`. Trả cảnh báo của các thiết bị chưa gỡ thuộc phụ huynh, mới nhất trước theo `last_seen_at`, tối đa 200. `device_id` lọc theo một thiết bị.

| HTTP | Body |
| :---- | :---- |
| 200 | Danh sách Alert |
| 404 | `not_found` (thiết bị không thuộc phụ huynh hoặc đã gỡ) |
| 401 | `not_authenticated` |
| 403 | `forbidden` |

### Mất kết nối và chính sách hết hạn

Agent chọn fail-closed có giới hạn:

- Sự kiện được lưu vào DB cục bộ trước khi gửi. Mỗi lô được gán khóa chống trùng và lưu khóa trước lần gửi đầu, nên gửi lại sau lỗi luôn dùng cùng khóa. Server trả 200 thì agent xóa lô; trả 422 thì agent bỏ lô và ghi log để lô hỏng không chặn hàng đợi.
- Thời gian mất kết nối tính từ heartbeat thành công gần nhất, lấy giá trị lớn hơn giữa hai cách đo: cộng dồn bằng đồng hồ đơn điệu, lưu trong DB cục bộ; và giờ hệ thống trừ `server_time` lần cuối. Lùi giờ hệ thống không làm giảm thời gian đo được, khởi động lại không làm mất, và thời gian tắt máy vẫn được tính.
- Dưới 7 ngày, agent áp chính sách đã ký đang giữ.
- Từ 7 ngày, agent áp `data/default_policy.json` cho mọi trẻ: 120 phút mỗi ngày cả ngày thường và cuối tuần, cho phép 07:00 đến 21:00 mỗi ngày. Agent vẫn dùng `accounts` của chính sách đã ký đang giữ để biết phiên là của trẻ nào. Trẻ chưa có chính sách đã ký nào cũng nhận chính sách mặc định. Heartbeat thành công tiếp theo đưa agent về chính sách đã ký.
- Sự kiện ghi lúc áp chính sách mặc định có `policy_id` là `0`.

Chính sách mặc định đi cùng bộ cài, không ký:

```json
{
  "format": 1,
  "policy_version": 0,
  "rules": {
    "weekday_quota_minutes": 120,
    "weekend_quota_minutes": 120,
    "weekly_schedule": ["000000000000001111111111111111111111111111000000", "... 7 chuỗi ..."],
    "app_rules": []
  }
}
```

`rules` theo đúng định dạng của tài liệu chính sách. Chính sách mặc định không có `accounts` và `set_by`.

## Quản lý thời gian

Service đếm thời gian, quyết định cảnh báo và khóa; Tray UI báo thời gian rảnh, hiện cảnh báo và gọi lệnh khóa vì `LockWorkStation` chỉ chạy được trong phiên của người dùng.

### Trẻ nào đang dùng máy

- Service lấy SID của phiên đang hoạt động (Windows: `LookupAccountName` từ tên phiên; Mac: tài khoản giả trong `OGK_FAKE_ACCOUNTS`, chọn bằng `OGK_FAKE_SESSION_USER`).
- Trẻ là trẻ có SID đó trong `accounts` của chính sách đã ký. SID không thuộc trẻ nào (ví dụ tài khoản của phụ huynh) thì không bị áp luật.

### Giờ tin cậy

- Ngày, ngày thường hay cuối tuần và ô lịch tính theo giờ tin cậy, đổi sang múi giờ của máy: mốc giờ cộng thời gian trôi của đồng hồ đơn điệu.
- Mốc là `server_time` của heartbeat thành công gần nhất. Lúc khởi động, mốc là giá trị lớn hơn giữa giờ hệ thống và giờ tin cậy đã lưu, nên lùi giờ rồi khởi động lại không làm thời gian lùi theo.
- Giờ hệ thống chậm hơn giờ tin cậy quá 2 phút: cảnh báo `clock_tampered` với `detail = backward` ngay lập tức.
- Giờ hệ thống nhanh hơn: khi đang online, cảnh báo `forward` nếu heartbeat tiếp theo cho thấy giờ hệ thống nhanh hơn `server_time` quá 2 phút; chưa tới heartbeat đó thì chờ vì thức dậy sau khi ngủ trông giống hệt. Khi mất kết nối, bước tiến được coi là máy vừa ngủ và trở thành mốc mới.
- Cảnh báo tự hết khi giờ hệ thống về lại trong khoảng 2 phút.

### Bộ đếm

- Thời gian được tính khi phiên đã đăng nhập, không khóa, và Tray UI báo rảnh dưới 5 phút. Không có tín hiệu từ Tray UI trong 15 giây thì vẫn tính (fail-closed).
- Mỗi giây cộng khoảng trôi của đồng hồ đơn điệu, tối đa 2 giây một lần, nên chỉnh giờ hệ thống không cộng hay trừ được và thời gian ngủ không bị tính.
- Bộ đếm lưu vào DB cục bộ mỗi 30 giây và khi khóa hoặc đăng xuất; sang ngày mới theo giờ tin cậy thì bắt đầu từ 0.

### Cảnh báo và khóa

- Thời gian còn lại là giá trị nhỏ hơn giữa quota còn lại của ngày và thời gian tới khi lịch đóng.
- Thời gian còn lại đi qua 10, 5, 1 phút thì có cảnh báo và sự kiện `quota_warning`. Ngưỡng đã thấp hơn thời gian còn lại lúc bắt đầu thì không cảnh báo.
- Hết giờ trong lúc dùng: ân hạn 60 giây, rồi khóa và ghi sự kiện `locked`.
- Đã hết giờ hoặc ngoài lịch lúc đăng nhập, mở khóa, khởi động service hoặc đổi trẻ: khóa ngay, không ân hạn, ghi `locked`.
- Khi đang khóa mà phiên vẫn mở thì service ra lệnh khóa lại mỗi 5 giây, không ghi thêm sự kiện.
- Thêm quota, mở lịch hoặc sang ngày mới thì trạng thái về `ok`.

## Kiểm soát ứng dụng

Service so luật, kết thúc tiến trình bị chặn và tính thời lượng ứng dụng; Tray UI báo ứng dụng ở cửa sổ trước và hiện cửa sổ giải thích khi chặn.

### So luật

- Mỗi giây service liệt kê tiến trình và chỉ xét tiến trình mới, nhận diện bằng cặp (pid, thời điểm tạo).
- Tên là tên tệp thực thi chữ thường. SHA-256 tính trên tệp thực thi ở thread phụ, đệm theo đường dẫn, kích thước và thời điểm sửa tệp nên tệp không đổi thì không tính lại. Không đọc được tệp thì chỉ so theo tên.
- Luật `block` khớp tiến trình nếu `name` bằng tên tiến trình, hoặc `sha256` khác `null` và bằng SHA-256 của tệp. Vì vậy đổi tên `notepad.exe` thành `game.exe` vẫn bị luật chặn có SHA-256 của notepad nhận ra.
- Luật `allow` chỉ có tác dụng khi `sha256` khác `null` và bằng SHA-256 của tệp; khi đó tiến trình được chạy dù có luật `block` khớp. Luật `allow` có `sha256` là `null` chỉ dùng làm ghi chú.
- Thứ tự quyết định: `allow` khớp theo SHA-256, rồi `block` khớp, còn lại cho chạy.
- Khớp `block` theo tên thì chặn ngay khi thấy tiến trình, trừ khi chính sách có luật `allow` có SHA-256; khi đó, và khi chỉ có thể khớp theo SHA-256, service quyết định sau khi tính xong SHA-256.

### Không bao giờ kết thúc

Service không kết thúc:

- Tiến trình ngoài phiên của trẻ đang đăng nhập, pid 0 và 4.
- Tiến trình hệ thống quan trọng: tên thuộc danh sách cố định (ví dụ `csrss.exe`, `wininit.exe`, `winlogon.exe`, `services.exe`, `lsass.exe`, `smss.exe`, `svchost.exe`, `dwm.exe`, `explorer.exe`, `ogk-service.exe`, `ogk-tray.exe`) **và** tệp thực thi nằm dưới thư mục Windows hoặc thư mục cài OGK. Một tệp khác đổi tên thành `explorer.exe` trong thư mục của trẻ vẫn bị chặn.

### Khi chặn

- Chỉ chặn khi phiên thuộc một trẻ và cưỡng chế đang bật, để không chặn im lặng lúc Tray UI không chạy.
- Service kết thúc tiến trình, ghi sự kiện `blocked_app` (tối đa một sự kiện mỗi tên trong 5 giây khi trẻ mở lại liên tục) và tăng `block_seq` trong `GET /ipc/appcontrol`. Tray UI hiện cửa sổ giải thích tên ứng dụng, lý do và người đặt luật.

### Thời lượng ứng dụng

- Tray UI báo tên tiến trình của cửa sổ trước trong mỗi heartbeat, không gửi tiêu đề cửa sổ. Ứng dụng chạy ngầm hoặc thu nhỏ không có cửa sổ trước nên không được tính.
- Đổi ứng dụng ở cửa sổ trước thì service ghi `app_stop` cho ứng dụng cũ, `duration_sec` đo bằng đồng hồ đơn điệu, và `app_start` cho ứng dụng mới.
- Khoảng đang tính kết thúc khi khóa máy, đăng xuất, đổi trẻ, Tray UI báo rảnh từ 5 phút hoặc không có heartbeat trong 15 giây. Khoảng dài quá 86400 giây được tách làm nhiều sự kiện.

## Kênh IPC giữa service và Tray UI

HTTP tại `127.0.0.1`, chỉ phục vụ Tray UI trên cùng máy. Service sinh token mới mỗi lần khởi động và ghi `{ "port": ..., "token": "..." }` vào `ipc.json` trong thư mục dữ liệu. Chỉ tệp này cho người dùng thường đọc được. Mọi request mang header `Authorization: Bearer <token>`; thiếu hoặc sai token thì trả 401 `{ "error": "unauthorized" }`.

### `GET /ipc/status`

| HTTP | Body |
| :---- | :---- |
| 200 | `{ "status": "ok", "uptime": 12.3, "server_reachable": true, "enrollment": "active", "enforcement": { "enabled": true, "reason": null, "since": "2026-11-18T08:00:00Z" }, "policies": { "7": 3 }, "policy_mode": "cached", "offline_seconds": 0 }` |

`policy_mode` là `cached` khi agent áp chính sách đã ký, `default` khi áp chính sách mặc định. `offline_seconds` là thời gian mất kết nối đã đo.

`enforcement.enabled` là `false` khi service đã tắt cưỡng chế. Khi đó `reason` cho biết lý do: `tray_unavailable` nghĩa là bật lại Tray UI thất bại 3 lần liên tiếp. Cưỡng chế bật lại ngay khi nhận được tín hiệu sống từ Tray UI.

### `POST /ipc/heartbeat`

Tray UI gửi mỗi 5 giây. Body: `{ "pid": 4242, "idle_seconds": 12.5, "foreground": "chrome.exe" }`. `idle_seconds` là số giây từ lần nhập liệu gần nhất (Windows: `GetLastInputInfo`; Mac: tệp `fake_idle`), có thể bỏ trống. `foreground` là tên tệp thực thi chữ thường của cửa sổ trước (Windows: `GetForegroundWindow` rồi tên tiến trình; Mac: tệp `fake_foreground`), `null` hoặc bỏ trống khi không có cửa sổ trước.

| HTTP | Body |
| :---- | :---- |
| 200 | `{ "status": "ok" }` |
| 400 | `{ "error": "bad_request" }` (body không phải JSON, `pid` không phải số nguyên dương, `idle_seconds` không phải số không âm, hoặc `foreground` không phải chuỗi 1 đến 255 ký tự không chứa `/` hay `\`) |

Service tự bật Tray UI trong phiên người dùng đang hoạt động. Nếu không có tín hiệu sống trong 15 giây sau khi bật, hoặc tiến trình thoát trước tín hiệu sống đầu tiên, thì tính là một lần thất bại.

### `GET /ipc/screentime`

Tray UI hỏi mỗi giây.

```json
{
  "status": "ok",
  "child_id": 7,
  "state": "grace",
  "counting": true,
  "used_seconds": 7210,
  "quota_seconds": 7200,
  "remaining_seconds": 0,
  "warning": 1,
  "warning_seq": 3,
  "grace_seconds": 42,
  "lock_reason": "quota",
  "lock_seq": 0,
  "set_by": "parent@example.com"
}
```

| Trường | Ý nghĩa |
| :---- | :---- |
| `state` | `none` (phiên không thuộc trẻ nào), `ok`, `grace` (đang ân hạn), `locked` |
| `counting` | Giây hiện tại có được tính không |
| `warning`, `warning_seq` | Cảnh báo gần nhất (phút) và số thứ tự tăng dần; Tray UI hiện mỗi số thứ tự một lần, lần hỏi đầu chỉ ghi nhận mốc |
| `grace_seconds` | Số giây ân hạn còn lại khi `state = grace` |
| `lock_reason` | `quota` hoặc `schedule` |
| `lock_seq` | Số thứ tự lệnh khóa, tăng dần. Khi `state = locked` và `lock_seq` khác lần trước, Tray UI hiện lý do và người đặt luật khoảng 2 giây rồi khóa máy (Windows: `LockWorkStation`; Mac: ghi `fake_lock.jsonl` và thêm sự kiện `lock` vào `fake_session.jsonl`) |
| `set_by` | Email phụ huynh đặt luật; rỗng khi áp chính sách mặc định |

### `GET /ipc/appcontrol`

Tray UI hỏi mỗi giây.

```json
{ "status": "ok", "block_seq": 2, "app": "game.exe", "set_by": "parent@example.com", "source": "cached" }
```

| Trường | Ý nghĩa |
| :---- | :---- |
| `block_seq` | Số thứ tự lần chặn, tăng dần. Tray UI hiện cửa sổ giải thích mỗi số thứ tự một lần; lần hỏi đầu chỉ ghi nhận mốc |
| `app` | Tên ứng dụng bị chặn gần nhất; `null` khi chưa chặn lần nào |
| `set_by` | Email phụ huynh đặt luật; rỗng khi áp chính sách mặc định |
| `source` | `cached` (chính sách đã ký) hoặc `default` (chính sách mặc định) |

### Công cụ phát triển

Chỉ có khi service chạy với biến môi trường `OGK_DEV=1` và gói `service.devtools` có trong bản build. Bản phát hành build với `--exclude-module service.devtools` nên không có các route này; gọi tới thì nhận 404. Dùng qua `python -m service.devtools`.

| Route | Body | Tác dụng |
| :---- | :---- | :---- |
| `POST /ipc/dev/events` | `{ "events": [...] }` hoặc `{ "vector": "<tên>", "child_id": 7, "count": 1 }` | Đưa sự kiện vào hàng đợi; `vector` lấy sự kiện mẫu hợp lệ trong `docs/test_vectors.json`, thay `ts` bằng giờ hiện tại, `child_id` bằng giá trị gửi lên hoặc trẻ đầu tiên có chính sách, `policy_id` bằng version đang áp. `device_id` luôn được thay bằng thiết bị hiện tại. Trả `{ "queued": n, "pending": m }`; sự kiện sai trả 400 `{ "error": "invalid_event", "field": "..." }`; chưa ghép đôi trả 409 `{ "error": "not_enrolled" }` |
| `POST /ipc/dev/offline` | `{ "days": 7 }` | Cộng thêm số ngày mất kết nối giả lập rồi kiểm tra hạn chính sách ngay. Trả `{ "offline_seconds": ..., "policy_mode": "default" }` |
