RackFlow — quản lý sơ đồ kho từ Excel

CÀI ĐẶT
1. Cài Python 3.10 trở lên.
2. Mở Terminal tại thư mục chứa app.py và chạy:
   py -m pip install flask openpyxl
3. Khởi động website:
   py app.py
4. Mở trình duyệt:
   http://127.0.0.1:5000

TÍNH NĂNG
- Đọc các sheet trong rack.xlsx và dựng sơ đồ theo hàng/cột, giữ các khoảng trống.
- Tìm kiếm ở thanh bên trái; khi nhập sẽ hiện gợi ý mã thùng, sheet và địa chỉ ô.
- Nhấp vào mã thùng để sửa trực tiếp; Enter hoặc click ra ngoài sẽ lưu.
- Nhấn chuột phải vào ô trống để thêm thùng.
- Nhấn chuột phải vào mã thùng để sửa, xóa hoặc chọn chế độ di chuyển.
- Có thể giữ chuột phải và kéo thùng đến ô trống trong cùng sheet. Nếu thao tác kéo không tiện, chọn “Di chuyển thùng” rồi nhấp ô đích.
- Mọi thay đổi ghi trực tiếp vào rack.xlsx; mã được lưu dưới dạng văn bản để giữ số 0 ở đầu.
- Có nút tải workbook Excel đã cập nhật.

LƯU Ý
- Sao lưu rack.xlsx trước khi sửa dữ liệu.
- Đóng rack.xlsx trong Microsoft Excel trong lúc website đang ghi dữ liệu, nếu không file có thể bị khóa.
- Không thể chỉnh sửa phần con của vùng ô gộp; không thể di chuyển qua sheet khác.
- Di chuyển chỉ cho phép đến ô trống và không tự thay đổi định dạng hoặc cấu trúc vùng gộp.
- Đây là website chạy trên máy local; để dùng từ máy khác cần cấu hình mạng/hosting và bảo mật phù hợp.


CAP NHAT GIAO DIEN
- Ma thung tren so do chi hien thi, khong the sua truc tiep bang cach go vao o.
- Muon sua/them/xoa thung, hay nhan chuot phai vao o va chon thao tac trong menu.
- Sao luu rack.xlsx truoc khi chinh sua du lieu.
