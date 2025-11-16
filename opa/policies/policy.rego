package envoy.authz

import input.attributes.request.http as http

# Mặc định: CẤM
default allow = 0

# ----- QUY TẮC CHO NGƯỜI DÙNG (USER) -----
# Cho phép nếu user có JWT hợp lệ VÀ có vai trò "admin"
allow if {
    payload := io.jwt.decode(http.headers.authorization)
    payload[1].realm_access.roles[_] == "admin"
}

# ----- QUY TẮC CHO THIẾT BỊ (DEVICE) -----
# Cho phép nếu thiết bị có mTLS hợp lệ
allow if {
    # Khi dùng mTLS, Envoy sẽ gửi "CN" (Common Name) của cert
    # Chúng ta sẽ cấp cert cho ESP32 với tên "CN=esp32_device"
    http.headers["x-forwarded-client-cert"] == "Subject=\"CN=esp32_device\""
}