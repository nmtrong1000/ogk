# QUY TRÌNH THỰC HIỆN PHASE

Quy trình áp dụng cho mọi phase của đồ án OGK. Mỗi phase đi qua 8 bước theo thứ tự:

PLANNING -> DESIGN -> IMPLEMENTATION -> TESTING -> REVIEW -> RESOLVE FEEDBACK -> HUMAN REVIEW -> COMMIT

## 1. Các bước

| Bước | Việc làm | Đầu ra | Điều kiện sang bước sau |
| :---- | :---- | :---- | :---- |
| PLANNING | Tạo branch của phase từ `main`; đọc file phase trong `plan/`, xác định phạm vi, task và câu hỏi còn mở | Kế hoạch chạy phase | User duyệt kế hoạch |
| DESIGN | Thiết kế API, lược đồ DB, module và giao thức cho phase | Thiết kế; cập nhật `docs/protocol.md` khi giao thức thay đổi; cập nhật `DB_SCHEMA.md` trong thư mục migrations của app khi lược đồ DB thay đổi | Thiết kế khớp kế hoạch đã duyệt |
| IMPLEMENTATION | Viết code theo task ID, đúng quy tắc module trong PLAN.md | Code và test của phase | Làm xong mọi task của phase |
| TESTING | Chạy test tự động và mọi mục kiểm tra nghiệm thu của phase | Kết quả từng mục, kèm lỗi nếu có | Mọi test và mục nghiệm thu qua |
| REVIEW | Tự review thay đổi: đúng yêu cầu, bảo mật, quy tắc module, không có tệp bí mật, `DB_SCHEMA.md` khớp model và migration | Danh sách vấn đề | Đã có danh sách vấn đề, kể cả khi rỗng |
| RESOLVE FEEDBACK | Sửa từng vấn đề, chạy lại TESTING | Code đã sửa, kết quả test mới | Không còn vấn đề và test qua |
| HUMAN REVIEW | Trình bày cho user: thay đổi, kết quả test, chỗ lệch so với kế hoạch | Quyết định của user | User approve. Nếu user yêu cầu sửa thì quay lại RESOLVE FEEDBACK |
| COMMIT | Commit theo conventional commit trên branch của phase, merge branch vào `main` và push | Phase đã merge vào `origin/main` | Kết thúc phase |

## 2. Quy định branch và commit

- Mỗi phase làm trên một branch riêng tạo từ `main`, tên dạng `phase/p<số phase>`, ví dụ `phase/p5`.
- Không commit thẳng vào `main`.
- Tuyệt đối không commit, merge hoặc push khi user chưa approve ở bước HUMAN REVIEW.
- User approve cho một lần commit, merge hoặc push không áp dụng cho lần sau.
- Commit message theo conventional commit, ví dụ `feat(server): add parent login`.
- Không commit tệp bí mật: khóa, chứng chỉ, `.env`, DB.

## 3. Quy định lược đồ cơ sở dữ liệu

- Mỗi app có DB giữ hợp đồng lược đồ ở `DB_SCHEMA.md` trong thư mục migrations của app đó, gồm sơ đồ ER, định nghĩa từng bảng và ràng buộc toàn vẹn. Server: `ogk-server/migrations/DB_SCHEMA.md`; DB_SCHEMA.md của app khác theo cùng cấu trúc.
- Mọi thay đổi lược đồ DB đều cập nhật `DB_SCHEMA.md` của app đó trong cùng commit với model và migration: thêm, xóa, đổi tên bảng hoặc cột, đổi kiểu, nullable, mặc định, khóa, chỉ mục duy nhất, khóa ngoại, hành động khi xóa, hoặc luật kiểm tra dữ liệu trong code.
- Sơ đồ ER, bảng định nghĩa cột và ràng buộc toàn vẹn phải khớp model và migration. Ràng buộc do code kiểm tra thay vì DB thì ghi rõ trong phần Context.
- Mã ràng buộc `IC-nnn` không dùng lại sau khi xóa.
- Bảng nội bộ của công cụ migration, như `alembic_version`, không ghi trong tài liệu.

## 4. Phạm vi áp dụng

- Áp dụng từ P2 trở đi.
- P1 được commit trước khi có quy trình này nên không áp dụng.
