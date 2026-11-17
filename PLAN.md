# KẾ HOẠCH THỰC HIỆN ĐỒ ÁN OGK (làm một mình)

Ứng dụng hỗ trợ quản lý việc sử dụng máy tính của trẻ em, gồm OGK-Agent chạy trên Windows và OGK-Server chạy FastAPI.

## 1. Phân tích yêu cầu

### 1.1. Bốn khối cần xây dựng

| Khối | Chạy ở đâu | Việc chính |
| :---- | :---- | :---- |
| OGK-Server | Máy chủ LAN hoặc VPS lab | Xác thực phụ huynh, ghép đôi thiết bị, phát hành chính sách, nhận sự kiện, báo cáo, nhật ký kiểm toán |
| Dashboard phụ huynh | Trình duyệt, kể cả điện thoại | Cấu hình quota, lịch tuần, danh sách ứng dụng và tên miền, duyệt yêu cầu, xem báo cáo |
| Agent Service | Windows, quyền LocalSystem | Đếm giờ, khóa máy, chặn ứng dụng, DNS proxy, bộ đệm ngoại tuyến |
| Tray UI | Windows, phiên người dùng | Hiển thị giờ còn lại, lý do chặn, gửi yêu cầu, màn hình minh bạch cho trẻ |

### 1.2. Ràng buộc kỹ thuật quan trọng

| Ràng buộc | Hệ quả cho thiết kế |
| :---- | :---- |
| Service chạy ở Session 0, không thấy màn hình người dùng | Khóa máy, đo thời gian rảnh (GetLastInputInfo), lấy ứng dụng ở cửa sổ trước và hiện cửa sổ phải do Tray UI làm, service ra lệnh qua kênh cục bộ |
| Sản phẩm không được có chế độ ẩn | Không hiển thị được biểu tượng khay thì agent dừng cưỡng chế và gửi cảnh báo thiết bị |
| Chính sách phải có chữ ký toàn vẹn | Server ký chính sách trên JSON chuẩn hóa; agent kiểm tra chữ ký trước khi áp dụng |
| Chống chỉnh đồng hồ | Đếm giờ bằng đồng hồ đơn điệu (time.monotonic), đối chiếu giờ server mỗi lần heartbeat |
| Đồ án nhóm 3 người nhưng làm 1 mình | Làm đủ mọi mục BẮT BUỘC trước, mục NÊN CÓ chỉ làm khi còn thời gian |

### 1.3. Phân loại phạm vi

| Mức | Hạng mục | Quyết định |
| :---- | :---- | :---- |
| BẮT BUỘC | Toàn bộ F1 đến F5 có nhãn BẮT BUỘC | Làm hết |
| NÊN CÓ | Ngân sách theo nhóm ứng dụng | Thiết kế bộ đếm theo nhóm cùng lúc với bộ đếm thời gian; cài đặt ở phase tùy chọn P19 sau khi xong mọi mục BẮT BUỘC |
| CÓ THÌ TỐT | Thưởng giờ theo nhiệm vụ, TOTP | Bỏ qua, chỉ làm nếu dư thời gian |

## 2. Quyết định kỹ thuật

| Vấn đề | Lựa chọn | Lý do |
| :---- | :---- | :---- |
| Môi trường phát triển | Server và dashboard viết trên macOS (Apple Silicon); agent phát triển, kiểm thử và demo trên máy ảo Windows 11 ARM (UTM hoặc Parallels) | Agent cần pywin32 và quyền SYSTEM; Mac dùng chip ARM nên máy ảo chỉ chạy được Windows 11 ARM; báo cáo nêu rõ agent chưa được kiểm thử trên Windows 10 và máy x64 thật |
| Phiên bản Python | Python 3.12 cho cả server và agent | Đáp ứng yêu cầu 3.11+; pywin32, psutil, PyInstaller, argon2 có bản dựng sẵn |
| Kiến trúc bản build agent | x64, chạy trên Windows 11 ARM qua giả lập x64 | Đúng nền tảng x64 của đề; thư viện có đủ bản dựng x64 |
| Quản lý mã nguồn | Một git repo chung cho cả 3 app | Đổi giao thức thì sửa server và agent trong cùng một commit |
| Vị trí server khi demo | Máy Mac trong LAN, máy ảo Windows kết nối qua mạng nội bộ | Miễn phí, không phụ thuộc internet khi demo |
| Xác định trẻ trên máy | Mỗi tài khoản Windows gán cho một trẻ khi ghép đôi; agent đếm giờ theo tài khoản đang đăng nhập | Đúng mô hình 1 phụ huynh : n trẻ : m thiết bị, cho phép nhiều trẻ dùng chung máy |
| Cách khóa máy | LockWorkStation; nếu trẻ đăng nhập lại khi vẫn hết giờ thì khóa lại trong 5 giây và hiện lý do | Dùng màn hình khóa của Windows nên cuộc gọi khẩn cấp của hệ điều hành không bị chặn |
| Tray UI bị tắt | Service tự bật lại Tray UI trong phiên của trẻ; bật lại thất bại nhiều lần thì dừng cưỡng chế và gửi cảnh báo thiết bị báo phụ huynh | Đúng yêu cầu không có chế độ ẩn và không để trẻ tắt giám sát dễ dàng |
| Trẻ xem báo cáo (child-view) | Tray UI mở trang web của server bằng token thiết bị, chỉ đọc dữ liệu của trẻ đang đăng nhập Windows | Trẻ không cần nhớ mật khẩu |
| Vai trò admin | Sửa bảng phân loại dùng chung, mở khóa tài khoản phụ huynh, xem nhật ký kiểm toán toàn hệ thống; không xem dữ liệu sử dụng của trẻ | Đúng nguyên tắc tối thiểu dữ liệu |
| Kênh Service và Tray UI | HTTP 127.0.0.1 với token cục bộ lưu trong ProgramData | Dễ viết, dễ kiểm thử hơn named pipe |
| Thư viện Tray UI | pystray cho biểu tượng khay, tkinter cho cửa sổ | Có sẵn hoặc nhẹ, không cần build phức tạp |
| DNS proxy | dnslib, UDP và TCP tại 127.0.0.1:53, chuyển tiếp lên DNS gốc; luật tường lửa chặn cổng 53 đi ra ngoài trừ agent | Kiểm soát được từng truy vấn; ứng dụng không vượt proxy bằng cách gọi thẳng DNS bên ngoài |
| Tên miền cấp hai | tldextract với Public Suffix List đóng gói sẵn | Tách đúng các đuôi như edu.vn; không gọi dịch vụ bên thứ ba |
| Dashboard | App React riêng dùng Vite trong thư mục ogk-dashboard; build ra file tĩnh do FastAPI phục vụ; khi phát triển dùng proxy của Vite tới FastAPI; TypeScript, React Router, TanStack Query, Recharts | Đề cho phép React nhẹ; dashboard và API cùng origin nên cookie phiên, CSRF và IP trong nhật ký kiểm toán hoạt động như khi dùng một server; không cần chạy thêm Node.js |
| Lệnh khẩn | WebSocket từ agent tới server, tự kết nối lại | Đạt độ trễ dưới 5 giây |
| TLS | CA tự ký, agent ghim SHA-256 của chứng chỉ server | Đúng yêu cầu môi trường lab |
| Mã hóa trường nhạy cảm | AES-GCM (thư viện cryptography), khóa từ biến môi trường ở server và DPAPI ở agent | Không hardcode khóa |
| Băm mật khẩu | Argon2id qua passlib | Đúng yêu cầu F5 |
| Truy cập CSDL server | SQLAlchemy async với aiosqlite; Alembic quản lý thay đổi lược đồ | Toàn bộ server async, đồng nhất với WebSocket |
| Xử lý song song trong agent | asyncio cho DNS proxy, HTTP, WebSocket, IPC và các vòng hẹn giờ; việc chặn như tính SHA-256 hoặc gọi pywin32 chạy ở thread phụ | Một event loop dễ quản lý và dễ dừng service |
| Ký chính sách | Ed25519; server giữ khóa bí mật, agent giữ khóa công khai | Lấy được dữ liệu trên máy trẻ cũng không giả được chính sách |
| Chống đếm trùng sự kiện | Mỗi lô sự kiện có idempotency key ở header request; server lưu các key đã nhận và bỏ qua lô trùng | Lược đồ sự kiện giữ đúng 7 trường; gửi lại một lô không bị đếm hai lần |
| Cảnh báo thiết bị | Chỉnh đồng hồ và dừng cưỡng chế được gửi trong phần trạng thái của heartbeat; server lưu ở bảng cảnh báo thiết bị và hiện trên dashboard | Bảng sự kiện giữ đúng 9 loại đề quy định |
| Thời gian dùng ứng dụng | Tray UI báo tên tiến trình ở cửa sổ trước cho service; không lấy tiêu đề cửa sổ | Thời lượng và top 10 ứng dụng tính theo ứng dụng thật sự đang dùng; đúng NT2 |
| Theo dõi phiên đăng nhập | Service nhận SERVICE_CONTROL_SESSIONCHANGE khi đăng nhập, đăng xuất, khóa, mở khóa | Không phụ thuộc Tray UI để biết trạng thái phiên |
| Sự đồng ý của phụ huynh | Lưu thời điểm, IP và tài khoản phụ huynh khi ghép đôi | Đề yêu cầu ghi nhận sự đồng ý theo Nghị định 13/2023 tại bước ghép đôi |
| Chính sách hết hạn | Fail-closed có giới hạn: dưới 7 ngày mất mạng thì áp chính sách đệm; từ ngày thứ 7 chuyển sang chính sách mặc định 6 đến 11 tuổi, vẫn giữ danh sách miễn chặn an toàn | Không để trẻ mất kiểm soát hoàn toàn và cũng không khóa máy vô thời hạn |

## 3. Cấu trúc thư mục

```
doan/
  ogk-server/                      Modular monolith
    app/
      main.py                      Tạo app FastAPI, gắn router của các module, phục vụ bản build dashboard
      core/                        Hạ tầng dùng chung trong server
        config.py
        db.py                      SQLAlchemy, SQLite WAL
        security.py                Phiên, CSRF, rate limit, kiểm tra vai trò
        crypto.py                  AES-GCM
        signing.py                 Ký Ed25519
      modules/
        auth/                      Đăng ký, đăng nhập, khóa tài khoản, vai trò, admin mở khóa tài khoản
        family/                    Phụ huynh, trẻ, thiết bị, tài khoản Windows
        audit/                     Nhật ký kiểm toán
        enrollment/                Mã ghép đôi, token thiết bị, ghi nhận sự đồng ý
        policy/                    Chính sách, phiên bản, ký
        sync/                      Heartbeat, cảnh báo thiết bị, nhận sự kiện theo lô
        screentime/                Quota, lịch tuần trong chính sách
        appcontrol/                Luật ứng dụng trong chính sách
        webfilter/                 Luật tên miền, bảng phân loại, miễn chặn
        commands/                  WebSocket lệnh khẩn
        requests/                  Yêu cầu của trẻ
        reports/                   Báo cáo phụ huynh và child-view
        retention/                 Xóa sau 90 ngày, xóa toàn bộ dữ liệu của con
    certs/                         Script tạo CA tự ký
    tests/                         Chia thư mục theo module
    requirements.txt
    dist/                          Bản đóng gói server

  ogk-dashboard/                   Feature-based
    src/
      app/                         Router, layout, khởi tạo
      features/
        auth/                      Đăng nhập, đăng ký, admin mở khóa tài khoản
        family/                    Trẻ, thiết bị, gỡ thiết bị
        audit/                     Nhật ký kiểm toán
        enrollment/                Tạo mã ghép đôi, gán tài khoản Windows cho trẻ
        policy/                    Tổng quan chính sách, phiên bản
        alerts/                    Cảnh báo thiết bị
        screentime/                Quota, lịch tuần
        appcontrol/                Danh sách ứng dụng
        webfilter/                 Danh sách tên miền, nhóm phân loại, admin sửa bảng phân loại
        commands/                  Khóa ngay, mở khóa, cộng 15 phút
        requests/                  Duyệt yêu cầu của trẻ
        reports/                   Biểu đồ, top 10, số lần chặn
        child-view/                Hôm nay em đã dùng gì, nhật ký thay đổi luật
        retention/                 Xóa toàn bộ dữ liệu của con
      shared/
        api/                       Client gọi API, xử lý cookie và CSRF
        components/                Nút, bảng, biểu đồ, form dùng chung
        hooks/
        types/                     Kiểu dữ liệu của API
        utils/
    vite.config.ts
    package.json
    dist/                          Bản build của Vite

  ogk-agent/
    service/                       Module theo năng lực, ports and adapters
      main.py                      Điểm vào Windows Service, nối các module
      core/
        policy_store.py            Chính sách hiện hành đã kiểm chữ ký
        event_queue.py             Hàng đợi sự kiện, gửi theo lô có idempotency key
        bus.py                     Kênh tín hiệu giữa các module
        clock.py                   Đồng hồ đơn điệu, giờ server
        local_db.py                SQLite trong ProgramData
        ipc_server.py              Kênh 127.0.0.1 với Tray UI
      modules/
        enrollment/                Ghép đôi, token
        presence/                  Bật lại Tray UI, dừng cưỡng chế
        policy/                    Tải chính sách, kiểm chữ ký
        sync/                      Heartbeat, gửi sự kiện, cảnh báo thiết bị, ngoại tuyến, chính sách hết hạn
        screentime/                Bộ đếm, lịch, chống chỉnh đồng hồ
        appcontrol/                Quét tiến trình, SHA-256, kết thúc tiến trình, thời lượng ứng dụng
        webfilter/                 DNS proxy, phân loại, SafeSearch, DoH, miễn chặn
        commands/                  WebSocket lệnh khẩn
        requests/                  Chuyển yêu cầu của trẻ lên server
        retention/                 Xóa dữ liệu cục bộ
      platform/                    Nơi duy nhất gọi API Windows
        session.py                 SESSIONCHANGE, bật Tray UI trong phiên trẻ
        process.py
        dpapi.py
        firewall.py
        netconfig.py               DNS card mạng, registry tắt DoH
    tray/                          Feature-based
      main.py
      ipc_client.py
      features/
        presence/                  Biểu tượng khay, thông báo khởi động
        screentime/                Đồng hồ còn lại, cảnh báo, báo thời gian rảnh, khóa máy
        appcontrol/                Báo ứng dụng ở cửa sổ trước, cửa sổ giải thích khi chặn
        webfilter/                 Thông báo khi chặn tên miền
        commands/                  Thông báo khi phụ huynh khóa hoặc cộng giờ
        requests/                  Xin thêm giờ, báo chặn nhầm, kết quả duyệt
        reports/                   Mở trang báo cáo và nhật ký thay đổi luật
    data/                          categories.csv, default_policy.json, public_suffix_list.dat
    testdata/                      50 tên miền kiểm thử, 20 tên miền giáo dục
    installer/                     Script cài đặt và gỡ cài đặt
    tests/                         Chia thư mục theo module
    requirements.txt
    dist/                          ogk-service.exe, ogk-tray.exe, bộ cài

  docs/
    protocol.md                    Đặc tả giao thức, định dạng chính sách và sự kiện
    test_vectors.json              Chính sách mẫu kèm chữ ký đúng, sự kiện mẫu; test của server và agent cùng đọc
    report/                        Báo cáo, sơ đồ
  PRIVACY.md
  README.md
  PLAN.md
```

### 3.1. Quy tắc module

| App | Quy tắc |
| :---- | :---- |
| ogk-server | Mỗi module sở hữu bảng của mình. Module khác muốn dùng thì gọi qua `service.py` của module đó, không truy vấn thẳng bảng. Mỗi module gồm `router.py`, `service.py`, `models.py`, `schemas.py` |
| ogk-dashboard | Mỗi feature tự chứa trang, component và hàm gọi API của nó. Feature không import lẫn nhau, chỉ dùng chung qua `shared/` |
| ogk-agent/service | Các module không import lẫn nhau, chỉ trao đổi qua `core/`. Chỉ `platform/` được import pywin32 |
| ogk-agent/tray | Mỗi feature là một màn hình. Mọi xử lý đều gọi sang service qua `ipc_client.py` |

Module cùng tên ở các app thuộc cùng một phase.

### 3.2. Build

Mỗi app build ra `dist/` trong thư mục của chính nó.

| App | Lệnh build | Kết quả |
| :---- | :---- | :---- |
| ogk-server | Đóng gói mã nguồn và requirements | `ogk-server/dist/` |
| ogk-dashboard | `vite build` | `ogk-dashboard/dist/` |
| ogk-agent | PyInstaller (Python 3.12 x64) cho service và tray, rồi tạo bộ cài | `ogk-agent/dist/` |

Server đọc vị trí bản build dashboard từ biến cấu hình `DASHBOARD_DIST`. Khi phát triển, biến này trỏ tới `../ogk-dashboard/dist`. Khi deploy, bản build dashboard được chép cạnh gói server.

## 4. Các phase

P1 đến P4 dựng khung cho 4 app, chưa có chức năng nào. P5 đến P18, mỗi phase là một module chức năng của đề bài. P19 là phase tùy chọn cho mục NÊN CÓ. P20 đóng gói, nghiệm thu, viết báo cáo và chuẩn bị vấn đáp.

Mỗi phase nằm trong một file riêng ở thư mục `plan/`, gồm mục tiêu, kiểm tra nghiệm thu, kết quả, phase con và task.

| Cấp | Dạng ID | Ví dụ |
| :---- | :---- | :---- |
| Phase | P và số thứ tự | P12 |
| Phase con | ID phase, dấu chấm, số thứ tự app trong phase theo thứ tự server, dashboard, service, tray | P12.3 |
| Task | ID phase con, dấu chấm, số thứ tự task | P12.3.2 |

| ID | Phase | Cần xong trước | App | Mốc kiểm tra |
| :---- | :---- | :---- | :---- | :---- |
| P1 | [Scaffold OGK-Server](plan/P1.md) | | server | curl `/api/health` qua HTTPS trả mã 200 |
| P2 | [Scaffold Dashboard](plan/P2.md) | P1 | server, dashboard | Mở trang trống qua HTTPS của OGK-Server |
| P3 | [Scaffold Agent Service](plan/P3.md) | P1 | service | Service chạy trên máy ảo và gọi được server |
| P4 | [Scaffold Tray UI](plan/P4.md) | P3 | service, tray | Biểu tượng khay hiện và gọi được service |
| P5 | [Xác thực và phân quyền](plan/P5.md) | P2 | server, dashboard | Phụ huynh đăng nhập qua HTTPS, khóa sau 5 lần sai |
| P6 | [Gia đình và thiết bị](plan/P6.md) | P5 | server, dashboard | Phụ huynh A không đọc được trẻ của phụ huynh B |
| P7 | [Nhật ký kiểm toán](plan/P7.md) | P6 | server, dashboard | Mỗi thay đổi có một dòng nhật ký đủ 5 trường |
| P8 | [Ghép đôi thiết bị](plan/P8.md) | P4, P6 | server, dashboard, service | Ghép đôi bằng mã 8 ký tự; thiết bị bị gỡ không gọi được API |
| P9 | [Hiện diện của agent](plan/P9.md) | P4 | service, tray | Kill Tray UI thì nó hiện lại |
| P10 | [Chính sách](plan/P10.md) | P7, P8 | server, service | Sửa một byte chính sách thì agent từ chối |
| P11 | [Đồng bộ và sự kiện](plan/P11.md) | P10 | server, dashboard, service | Đổi chính sách có hiệu lực trong 60 giây; rút mạng không mất và không trùng sự kiện |
| P12 | [Quản lý thời gian](plan/P12.md) | P9, P11 | server, dashboard, service, tray | Quota 3 phút khóa đúng hạn |
| P13 | [Kiểm soát ứng dụng](plan/P13.md) | P9, P11 | server, dashboard, service, tray | Đổi tên notepad.exe thành game.exe vẫn bị chặn |
| P14 | [Lọc website](plan/P14.md) | P9, P11 | server, dashboard, service, tray | Chặn ít nhất 95%, không chặn nhầm tên miền giáo dục |
| P15 | [Lệnh khẩn](plan/P15.md) | P12 | server, dashboard, service, tray | Lệnh khẩn có hiệu lực dưới 5 giây |
| P16 | [Yêu cầu của trẻ](plan/P16.md) | P14, P15 | server, dashboard, service, tray | Trẻ xin thêm giờ, phụ huynh duyệt, trẻ thấy kết quả |
| P17 | [Báo cáo](plan/P17.md) | P13, P14, P16 | server, dashboard, service, tray | Dashboard đủ biểu đồ; trẻ xem được báo cáo và nhật ký thay đổi luật |
| P18 | [Lưu trữ và xóa dữ liệu](plan/P18.md) | P17 | server, dashboard, service | Xóa toàn bộ dữ liệu của con thì sạch cả server và agent |
| P19 | [Ngân sách theo nhóm ứng dụng](plan/P19.md) | P12, P13 | server, dashboard, service, tray | Hai bộ đếm theo nhóm chạy độc lập |
| P20 | [Nghiệm thu, báo cáo và vấn đáp](plan/P20.md) | P18 | server, dashboard, service, tray | Mỗi tiêu chí có bằng chứng; cài và gỡ agent sạch |

## 5. Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
| :---- | :---- |
| Một người không kịp khối lượng của ba người | Làm theo thứ tự BẮT BUỘC trước; giữ giao diện đơn giản |
| Service không tương tác được với màn hình | Mọi thao tác giao diện đi qua Tray UI |
| Cổng 53 bị chiếm hoặc trình duyệt dùng DoH | Kiểm tra cổng khi khởi động, ghi log rõ ràng; tắt DoH bằng chính sách trình duyệt |
| Thư viện lỗi hoặc chậm khi chạy Python x64 trên Windows 11 ARM qua giả lập | Kiểm tra cài đặt thư viện và build PyInstaller ngay ở P3 |
| Khóa nhầm làm hỏng máy ảo | Chụp snapshot máy ảo trước mỗi lần thử; luôn có script gỡ cài đặt |
| Trễ tiến độ | Xong mỗi phase thì đối chiếu mốc kiểm tra; trễ thì cắt mục NÊN CÓ trước |
