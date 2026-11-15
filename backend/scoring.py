import os
import sys
import math
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from geocoding import get_real_road_route

# Profil Lalu Lintas Koridor Jalan Nyata di Medan saat ini
CORRIDOR_LIVE_TRAFFIC = {
    "Jl. Menteng Raya": {"status": "Lengang", "congestion": 0.22, "detail": "Lalin lengang di area ini, tidak ada macet"},
    "Jl. Sutrisno": {"status": "Lancar", "congestion": 0.38, "detail": "Arus ramai lancar di pertokoan"},
    "Jl. Panglima Denai": {"status": "Lancar", "congestion": 0.35, "detail": "Lalu lintas stabil"},
    "Jl. H.M. Joni": {"status": "Sedang", "congestion": 0.58, "detail": "Mulai padat menjelang simpang"},
    "Jl. Brigjend Katamso": {"status": "Padat", "congestion": 0.72, "detail": "Arus padat arah Kampung Baru"},
    "Jl. Ir. H. Juanda": {"status": "Padat", "congestion": 0.78, "detail": "Padat di sekitar simpang Istana Maimun"},
    "Jl. Sisingamangaraja": {"status": "Macet", "congestion": 0.88, "detail": "Macet antrean bus/truk Biosolar & komuter Amplas"},
    "Jl. H. Adam Malik": {"status": "Padat", "congestion": 0.75, "detail": "Padat teratur, kapasitas pompa besar"},
    "Jl. Putri Hijau": {"status": "Padat", "congestion": 0.70, "detail": "Arus kendaraan kantor pulang kerja"},
    "Jl. Jend. Gatot Subroto": {"status": "Macet", "congestion": 0.92, "detail": "Macet parah jalur utama Medan-Binjai jam sibuk"},
    "Jl. Ringroad Gagak Hitam": {"status": "Padat", "congestion": 0.82, "detail": "Antrean padat di persimpangan Ringroad"},
    "Jl. Dr. Mansyur": {"status": "Padat", "congestion": 0.74, "detail": "Padat aktivitas mahasiswa dan ojol"},
    "Jl. Jamin Ginting": {"status": "Sedang", "congestion": 0.62, "detail": "Arus ramai menuju Padang Bulan"},
    "Jl. Gunung Krakatau": {"status": "Lancar", "congestion": 0.32, "detail": "Lancar di dua arah"},
    "Jl. K.L. Yos Sudarso": {"status": "Padat", "congestion": 0.76, "detail": "Arus truk logistik menuju Belawan"}
}

def calculate_time_factor(now=None):
    """
    Menghitung pengali jam sibuk komuter harian Kota Medan.
    """
    if now is None:
        now = datetime.now()
    
    hour = now.hour + (now.minute / 60.0)
    
    # 22:00 - 05:30: Dini Hari (Lengang)
    if hour >= 22.0 or hour < 5.5:
        multiplier = 0.35
        label = "Dini Hari (Lalu Lintas Lengang)"
    # 05:30 - 06:45: Pagi Awal
    elif 5.5 <= hour < 6.75:
        multiplier = 0.60
        label = "Pagi Awal"
    # 06:45 - 08:45: Puncak Pagi
    elif 6.75 <= hour < 8.75:
        multiplier = 1.30
        label = "Puncak Pagi (Berangkat Kantor/Sekolah)"
    # 08:45 - 11:45: Reguler
    elif 8.75 <= hour < 11.75:
        multiplier = 0.80
        label = "Jam Kerja Reguler"
    # 11:45 - 13:45: Istirahat Siang
    elif 11.75 <= hour < 13.75:
        multiplier = 1.05
        label = "Jam Istirahat Siang"
    # 13:45 - 16:30: Sore Reguler
    elif 13.75 <= hour < 16.5:
        multiplier = 0.85
        label = "Sore Reguler"
    # 16:30 - 19:30: Puncak Pulang Kerja (PEAK)
    elif 16.5 <= hour < 19.5:
        multiplier = 1.40
        label = "Puncak Jam Sibuk Pulang Kerja"
    # 19:30 - 22:00: Malam
    else:
        multiplier = 0.70
        label = "Malam Hari"

    return multiplier, label

def calculate_crowd_score(spbu, user_lat=None, user_lng=None, current_time=None):
    """
    Perhitungan Skor Keramaian Berdaya Rentang Tinggi (High Dynamic Range):
    Menghasilkan skor yang sangat variatif dan realistis:
    - SPBU jalan lengang: 15 - 35 (Sepi / Hijau)
    - SPBU arus sedang: 40 - 65 (Sedang / Kuning)
    - SPBU titik macet / antrean panjang: 75 - 95 (Ramai / Merah)
    """
    time_mult, time_label = calculate_time_factor(current_time)
    road_name = spbu.get("road_name", "")
    
    # 1. Ambil data kondisi lalin segmen jalan SPBU tersebut
    corridor = CORRIDOR_LIVE_TRAFFIC.get(road_name, {
        "status": "Sedang",
        "congestion": spbu.get("base_traffic_weight", 0.5),
        "detail": "Kondisi lalu lintas normal"
    })
    
    base_congestion = corridor["congestion"] # 0.20 s.d 0.95
    
    # 2. Faktor Efisiensi Penyerapan Antrean (Kapasitas Pompa)
    pumps = spbu.get("pump_capacity", {})
    motor_nozzles = pumps.get("motorcycle_nozzles", 4)
    car_nozzles = pumps.get("car_nozzles", 4)
    diesel_nozzles = pumps.get("diesel_nozzles", 2)
    total_nozzles = motor_nozzles + car_nozzles + diesel_nozzles
    
    # Jika SPBU besar (seperti Singapore Station Adam Malik dengan 22 nozzle),
    # antrean terserap 40% lebih cepat (relief factor)
    if total_nozzles >= 18:
        pump_efficiency_factor = 0.70 # Meredam skor antrean
    elif total_nozzles >= 12:
        pump_efficiency_factor = 0.85
    elif total_nozzles >= 8:
        pump_efficiency_factor = 1.05
    else:
        pump_efficiency_factor = 1.30 # Pompa sedikit, antrean melompat tinggi
        
    # 3. Faktor Antrean BBM Subsidi (Solar & Pertalite)
    # Di Medan, SPBU jalur lintas dengan Solar tinggi (Amplas/Yos Sudarso) antreannya tinggi
    subsidy_pressure = 1.0
    if "Biosolar" in spbu.get("fuel_types", []):
        if "Arteri Primer" in spbu.get("road_class", ""):
            subsidy_pressure = 1.25 # Truk/bus mengantre panjang

    # 4. Perhitungan Skor Dinamis Berdaya Rentang Penuh (0 - 100)
    # Nilai dasar ditentukan oleh kepadatan lalu lintas nyata di jalan tersebut
    raw_score = (base_congestion * 100.0) * time_mult * pump_efficiency_factor * subsidy_pressure
    
    # Normalisasi kurva skor agar tidak menumpuk di tengah
    final_score = int(round(raw_score))
    final_score = max(8, min(96, final_score))
    
    # Penentuan Status Berdasarkan Ambang Batas Nyata
    if final_score <= 35:
        status = "Sepi"
        status_color = "#10B981" # Hijau
        est_vehicles = max(0, int(round(final_score / 12)))
        status_desc = f"Lancar, jalan depan SPBU {corridor['status'].lower()} ({corridor['detail']})."
        wait_label = "< 3 menit"
    elif final_score <= 70:
        status = "Sedang"
        status_color = "#F59E0B" # Oranye/Kuning
        est_vehicles = int(round(final_score / 10))
        status_desc = f"Arus {corridor['status'].lower()}, {corridor['detail']}."
        wait_label = f"{max(3, est_vehicles)} - {est_vehicles + 3} menit"
    else:
        status = "Ramai"
        status_color = "#EF4444" # Merah
        est_vehicles = int(round(final_score / 7))
        status_desc = f"Padat/Macet, {corridor['detail']}."
        wait_label = f"{est_vehicles + 2} - {est_vehicles + 8} menit"

    # Routing Riil OSRM
    route_data = None
    if user_lat is not None and user_lng is not None:
        route_data = get_real_road_route(user_lat, user_lng, spbu["latitude"], spbu["longitude"])

    return {
        "score": final_score,
        "status": status,
        "status_color": status_color,
        "status_description": status_desc,
        "estimated_wait_time": wait_label,
        "estimated_vehicles_in_queue": est_vehicles,
        "traffic_condition": corridor,
        "route_real": route_data,
        "breakdown": {
            "time_commuter": {
                "score": int(round(time_mult * 50)),
                "label": time_label,
                "weight": "Faktor Jam Puncak"
            },
            "traffic_corridor": {
                "score": int(round(base_congestion * 100)),
                "road_class": spbu.get("road_class", "Kolektor"),
                "status": corridor["status"],
                "weight": "Kondisi Lalin Nyata"
            },
            "pump_capacity": {
                "score": int(round(pump_efficiency_factor * 50)),
                "total_nozzles": total_nozzles,
                "weight": "Efisiensi Nozzle"
            },
            "facilities_dwell": {
                "score": 75 if spbu.get("has_convenience_store") else 30,
                "has_convenience_store": spbu.get("has_convenience_store", False),
                "weight": "Tenant Singgah"
            }
        }
    }
