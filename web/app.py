import os
import ssl  # <--- THÊM THƯ VIỆN SSL
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ----------------------------
# Khởi tạo Flask App
# ----------------------------
app = Flask(__name__)

# ----------------------------
# Cấu hình InfluxDB (Lấy từ env của InfluxDB)
# ----------------------------
INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "mysecrettoken") # Phải khớp với token trong YML
INFLUX_ORG = os.environ.get("INFLUX_ORG", "MyHome")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "SensorData")

# Khởi tạo InfluxDB Client
try:
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print("WEB: Kết nối InfluxDB thành công.", flush=True)
except Exception as e:
    print(f"WEB: Lỗi kết nối InfluxDB: {e}", flush=True)

# ----------------------------
# Cấu hình MQTT (ĐÃ SỬA DÙNG MQTTS)
# ----------------------------
MQTT_HOST = "mqtt"
MQTT_PORT = 8883  # <--- SỬA CỔNG SANG 8883 (MQTTS)
MQTT_USER = "admin"
MQTT_PASS = "123456"
CA_CERT_PATH = "/app/certs/rootCA.crt"  # <--- Đường dẫn mount từ Docker YML

# Khởi tạo MQTT Client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"WEB: Đã kết nối MQTTS thành công tới {MQTT_HOST}:{MQTT_PORT}", flush=True)
    else:
        print(f"WEB: Kết nối MQTTS thất bại, mã lỗi: {rc}", flush=True)

def on_disconnect(client, userdata, flags, rc, properties):
    print(f"WEB: Bị ngắt kết nối MQTTS: {rc}", flush=True)

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

# --- THÊM KHỐI NÀY ĐỂ BẬT TLS/SSL ---
try:
    print(f"WEB: Đang bật MQTTS TLS...", flush=True)
    mqtt_client.tls_set(
        ca_certs=CA_CERT_PATH,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
except Exception as e:
    print(f"WEB: Lỗi khi cài đặt TLS: {e}", flush=True)
# -----------------------------------

# --- ĐẶT KẾT NỐI TRONG TRY...EXCEPT ---
try:
    print(f"WEB: Đang kết nối tới {MQTT_HOST}:{MQTT_PORT}...", flush=True)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start() # Chạy trong background
except Exception as e:
    print(f"WEB: Lỗi nghiêm trọng khi kết nối MQTT: {e}", flush=True)
# -------------------------------------


# ==========================================================
# API ENDPOINTS (Đây là nơi Envoy sẽ chuyển request tới)
# ==========================================================

@app.route("/")
def hello():
    return "Web Service Backend đang chạy!"

# --- API cho THIẾT BỊ (ESP32) gửi dữ liệu LÊN ---
@app.route("/api/device/data", methods=["POST"])
def device_data():
    try:
        data = request.json
        print(f"WEB: Nhận dữ liệu từ thiết bị: {data}", flush=True)

        # Lấy tên thiết bị từ header mà Envoy thêm vào
        device_cn = request.headers.get('X-Forwarded-Client-Cert', 'UNKNOWN')
        device_id = device_cn.split('CN=')[-1].split('"')[0] if 'CN=' in device_cn else 'unknown'

        # Ghi vào InfluxDB
        point = Point("sensor_data") \
                .tag("device_id", device_id) \
                .field("temperature", float(data.get("temperature", 0.0))) \
                .field("humidity", float(data.get("humidity", 0.0)))
        
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        
        return jsonify({"status": "success", "message": "Đã ghi vào DB"}), 200

    except Exception as e:
        print(f"WEB: Lỗi xử lý dữ liệu: {e}", flush=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API cho NGƯỜI DÙNG (Admin) gửi lệnh XUỐNG ---
@app.route("/api/user/control/relay", methods=["POST"])
def user_control():
    try:
        data = request.json
        device_id = data.get("device_id") # VD: "esp32_device"
        action = data.get("action")       # VD: "ON" hoặc "OFF"

        if not device_id or not action:
            return jsonify({"status": "error", "message": "Thiếu device_id hoặc action"}), 400

        # Gửi lệnh điều khiển qua MQTT
        topic = f"devices/{device_id}/control"
        payload = f"{{\"relay\": \"{action}\"}}"
        
        print(f"WEB: Gửi lệnh qua MQTT: Topic={topic}, Payload={payload}", flush=True)
        mqtt_client.publish(topic, payload)
        
        return jsonify({"status": "success", "message": "Đã gửi lệnh"}), 200
        
    except Exception as e:
        print(f"WEB: Lỗi gửi lệnh: {e}", flush=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# ----------------------------
# Chạy máy chủ Flask
# ----------------------------
if __name__ == "__main__":
    print("WEB: Khởi động máy chủ Flask...", flush=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
    