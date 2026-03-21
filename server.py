from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI(title="Karuna Safety Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DATA MODEL (what Arduino sends) ──
class SensorData(BaseModel):
    temperature:   float
    humidity:      float
    globe_temp:    Optional[float] = None
    uv_index:      Optional[float] = 0.0
    fall_detected: Optional[bool]  = False
    latitude:      Optional[float] = 17.7231
    longitude:     Optional[float] = 83.3012
    heart_rate:    Optional[float] = 0.0

# ── IN-MEMORY STORE ──
latest_data = {
    "temperature":   0,
    "humidity":      0,
    "globe_temp":    0,
    "wbgt":          0,
    "uv_index":      0,
    "uv_dose":       0,
    "fall_detected": False,
    "latitude":      17.7231,
    "longitude":     83.3012,
    "heart_rate":    0,
    "zone":          "SAFE",
    "timestamp":     ""
}

# ── HELPERS ──
def calculate_wbgt(temp: float, humidity: float, globe_temp: float) -> float:
    wet_bulb = temp * (0.99 + 0.01 * humidity) - (0.55 - 0.0055 * humidity) * (temp - 14.5)
    wbgt = 0.7 * wet_bulb + 0.2 * globe_temp + 0.1 * temp
    return round(wbgt, 1)

def get_zone(wbgt: float) -> str:
    if wbgt < 25: return "SAFE"
    if wbgt < 28: return "CAUTION"
    if wbgt < 32: return "WARNING"
    return "DANGER"

# ── ROUTES ──

@app.get("/")
def root():
    return {"status": "Karuna server running", "wbgt": latest_data["wbgt"]}

@app.post("/data")
def receive_data(sensor: SensorData):
    global latest_data

    globe = sensor.globe_temp if sensor.globe_temp else sensor.temperature + 2.5
    wbgt  = calculate_wbgt(sensor.temperature, sensor.humidity, globe)
    zone  = get_zone(wbgt)

    # Accumulate UV dose
    latest_data["uv_dose"] = round(latest_data["uv_dose"] + sensor.uv_index * 0.5, 1)

    latest_data.update({
        "temperature":   sensor.temperature,
        "humidity":      sensor.humidity,
        "globe_temp":    globe,
        "wbgt":          wbgt,
        "uv_index":      sensor.uv_index,
        "fall_detected": sensor.fall_detected,
        "latitude":      sensor.latitude,
        "longitude":     sensor.longitude,
        "heart_rate":    sensor.heart_rate,
        "zone":          zone,
        "timestamp":     datetime.now().strftime("%H:%M:%S")
    })

    print(f"[{latest_data['timestamp']}] WBGT: {wbgt}°C | Zone: {zone} | UV: {sensor.uv_index} | Fall: {sensor.fall_detected}")

    if sensor.fall_detected:
        print(f"🚨 FALL DETECTED — GPS: {sensor.latitude}, {sensor.longitude}")

    return {"status": "ok", "zone": zone, "wbgt": wbgt}

@app.get("/data")
def send_data():
    return latest_data

@app.delete("/reset-uv")
def reset_uv():
    latest_data["uv_dose"] = 0
    return {"status": "UV dose reset"}
