package envoy.authz

import input.attributes.request.http as http_request

# 1. Mặc định là CẤM (Sử dụng := cho phiên bản OPA mới)
default allow := false

# --------------------------------------------------------
# 2. QUY TẮC CHO NGƯỜI DÙNG (ADMIN)
# --------------------------------------------------------
allow if {
    # 2.1 Kiểm tra và bóc tách Token sạch (bỏ "Bearer ")
    auth_header := http_request.headers.authorization
    startswith(auth_header, "Bearer ")
    token := substring(auth_header, 7, -1)

    # 2.2 Giải mã lấy payload (vị trí [1])
    [_, payload, _] := io.jwt.decode(token)

    # 2.3 Truy cập đúng cấu trúc Role của Keycloak
    payload.realm_access.roles[_] == "admin"

    # 2.4 In log để kiểm tra
    print("OPA: [ALLOW] Quyền Admin hợp lệ cho:", payload.preferred_username)
}

# --------------------------------------------------------
# 3. QUY TẮC CHO THIẾT BỊ (ESP32)
# --------------------------------------------------------
allow if {
    # 3.1 Dùng biến 'xfcc' rõ ràng và kiểm tra CN
    xfcc := http_request.headers["x-forwarded-client-cert"]
    contains(xfcc, "CN=esp32_device")
    
    print("OPA: [ALLOW] Thiết bị mTLS hợp lệ")
}