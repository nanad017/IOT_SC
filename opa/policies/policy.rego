package envoy.authz

import input.attributes.request.http as http_request

default allow := false

token_payload := payload if {
    auth_header := http_request.headers.authorization
    startswith(auth_header, "Bearer ")
    token := substring(auth_header, 7, -1)
    [_, payload, _] := io.jwt.decode(token)
}

allow if {
    startswith(http_request.path, "/api/user")
    token_payload.realm_access.roles[_] == "admin"
    print("OPA: [ALLOW] Admin", token_payload.preferred_username, "truy cập", http_request.path)
}

allow if {
    startswith(http_request.path, "/api/device")
    xfcc := http_request.headers["x-forwarded-client-cert"]
    contains(xfcc, "CN=esp32_device")
    print("OPA: [ALLOW] Thiết bị mTLS hợp lệ truy cập", http_request.path)
}

allow if {
    http_request.path == "/"
    http_request.method == "GET"
}
