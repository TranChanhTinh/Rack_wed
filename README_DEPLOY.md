# RackFlow Online — triển khai website có link công khai

Đây là ứng dụng Flask hiện có của bạn, giữ nguyên các chức năng tìm kiếm, xem sơ đồ nhiều sheet, sửa/thêm/xóa/di chuyển thùng, tô màu ô và xuất Excel. `rack.xlsx` là dữ liệu khởi tạo.

## Chạy thử trên Windows

1. Cài Python 3.10 trở lên.
2. Mở thư mục chứa `app.py` trong VS Code.
3. Mở Terminal và chạy:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Mở http://127.0.0.1:5000.

## Đưa website lên Internet bằng Render

1. Tạo repository GitHub mới. Đưa các file trong thư mục này lên repository (bao gồm `app.py`, `templates/`, `static/`, `rack.xlsx`, `requirements.txt`, `render.yaml`).
2. Đặt repository ở Private nếu dữ liệu kho là nội bộ.
3. Đăng nhập https://render.com/ và chọn **New + → Blueprint**; kết nối repository vừa tạo.
4. Render đọc `render.yaml`, tạo web service và ổ đĩa bền vững `/var/data`. Cấu hình này dùng gói có hỗ trợ persistent disk (Starter trả phí); không xóa disk nếu muốn giữ dữ liệu.
5. Sau khi deploy thành công, mở URL `https://rackflow-online.onrender.com` (tên thực tế có thể khác nếu bị trùng). Gửi link đó cho người dùng ở mạng khác; họ chỉ cần trình duyệt và Internet.

Nếu muốn dùng Render Free, cần thay đổi phương án lưu dữ liệu: filesystem miễn phí có thể bị xóa khi deploy/restart. Không dùng bản Free với file Excel là dữ liệu quan trọng nếu chưa có sao lưu hoặc kho lưu trữ bền vững.

## Dữ liệu và quyền truy cập

- Khi khởi động lần đầu, ứng dụng sao chép `rack.xlsx` vào thư mục dữ liệu bền vững nếu chưa có file. Khi đã tồn tại, nó không ghi đè dữ liệu trên máy chủ bằng file đi kèm code.
- Tất cả người có link hiện có thể xem và sửa dữ liệu. Ứng dụng gốc chưa có đăng nhập/phân quyền; không công khai nếu không muốn người ngoài thay đổi kho.
- Vì dữ liệu đang ghi vào một file Excel, tránh để nhiều người sửa đồng thời. Tải bản Excel sao lưu định kỳ. Với nhiều người sử dụng thường xuyên, nên chuyển sang cơ sở dữ liệu và bổ sung đăng nhập.
- Website cần kết nối Internet để đọc/ghi dữ liệu máy chủ; tải trang cache hoặc PWA không làm thao tác sửa kho hoạt động offline.

## Ghi chú

`render.yaml` khai báo ổ đĩa persistent và dùng gói Render có trả phí. Đây là yêu cầu để các cập nhật `rack.xlsx` không mất sau khi ứng dụng khởi động lại. Chưa có hosting nào được tạo tự động bởi file ZIP; bạn vẫn cần đăng nhập tài khoản hosting và kết nối GitHub để nhận URL công khai.
