ui = true

storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8300"
  tls_disable = 1
}

api_addr = "http://127.0.0.1:8300"
cluster_addr = "http://127.0.0.1:8301"

disable_mlock = true

telemetry {
  disable_hostname = true
}
