# HỆ THỐNG GIA SƯ GIÁO DỤC PHỔ THÔNG VIỆT NAM (LỚP 6-12) - 24/7 CLOUD DEPLOY

Dịch vụ MCP Server chạy đám mây 24/7 trên [Render.com](https://render.com/) hoàn toàn **miễn phí ($0/tháng)**, giúp Robot Xiaozhi ESP32 luôn hoạt động độc lập qua Wi-Fi mà **không cần bật máy tính cá nhân**.

---

## 1. Cấu Trúc Thư Mục

```text
├── main.py          # Ứng dụng FastAPI + MCP Client chạy ngầm kết nối Xiaozhi 24/7
├── Procfile         # Khởi động dịch vụ trên Render (uvicorn main:app)
├── requirements.txt # Thư viện: fastapi, uvicorn, websockets
├── .gitignore       # Bỏ qua các tệp tạm của Python
└── README.md        # Hướng dẫn chi tiết
```

---

## 2. Hướng Dẫn Triển Khai Lên Render.com Trong 3 Bước

### Bước 1: Tạo Repository mới trên GitHub
1. Truy cập [https://github.com/new](https://github.com/new) trên tài khoản `thetaivnpt-design`.
2. Đặt tên repository: `xiaozhi-tutor-mcp` (để chế độ **Public** hoặc **Private** đều được).
3. Tải toàn bộ các file trong thư mục `cloud_deploy` này lên repository đó.

### Bước 2: Tạo Web Service trên Render.com
1. Truy cập [https://dashboard.render.com](https://dashboard.render.com/) và đăng nhập (bằng tài khoản GitHub của bạn).
2. Nhấn nút **New +** ở góc trên cùng bên phải $\rightarrow$ Chọn **Web Service**.
3. Chọn repository `thetaivnpt-design/xiaozhi-tutor-mcp` vừa tạo $\rightarrow$ Nhấn **Connect**.

### Bước 3: Cấu hình thông số (Hoàn toàn tự động)
Điền các thông số như sau:
* **Name:** `xiaozhi-tutor-mcp`
* **Region:** `Singapore` (hoặc khu vực gần Việt Nam nhất)
* **Branch:** `main`
* **Runtime:** `Python 3`
* **Build Command:** `pip install -r requirements.txt`
* **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
* **Instance Type:** Chọn **Free ($0/month)**.

*(Tùy chọn bảo mật)*: Trong mục **Environment Variables** (Biến môi trường), bạn có thể thêm:
* Key: `MCP_TOKEN`
* Value: *(Dán chuỗi token MCP của bạn vào đây nếu sau này bạn đổi token mới)*

Nhấn **Create Web Service**!

---

## 3. Hoàn Tất & Kiểm Tra
* Sau khoảng 1 phút, Render sẽ build xong và báo trạng thái **Live** (Màu xanh lá).
* Đường link web của bạn (ví dụ: `https://xiaozhi-tutor-mcp.onrender.com/`) khi truy cập sẽ báo:
  ```json
  {
    "status": "online",
    "service": "Gia Sư Phổ Thông Việt Nam (Lớp 6-12) 24/7",
    "cloud_host": "Render.com",
    "mcp_connected": true
  }
  ```
* Robot Xiaozhi ESP32 của bạn bây giờ có thể đặt ở bất cứ đâu (phòng khách, bàn học, phòng ngủ...) chỉ cần có Wi-Fi là luôn có một người Gia sư thông thái 24/7 mà bạn hoàn toàn có thể tắt máy tính cá nhân!
