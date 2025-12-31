package envoy.authz

import input.attributes.request.http as http_request

# 1. Mặc định là CẤM
default allow := false

# Giải mã Token một lần để dùng chung cho các quy tắc người dùng
token_payload := payload if {
    auth_header := http_request.headers.authorization
    startswith(auth_header, "Bearer ")
    token := substring(auth_header, 7, -1)
    [_, payload, _] := io.jwt.decode(token)
}

# --------------------------------------------------------
# 2. QUY TẮC CHO NGƯỜI DÙNG (ADMIN)
# --------------------------------------------------------
# Chỉ cho phép Admin truy cập vào các đường dẫn /api/user/...
allow if {
    # Kiểm tra đường dẫn bắt đầu bằng /api/user
    startswith(http_request.path, "/api/user")
    
    # Kiểm tra Role admin từ Keycloak
    token_payload.realm_access.roles[_] == "admin"

    print("OPA: [ALLOW] Admin", token_payload.preferred_username, "truy cập", http_request.path)
}

# --------------------------------------------------------
# 3. QUY TẮC CHO THIẾT BỊ (ESP32)
# --------------------------------------------------------
# Chỉ cho phép Thiết bị truy cập vào đường dẫn /api/device/...
allow if {
    # Kiểm tra đường dẫn bắt đầu bằng /api/device
    startswith(http_request.path, "/api/device")
    
    # Kiểm tra mTLS qua header XFCC (được Envoy chuyển tiếp)
    xfcc := http_request.headers["x-forwarded-client-cert"]
    contains(xfcc, "CN=esp32_device")
    
    print("OPA: [ALLOW] Thiết bị mTLS hợp lệ truy cập", http_request.path)
}

# --------------------------------------------------------
# 4. QUY TẮC CHO PUBLIC (Tùy chọn)
# --------------------------------------------------------
# Cho phép bất kỳ ai truy cập trang chủ của Backend (để Healthcheck)
allow if {
    http_request.path == "/"
    http_request.method == "GET"
}