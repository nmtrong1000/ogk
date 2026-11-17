# QUY TRÌNH THỰC HIỆN PHASE

Quy trình áp dụng cho mọi phase của đồ án OGK. Mỗi phase đi qua 8 bước theo thứ tự:

PLANNING -> DESIGN -> IMPLEMENTATION -> TESTING -> REVIEW -> RESOLVE FEEDBACK -> HUMAN REVIEW -> COMMIT

## 1. Các bước

| Bước | Việc làm | Đầu ra | Điều kiện sang bước sau |
| :---- | :---- | :---- | :---- |
| PLANNING | Đọc file phase trong `plan/`, xác định phạm vi, task và câu hỏi còn mở | Kế hoạch chạy phase | User duyệt kế hoạch |
| DESIGN | Thiết kế API, lược đồ DB, module và giao thức cho phase | Thiết kế; cập nhật `docs/protocol.md` khi giao thức thay đổi | Thiết kế khớp kế hoạch đã duyệt |
| IMPLEMENTATION | Viết code theo task ID, đúng quy tắc module trong PLAN.md | Code và test của phase | Làm xong mọi task của phase |
| TESTING | Chạy test tự động và mọi mục kiểm tra nghiệm thu của phase | Kết quả từng mục, kèm lỗi nếu có | Mọi test và mục nghiệm thu qua |
| REVIEW | Tự review thay đổi: đúng yêu cầu, bảo mật, quy tắc module, không có tệp bí mật | Danh sách vấn đề | Đã có danh sách vấn đề, kể cả khi rỗng |
| RESOLVE FEEDBACK | Sửa từng vấn đề, chạy lại TESTING | Code đã sửa, kết quả test mới | Không còn vấn đề và test qua |
| HUMAN REVIEW | Trình bày cho user: thay đổi, kết quả test, chỗ lệch so với kế hoạch | Quyết định của user | User approve. Nếu user yêu cầu sửa thì quay lại RESOLVE FEEDBACK |
| COMMIT | Commit và push theo conventional commit | Commit trên `origin/main` | Kết thúc phase |

## 2. Quy định commit

- Tuyệt đối không commit hoặc push khi user chưa approve ở bước HUMAN REVIEW.
- User approve cho một lần commit không áp dụng cho lần commit sau.
- Commit message theo conventional commit, ví dụ `feat(server): add parent login`.
- Không commit tệp bí mật: khóa, chứng chỉ, `.env`, DB.

## 3. Phạm vi áp dụng

- Áp dụng từ P2 trở đi.
- P1 được commit trước khi có quy trình này nên không áp dụng.
