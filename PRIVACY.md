# Quyền riêng tư của OGK

Tài liệu này liệt kê mọi trường dữ liệu OGK lưu, mục đích, thời hạn lưu và ai xem được. Test `ogk-server/tests/retention/test_privacy_doc.py` và `ogk-agent/tests/modules/retention/test_privacy_doc.py` kiểm tra mọi cột trong hai DB đều có trong bảng dưới đây.

## Nguyên tắc

- OGK chỉ thu thập những gì cần để quản lý thời gian dùng máy, ứng dụng và website của trẻ, và để phụ huynh xem báo cáo.
- OGK không chụp màn hình, không ghi phím và không lưu nội dung trang web. Sự kiện chỉ lưu tên tệp thực thi hoặc tên miền cấp hai, không lưu URL đầy đủ.
- Tên trẻ, năm sinh, tên đăng nhập Windows và giá trị trong nhật ký kiểm toán được mã hóa AES-GCM khi lưu. Token, mã ghép đôi, mã child-view và bí mật thiết bị chỉ lưu dạng SHA-256. Trên máy trẻ, token và bí mật thiết bị được mã hóa bằng DPAPI.
- Lịch sử hoạt động của trẻ tự động bị xóa sau 90 ngày, trên server và trên máy trẻ.
- Phụ huynh có thể bấm "Xóa toàn bộ dữ liệu của con tôi" (trang Dữ liệu của con) để xóa ngay lịch sử của trẻ trên server và gửi lệnh xóa bộ đệm tới mọi máy đang gán trẻ. Hồ sơ trẻ, chính sách đang áp dụng và việc gán tài khoản Windows được giữ. Muốn xóa cả hồ sơ thì dùng "Xóa" trong trang thông tin của con.
- Nhật ký kiểm toán chỉ ghi thêm và không bị xóa, kể cả khi xóa toàn bộ dữ liệu của trẻ. Nhật ký chỉ ghi thay đổi do phụ huynh làm, không ghi hoạt động của trẻ.

## Ai xem được

| Vai trò | Xem được |
| :---- | :---- |
| Phụ huynh | Dữ liệu của chính mình và của trẻ, thiết bị mình quản lý, qua dashboard |
| Admin | Danh sách tài khoản phụ huynh (email, số lần sai, thời điểm khóa), toàn bộ nhật ký kiểm toán và bảng phân loại website; không xem được dữ liệu hoạt động của trẻ |
| Trẻ | Qua child-view trên máy của mình: tên, báo cáo hôm nay và nhật ký thay đổi chính sách, không có email hay IP của phụ huynh. Qua Tray UI: thời gian còn lại, trạng thái khóa và kết quả yêu cầu của chính mình |
| Agent | Dữ liệu của thiết bị mình: chính sách của trẻ được gán, lệnh và kết quả yêu cầu gửi tới thiết bị |
| Hệ thống | Trường chỉ dùng nội bộ (hàm băm, khóa chống trùng); không hiển thị cho ai |

## DB của server (`ogk-server`)

"Đến khi xóa trẻ" nghĩa là dòng bị xóa theo khi phụ huynh xóa trẻ. "Đến khi xóa thiết bị" chỉ áp dụng khi dòng thiết bị bị xóa hẳn; gỡ thiết bị trên dashboard chỉ đặt `revoked_at`.

| Trường | Mục đích | Thời hạn lưu | Ai xem được |
| :---- | :---- | :---- | :---- |
| `accounts.id` | Định danh tài khoản | Suốt thời gian dùng tài khoản | Hệ thống |
| `accounts.email` | Đăng nhập | Suốt thời gian dùng tài khoản | Phụ huynh đó, admin |
| `accounts.password_hash` | Kiểm tra mật khẩu, không lưu mật khẩu gốc | Suốt thời gian dùng tài khoản | Hệ thống |
| `accounts.role` | Phân quyền phụ huynh và admin | Suốt thời gian dùng tài khoản | Hệ thống |
| `accounts.failed_attempts` | Khóa sau 5 lần sai mật khẩu | Về 0 khi đăng nhập đúng hoặc khi khóa | Admin |
| `accounts.locked_until` | Thời điểm hết khóa | Đến khi mở khóa | Admin |
| `accounts.created_at` | Ngày tạo tài khoản | Suốt thời gian dùng tài khoản | Hệ thống |
| `sessions.id` | SHA-256 của token phiên đăng nhập | 12 giờ, dọn khi đăng nhập lại hoặc đăng xuất | Hệ thống |
| `sessions.account_id` | Phiên thuộc tài khoản nào | Như `sessions.id` | Hệ thống |
| `sessions.created_at` | Thời điểm đăng nhập | Như `sessions.id` | Hệ thống |
| `sessions.expires_at` | Hết hạn phiên | Như `sessions.id` | Hệ thống |
| `children.id` | Định danh trẻ | Đến khi xóa trẻ | Hệ thống |
| `children.owner_id` | Trẻ thuộc phụ huynh nào | Đến khi xóa trẻ | Hệ thống |
| `children.name` | Tên hiển thị trên dashboard và child-view (mã hóa) | Đến khi xóa trẻ | Phụ huynh, trẻ |
| `children.birth_year` | Gợi ý chính sách theo tuổi (mã hóa) | Đến khi xóa trẻ | Phụ huynh |
| `children.created_at` | Ngày thêm trẻ | Đến khi xóa trẻ | Phụ huynh |
| `children.updated_at` | Lần sửa gần nhất | Đến khi xóa trẻ | Phụ huynh |
| `devices.id` | Định danh thiết bị | Không xóa, để bản ghi đồng ý trỏ được tới thiết bị | Hệ thống |
| `devices.owner_id` | Thiết bị thuộc phụ huynh nào | Như `devices.id` | Hệ thống |
| `devices.name` | Tên máy hiển thị trên dashboard | Như `devices.id` | Phụ huynh |
| `devices.created_at` | Ngày ghép đôi | Như `devices.id` | Phụ huynh |
| `devices.fingerprint_hash` | SHA-256 dấu vân tay máy gửi lúc ghép đôi; hiện chưa được đọc lại (xem mục Còn mở) | Như `devices.id` | Hệ thống |
| `devices.secret_hash` | Xác thực agent khi xin token mới | Như `devices.id` | Hệ thống |
| `devices.revoked_at` | Thiết bị đã gỡ thì từ chối agent | Như `devices.id` | Phụ huynh |
| `devices.last_seen_at` | Lần cuối máy kết nối, để phụ huynh biết máy còn hoạt động | Như `devices.id` | Phụ huynh |
| `windows_accounts.id` | Định danh tài khoản Windows | Đến khi xóa thiết bị | Hệ thống |
| `windows_accounts.device_id` | Tài khoản thuộc máy nào | Đến khi xóa thiết bị | Hệ thống |
| `windows_accounts.child_id` | Trẻ nào dùng tài khoản này | Đến khi đổi gán; xóa trẻ thì về rỗng | Phụ huynh |
| `windows_accounts.sid` | Nhận ra trẻ đang đăng nhập máy | Đến khi xóa thiết bị | Agent |
| `windows_accounts.username` | Tên đăng nhập hiển thị khi gán trẻ (mã hóa) | Đến khi xóa thiết bị | Phụ huynh |
| `audit_logs.id` | Định danh dòng nhật ký | Không xóa (chỉ ghi thêm) | Hệ thống |
| `audit_logs.actor_id` | Ai thay đổi | Không xóa | Phụ huynh đó, admin |
| `audit_logs.at` | Khi nào | Không xóa | Phụ huynh đó, admin; trẻ thấy thời điểm đổi chính sách |
| `audit_logs.ip` | IP của người thay đổi, để điều tra truy cập trái phép | Không xóa | Phụ huynh đó, admin |
| `audit_logs.action` | Tạo, sửa hay xóa | Không xóa | Phụ huynh đó, admin |
| `audit_logs.target_type` | Loại đối tượng bị đổi | Không xóa | Phụ huynh đó, admin |
| `audit_logs.target_id` | Đối tượng bị đổi | Không xóa | Phụ huynh đó, admin |
| `audit_logs.old_value` | Giá trị trước khi đổi (mã hóa) | Không xóa | Phụ huynh đó, admin; trẻ thấy thay đổi chính sách của mình |
| `audit_logs.new_value` | Giá trị sau khi đổi (mã hóa) | Không xóa | Như `audit_logs.old_value` |
| `pairing_codes.id` | Định danh mã ghép đôi | Mã chưa dùng bị xóa khi tạo mã mới; mã đã dùng được giữ làm bằng chứng đồng ý | Hệ thống |
| `pairing_codes.owner_id` | Phụ huynh tạo mã | Như `pairing_codes.id` | Hệ thống |
| `pairing_codes.code_hash` | SHA-256 của mã, không lưu mã gốc | Như `pairing_codes.id` | Hệ thống |
| `pairing_codes.created_at` | Thời điểm tạo mã và đồng ý giám sát | Như `pairing_codes.id` | Hệ thống |
| `pairing_codes.expires_at` | Mã hết hạn sau 10 phút | Như `pairing_codes.id` | Phụ huynh |
| `pairing_codes.used_at` | Mã chỉ dùng một lần | Như `pairing_codes.id` | Hệ thống |
| `pairing_codes.device_id` | Thiết bị đã ghép bằng mã | Như `pairing_codes.id` | Hệ thống |
| `pairing_codes.consent_ip` | IP lúc phụ huynh đồng ý, chép sang bản ghi đồng ý | Như `pairing_codes.id` | Hệ thống |
| `device_tokens.id` | Định danh token | Token hết hạn bị dọn khi agent xin token mới | Hệ thống |
| `device_tokens.device_id` | Token của thiết bị nào | Như `device_tokens.id` | Hệ thống |
| `device_tokens.kind` | Access hay refresh | Như `device_tokens.id` | Hệ thống |
| `device_tokens.token_hash` | SHA-256 của token | Như `device_tokens.id` | Hệ thống |
| `device_tokens.created_at` | Thời điểm cấp | Như `device_tokens.id` | Hệ thống |
| `device_tokens.expires_at` | Hết hạn token | Như `device_tokens.id` | Hệ thống |
| `device_tokens.revoked_at` | Token bị thu hồi khi xoay vòng hoặc gỡ thiết bị | Như `device_tokens.id` | Hệ thống |
| `consent_records.id` | Định danh bản ghi đồng ý | Không xóa khi gỡ thiết bị, để chứng minh phụ huynh đã đồng ý | Hệ thống |
| `consent_records.account_id` | Phụ huynh đồng ý | Như `consent_records.id` | Hệ thống |
| `consent_records.device_id` | Thiết bị được đồng ý giám sát | Như `consent_records.id` | Hệ thống |
| `consent_records.consented_at` | Thời điểm đồng ý | Như `consent_records.id` | Hệ thống |
| `consent_records.ip` | IP lúc đồng ý | Như `consent_records.id` | Hệ thống |
| `consent_records.consent_version` | Phiên bản nội dung đồng ý | Như `consent_records.id` | Hệ thống |
| `policies.child_id` | Chính sách của trẻ nào | Đến khi xóa trẻ | Phụ huynh, agent |
| `policies.version` | Agent biết khi nào cần tải chính sách mới | Đến khi xóa trẻ | Phụ huynh, agent |
| `policies.weekday_quota_minutes` | Quota ngày thường | Đến khi xóa trẻ | Phụ huynh, agent, trẻ |
| `policies.weekend_quota_minutes` | Quota cuối tuần | Đến khi xóa trẻ | Phụ huynh, agent, trẻ |
| `policies.weekly_schedule` | Giờ được dùng máy | Đến khi xóa trẻ | Phụ huynh, agent, trẻ |
| `policies.app_rules` | Luật chặn và cho phép ứng dụng | Đến khi xóa trẻ | Phụ huynh, agent, trẻ |
| `policies.web_allowlist` | Website luôn được mở | Đến khi xóa trẻ | Phụ huynh, agent, trẻ |
| `policies.web_blocklist` | Website bị chặn | Đến khi xóa trẻ | Phụ huynh, agent, trẻ |
| `policies.blocked_categories` | Nhóm website bị chặn | Đến khi xóa trẻ | Phụ huynh, agent, trẻ |
| `policies.updated_by` | Phụ huynh sửa gần nhất, ghi trong chính sách đã ký | Đến khi xóa trẻ | Phụ huynh, agent |
| `policies.updated_at` | Thời điểm sửa, là `issued_at` của chính sách đã ký | Đến khi xóa trẻ | Phụ huynh, agent |
| `policy_versions.id` | Định danh bản lưu chính sách | Đến khi xóa trẻ (dashboard chỉ hiện 50 bản gần nhất); xóa toàn bộ dữ liệu của trẻ chỉ giữ bản hiện hành | Hệ thống |
| `policy_versions.child_id` | Bản lưu của trẻ nào | Như `policy_versions.id` | Hệ thống |
| `policy_versions.version` | Số phiên bản | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.weekday_quota_minutes` | Ảnh chụp chính sách để phụ huynh xem lại | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.weekend_quota_minutes` | Như trên | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.weekly_schedule` | Như trên | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.app_rules` | Như trên | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.web_allowlist` | Như trên | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.web_blocklist` | Như trên | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.blocked_categories` | Như trên | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.set_by` | Ai đặt phiên bản này | Như `policy_versions.id` | Phụ huynh |
| `policy_versions.created_at` | Khi nào | Như `policy_versions.id` | Phụ huynh |
| `events.id` | Định danh sự kiện | 90 ngày theo `ts`; xóa ngay khi phụ huynh xóa toàn bộ dữ liệu của trẻ | Hệ thống |
| `events.ts` | Thời điểm xảy ra, để cắt theo ngày trong báo cáo | Như `events.id` | Phụ huynh, trẻ |
| `events.device_id` | Máy gửi sự kiện | Như `events.id` | Hệ thống |
| `events.child_id` | Trẻ của sự kiện | Như `events.id` | Hệ thống |
| `events.type` | Loại sự kiện (mở ứng dụng, truy vấn tên miền, bị chặn…) | Như `events.id` | Phụ huynh, trẻ |
| `events.subject` | Tên tệp thực thi hoặc tên miền cấp hai, không có URL | Như `events.id` | Phụ huynh, trẻ |
| `events.duration_sec` | Thời lượng dùng ứng dụng | Như `events.id` | Phụ huynh, trẻ |
| `events.policy_id` | Phiên bản chính sách đang áp lúc xảy ra | Như `events.id` | Hệ thống |
| `event_batches.id` | Định danh lô | 90 ngày theo `received_at` | Hệ thống |
| `event_batches.device_id` | Lô của máy nào | Như `event_batches.id` | Hệ thống |
| `event_batches.idempotency_key` | Không đếm trùng khi agent gửi lại | Như `event_batches.id` | Hệ thống |
| `event_batches.received_at` | Thời điểm nhận | Như `event_batches.id` | Hệ thống |
| `event_batches.event_count` | Số sự kiện trong lô, để đối soát | Như `event_batches.id` | Hệ thống |
| `parent_commands.id` | Định danh lệnh | 90 ngày theo `created_at`; xóa ngay khi phụ huynh xóa toàn bộ dữ liệu của trẻ | Hệ thống |
| `parent_commands.device_id` | Máy nhận lệnh | Như `parent_commands.id` | Phụ huynh, agent |
| `parent_commands.child_id` | Trẻ bị tác động | Như `parent_commands.id` | Phụ huynh, agent |
| `parent_commands.actor_id` | Phụ huynh gửi lệnh | Như `parent_commands.id` | Hệ thống |
| `parent_commands.type` | Khóa, mở khóa, thêm giờ, xóa bộ đệm | Như `parent_commands.id` | Phụ huynh, agent |
| `parent_commands.minutes` | Số phút thêm | Như `parent_commands.id` | Phụ huynh, agent |
| `parent_commands.status` | Agent đã nhận chưa | Như `parent_commands.id` | Phụ huynh |
| `parent_commands.created_at` | Thời điểm gửi | Như `parent_commands.id` | Phụ huynh |
| `parent_commands.acknowledged_at` | Thời điểm agent xác nhận | Như `parent_commands.id` | Phụ huynh |
| `device_alerts.id` | Định danh cảnh báo | 90 ngày sau khi đóng (cảnh báo mở: sau lần thấy cuối) | Hệ thống |
| `device_alerts.device_id` | Máy bị cảnh báo | Như `device_alerts.id` | Phụ huynh |
| `device_alerts.type` | Tắt cưỡng chế hoặc chỉnh đồng hồ | Như `device_alerts.id` | Phụ huynh |
| `device_alerts.detail` | Lý do ngắn | Như `device_alerts.id` | Phụ huynh |
| `device_alerts.first_seen_at` | Bắt đầu | Như `device_alerts.id` | Phụ huynh |
| `device_alerts.last_seen_at` | Lần thấy cuối | Như `device_alerts.id` | Phụ huynh |
| `device_alerts.resolved_at` | Đã hết | Như `device_alerts.id` | Phụ huynh |
| `web_categories.domain` | Bảng phân loại website dùng chung, không gắn với trẻ | Đến khi admin xóa | Admin, agent |
| `web_categories.category` | Nhóm của tên miền | Như `web_categories.domain` | Admin, agent |
| `web_categories.updated_at` | Lần sửa | Như `web_categories.domain` | Admin |
| `child_requests.id` | Định danh yêu cầu | 90 ngày theo `created_at`; xóa ngay khi phụ huynh xóa toàn bộ dữ liệu của trẻ | Hệ thống |
| `child_requests.device_id` | Máy gửi yêu cầu | Như `child_requests.id` | Hệ thống |
| `child_requests.child_id` | Trẻ gửi yêu cầu | Như `child_requests.id` | Phụ huynh |
| `child_requests.type` | Xin thêm giờ hay mở website | Như `child_requests.id` | Phụ huynh, trẻ |
| `child_requests.domain` | Website trẻ xin mở | Như `child_requests.id` | Phụ huynh, trẻ |
| `child_requests.status` | Chờ, đồng ý hay từ chối | Như `child_requests.id` | Phụ huynh, trẻ |
| `child_requests.message` | Lời nhắn của phụ huynh khi quyết định | Như `child_requests.id` | Phụ huynh, trẻ |
| `child_requests.created_at` | Thời điểm gửi | Như `child_requests.id` | Phụ huynh, trẻ |
| `child_requests.decided_at` | Thời điểm quyết định | Như `child_requests.id` | Phụ huynh, trẻ |
| `child_requests.decided_by` | Phụ huynh quyết định | Như `child_requests.id` | Hệ thống |
| `daily_usage.id` | Định danh dòng | 90 ngày theo `day`; xóa ngay khi phụ huynh xóa toàn bộ dữ liệu của trẻ | Hệ thống |
| `daily_usage.device_id` | Máy đo | Như `daily_usage.id` | Hệ thống |
| `daily_usage.child_id` | Trẻ | Như `daily_usage.id` | Hệ thống |
| `daily_usage.day` | Ngày địa phương | Như `daily_usage.id` | Phụ huynh, trẻ |
| `daily_usage.seconds` | Thời gian dùng máy trong ngày | Như `daily_usage.id` | Phụ huynh, trẻ |
| `daily_usage.updated_at` | Lần cập nhật cuối | Như `daily_usage.id` | Hệ thống |
| `child_view_codes.id` | Định danh mã child-view | Mã hết hạn bị dọn khi có mã mới; xóa khi phụ huynh xóa toàn bộ dữ liệu của trẻ | Hệ thống |
| `child_view_codes.code_hash` | SHA-256 của mã, không lưu mã gốc | Như `child_view_codes.id` | Hệ thống |
| `child_view_codes.device_id` | Máy cấp mã | Như `child_view_codes.id` | Hệ thống |
| `child_view_codes.child_id` | Trẻ được xem | Như `child_view_codes.id` | Hệ thống |
| `child_view_codes.created_at` | Thời điểm cấp | Như `child_view_codes.id` | Hệ thống |
| `child_view_codes.expires_at` | Mã chỉ dùng trong 60 giây | Như `child_view_codes.id` | Hệ thống |
| `child_view_codes.used_at` | Mã chỉ dùng một lần | Như `child_view_codes.id` | Hệ thống |
| `child_view_sessions.id` | SHA-256 của token phiên child-view | 30 phút; dọn khi có phiên mới, đăng xuất hoặc xóa toàn bộ dữ liệu của trẻ | Hệ thống |
| `child_view_sessions.child_id` | Phiên chỉ đọc được trẻ này | Như `child_view_sessions.id` | Hệ thống |
| `child_view_sessions.device_id` | Gỡ máy thì phiên hết hiệu lực | Như `child_view_sessions.id` | Hệ thống |
| `child_view_sessions.created_at` | Thời điểm mở phiên | Như `child_view_sessions.id` | Hệ thống |
| `child_view_sessions.expires_at` | Hết hạn phiên | Như `child_view_sessions.id` | Hệ thống |

## DB trên máy trẻ (`ogk-agent`, `C:\ProgramData\OGK\agent.db`)

Thư mục và tệp DB chỉ SYSTEM và Administrators đọc được, nên tài khoản trẻ không mở được.

| Trường | Mục đích | Thời hạn lưu | Ai xem được |
| :---- | :---- | :---- | :---- |
| `credentials.id` | Chỉ một bộ thông tin ghép đôi | Đến khi gỡ cài đặt | Hệ thống |
| `credentials.device_id` | Định danh thiết bị trên server | Đến khi gỡ cài đặt | Agent |
| `credentials.server_url` | Địa chỉ server | Đến khi gỡ cài đặt | Agent |
| `credentials.cert_sha256` | Ghim chứng chỉ server | Đến khi gỡ cài đặt | Agent |
| `credentials.device_secret` | Bí mật thiết bị (DPAPI) | Đến khi gỡ cài đặt | Agent |
| `credentials.access_token` | Token gọi API (DPAPI) | Đến khi gỡ cài đặt | Agent |
| `credentials.access_expires_at` | Khi nào cần xin token mới | Đến khi gỡ cài đặt | Agent |
| `credentials.refresh_token` | Token xin access token mới (DPAPI) | Đến khi gỡ cài đặt | Agent |
| `credentials.enrolled_at` | Ngày ghép đôi | Đến khi gỡ cài đặt | Agent |
| `credentials.revoked_at` | Server đã gỡ thiết bị | Đến khi gỡ cài đặt | Agent |
| `policies.child_id` | Chính sách của trẻ nào | Đến khi trẻ không còn gán vào máy | Agent |
| `policies.version` | Phiên bản đang có | Như `policies.child_id` | Agent |
| `policies.payload` | Chính sách đã ký, để áp khi mất mạng | Như `policies.child_id` | Agent |
| `policies.signature` | Chữ ký server, kiểm tra mỗi lần đọc | Như `policies.child_id` | Agent |
| `policies.received_at` | Thời điểm nhận | Như `policies.child_id` | Agent |
| `event_outbox.id` | Thứ tự sự kiện chờ gửi | Đến khi server nhận; tối đa 90 ngày; xóa khi nhận lệnh xóa bộ đệm | Agent |
| `event_outbox.payload` | Sự kiện chờ gửi, cùng trường với `events` trên server | Như `event_outbox.id` | Agent |
| `event_outbox.batch_key` | Khóa chống trùng khi gửi lại | Như `event_outbox.id` | Agent |
| `event_outbox.created_at` | Thời điểm ghi | Như `event_outbox.id` | Agent |
| `sync_state.id` | Chỉ một trạng thái đồng bộ | Đến khi gỡ cài đặt | Hệ thống |
| `sync_state.offline_seconds` | Thời gian mất kết nối, để hết hạn chính sách khi offline quá lâu | Đến khi gỡ cài đặt | Agent |
| `sync_state.last_server_time` | Giờ server lần cuối | Đến khi gỡ cài đặt | Agent |
| `sync_state.last_success_at` | Lần đồng bộ thành công cuối | Đến khi gỡ cài đặt | Agent |
| `usage.child_id` | Trẻ | 90 ngày theo `day`; xóa khi nhận lệnh xóa bộ đệm | Agent |
| `usage.day` | Ngày địa phương | Như `usage.child_id` | Agent, trẻ (Tray UI) |
| `usage.counter` | Bộ đếm nào | Như `usage.child_id` | Agent |
| `usage.seconds` | Thời gian dùng máy đã đếm | Như `usage.child_id` | Agent, trẻ (Tray UI) |
| `usage.updated_at` | Lần lưu cuối | Như `usage.child_id` | Agent |
| `clock_state.id` | Chỉ một mốc giờ | Đến khi gỡ cài đặt | Hệ thống |
| `clock_state.last_trusted` | Giờ tin cậy cuối, chống chỉnh lùi đồng hồ | Đến khi gỡ cài đặt | Agent |
| `command_state.child_id` | Trạng thái lệnh của trẻ nào | Xóa khi nhận lệnh xóa bộ đệm | Agent |
| `command_state.override_day` | Ngày phụ huynh mở khóa | Như `command_state.child_id` | Agent |
| `command_state.bonus_day` | Ngày được thêm giờ | Như `command_state.child_id` | Agent |
| `command_state.bonus_seconds` | Số giây thêm còn lại | Như `command_state.child_id` | Agent, trẻ (Tray UI) |
| `command_receipts.command_id` | Không thực hiện một lệnh hai lần | 90 ngày theo `processed_at` | Agent |
| `command_receipts.processed_at` | Thời điểm thực hiện | Như `command_receipts.command_id` | Agent |

## Ngoài DB

- Log của agent `C:\ProgramData\OGK\logs\service.log` có thể có tên ứng dụng và tên miền bị chặn; log xoay vòng ở 1 MB, giữ 5 tệp cũ, và nằm trong thư mục dữ liệu chỉ SYSTEM và Administrators đọc được. Lệnh xóa bộ đệm không xóa log.
- Trạng thái trong bộ nhớ của agent (bộ đếm hôm nay, kết quả yêu cầu hiển thị trên Tray UI) mất khi service dừng; lệnh xóa bộ đệm xóa phần của trẻ ngay.

## Còn mở

- `devices.fingerprint_hash` được lưu khi ghép đôi nhưng hiện không được đọc lại. Cần quyết định dùng nó (ví dụ cảnh báo khi một bí mật thiết bị xuất hiện trên máy khác) hay bỏ cột bằng migration.
