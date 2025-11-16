# 1. Bắt đầu từ image Python 3.11
FROM python:3.11

# 2. Đặt thư mục làm việc bên trong container
WORKDIR /app

# 3. Sao chép TỆP TIN YÊU CẦU vào trước
COPY requirements.txt .

# 4. Chạy pip install (CHẠY KHI BUILD)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Sao chép TOÀN BỘ code (app.py) vào
COPY . .

# 6. Lệnh mặc định khi container khởi động
CMD ["python", "app.py"]