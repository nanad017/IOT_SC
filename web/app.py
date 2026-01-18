import os
import ssl
import time
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_HOST = os.environ.get("MQTT_BROKER", "mqtt")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
CA_CERT = "/app/certs/rootCA.crt"
CLIENT_CERT = "/app/certs/client.crt"
CLIENT_KEY = "/app/certs/client.key"

INFLUX_URL = os.environ.get("INFLUXDB_URL", "https://db:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "mysecrettoken")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "MyHome")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "SensorData")

app = Flask(__name__)

try:
    influx_client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG,
        ssl_ca_cert=CA_CERT
    )
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print("WEB: Kết nối InfluxDB thành công.", flush=True)
except Exception as e:
    print(f"WEB: Lỗi kết nối InfluxDB: {e}", flush=True)

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"WEB: Đã kết nối MQTTS thành công tới {MQTT_HOST}:{MQTT_PORT}", flush=True)
    else:
        print(f"WEB: Kết nối MQTTS thất bại, mã lỗi: {rc}", flush=True)

def on_disconnect(client, userdata, flags, rc, properties):
    print(f"WEB: Bị ngắt kết nối MQTTS: {rc}", flush=True)

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

try:
    if os.path.isfile(CA_CERT) and os.path.isfile(CLIENT_CERT) and os.path.isfile(CLIENT_KEY):
        print("WEB: Đang cấu hình TLS cho MQTT...", flush=True)
        mqtt_client.tls_set(
            ca_certs=CA_CERT,
            certfile=CLIENT_CERT,
            keyfile=CLIENT_KEY,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        mqtt_client.tls_insecure_set(True)
    else:
        print("WEB: LỖI - Không tìm thấy các file chứng chỉ tại /app/certs/", flush=True)
except Exception as e:
    print(f"WEB: Lỗi khi cài đặt TLS: {e}", flush=True)

try:
    print(f"WEB: Đang kết nối tới Broker {MQTT_HOST}...", flush=True)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"WEB: Lỗi kết nối MQTT: {e}", flush=True)

@app.route("/")
def health_check():
    return jsonify({"status": "running", "service": "Backend Flask"}), 200

@app.route("/api/device/data", methods=["POST"])
def receive_data():
    try:
        data = request.json
        cert_header = request.headers.get('X-Forwarded-Client-Cert', '')
        device_id = "unknown"
        if "CN=" in cert_header:
            device_id = cert_header.split("CN=")[1].split(",")[0].split(";")[0].strip('"')

        print(f"WEB: Nhận dữ liệu từ {device_id}: {data}", flush=True)

        point = Point("sensor_data") \
            .tag("device_id", device_id) \
            .field("temperature", float(data.get("temperature", 0.0))) \
            .field("humidity", float(data.get("humidity", 0.0)))

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

        return jsonify({"status": "success", "device_id": device_id}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/user/control/relay", methods=["POST"])
def send_control():
    try:
        data = request.json
        target_device = data.get("device_id")
        action = data.get("action")

        if not target_device or not action:
            return jsonify({"status": "error", "message": "Missing data"}), 400

        topic = f"iot/device/{target_device}/control"
        payload = f"{{\"cmd\": \"{action}\"}}"

        result = mqtt_client.publish(topic, payload)
        result.wait_for_publish()

        print(f"WEB: Đã gửi lệnh {action} tới {target_device}", flush=True)
        return jsonify({"status": "command_sent", "topic": topic}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("WEB: Khởi động máy chủ Flask với chế độ mTLS (Zero Trust)...", flush=True)

    cert_file = "/app/certs/web.crt"
    key_file = "/app/certs/web.key"
    ca_file = "/app/certs/rootCA.crt"

    if os.path.exists(cert_file) and os.path.exists(key_file) and os.path.exists(ca_file):
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            context.load_verify_locations(cafile=ca_file)
            context.verify_mode = ssl.CERT_REQUIRED

            print("WEB: mTLS đã được kích hoạt thành công.", flush=True)
            app.run(host="0.0.0.0", port=5000, debug=False, ssl_context=context)
        except Exception as e:
            print(f"WEB: [LỖI] Cấu hình SSL thất bại: {e}", flush=True)
            app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        print("WEB: [LỖI] Thiếu file chứng chỉ!", flush=True)
        app.run(host="0.0.0.0", port=5000, debug=False)
