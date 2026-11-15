import os
import sys
import urllib.request
import urllib.parse
import json
import math

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from spbu_data import MEDAN_DISTRICTS, MEDAN_SPBU_DATABASE

# Cache in-memory untuk efisiensi
GEOCODE_CACHE = {}
ROUTING_CACHE = {}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def reverse_geocode(lat, lng):
    """
    Mengambil data administratif riil (Kota, Kecamatan, Jalan) dari koordinat GPS
    menggunakan OpenStreetMap Nominatim.
    """
    cache_key = f"{round(lat, 4)},{round(lng, 4)}"
    if cache_key in GEOCODE_CACHE:
        return GEOCODE_CACHE[cache_key]

    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&addressdetails=1"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SPBUMedanRealLocationApp/1.0 (contact: admin@spbumedan.id)"}
    )

    result = {
        "city": "Kota Medan",
        "district": "Medan Area",
        "subdistrict": "Pasar Merah",
        "road": "Jl. Menteng Raya",
        "display_name": "Kota Medan, Sumatera Utara",
        "is_real_geocode": False
    }

    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
            addr = data.get("address", {})

            # Ekstrak data administratif
            city = addr.get("city") or addr.get("town") or addr.get("county") or "Kota Medan"
            district = addr.get("suburb") or addr.get("city_district") or addr.get("municipality") or ""
            road = addr.get("road") or addr.get("pedestrian") or ""
            neighbourhood = addr.get("neighbourhood") or addr.get("village") or ""

            # Normalisasi nama kecamatan
            if not district:
                # Cari kecamatan terdekat berdasarkan koordinat referensi
                nearest = get_top_nearby_districts(lat, lng, limit=1)
                district = nearest[0]["name"] if nearest else "Medan Area"
            
            clean_district = district
            if not clean_district.lower().startswith("kecamatan") and not clean_district.lower().startswith("medan"):
                clean_district = f"Medan {district}"
            if not clean_district.lower().startswith("kecamatan"):
                clean_district = f"Kecamatan {clean_district}"

            result = {
                "city": city,
                "district": clean_district,
                "subdistrict": neighbourhood,
                "road": road if road else "Jalan Utama",
                "display_name": f"{road}, {clean_district}, {city}" if road else f"{clean_district}, {city}",
                "is_real_geocode": True
            }
            GEOCODE_CACHE[cache_key] = result
    except Exception as e:
        print(f"[!] Geocoding error ({e}), menggunakan resolusi spasial fallback...")
        nearest = get_top_nearby_districts(lat, lng, limit=1)
        fallback_district = nearest[0]["name"] if nearest else "Medan Area"
        result["district"] = f"Kecamatan {fallback_district}"
        result["display_name"] = f"Kecamatan {fallback_district}, Kota Medan"

    return result

def get_top_nearby_districts(user_lat, user_lng, limit=5):
    """
    Menghitung dan mengembalikan daftar Kecamatan Terdekat dari posisi GPS pengguna di Kota Medan.
    """
    district_list = []
    
    # Hitung jumlah SPBU per kecamatan
    spbu_count_map = {}
    for s in MEDAN_SPBU_DATABASE:
        d = s.get("district", "")
        spbu_count_map[d] = spbu_count_map.get(d, 0) + 1

    for dist in MEDAN_DISTRICTS:
        dist_km = haversine(user_lat, user_lng, dist["center_lat"], dist["center_lng"])
        d_name = dist["name"]
        district_list.append({
            "name": d_name,
            "full_name": f"Kecamatan {d_name}",
            "distance_km": dist_km,
            "spbu_count": spbu_count_map.get(d_name, 0),
            "center_lat": dist["center_lat"],
            "center_lng": dist["center_lng"]
        })

    # Urutkan berdasarkan jarak terdekat
    district_list.sort(key=lambda x: x["distance_km"])
    
    top_districts = district_list[:limit]
    if top_districts:
        top_districts[0]["is_current"] = True # Kecamatan tempat pengguna berada saat ini

    return top_districts

def get_real_road_route(lat1, lon1, lat2, lon2):
    """
    Mengambil jarak rute jalan raya riil (actual driving distance) dan durasi tempuh (duration)
    menggunakan OSRM Routing Engine.
    """
    cache_key = f"{round(lat1, 4)},{round(lon1, 4)}->{round(lat2, 4)},{round(lon2, 4)}"
    if cache_key in ROUTING_CACHE:
        return ROUTING_CACHE[cache_key]

    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    req = urllib.request.Request(url, headers={"User-Agent": "SPBUMedanRouting/1.0"})
    
    # Nilai default fallback matematis
    direct_dist = haversine(lat1, lon1, lat2, lon2)
    road_dist = round(direct_dist * 1.28, 2) # Faktor belokan jalan perkotaan Medan
    duration_min = round(road_dist / 22.0 * 60, 1) # Kecepatan rata-rata 22 km/jam dalam kota

    route_info = {
        "road_distance_km": road_dist,
        "driving_duration_min": duration_min,
        "routing_source": "Urban Grid Estimation"
    }

    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == "Ok" and data.get("routes"):
                r = data["routes"][0]
                real_dist = round(r["distance"] / 1000.0, 2)
                real_dur = round(r["duration"] / 60.0, 1)
                route_info = {
                    "road_distance_km": real_dist,
                    "driving_duration_min": real_dur,
                    "routing_source": "OSRM OpenStreetMap Real Network"
                }
                ROUTING_CACHE[cache_key] = route_info
    except Exception:
        pass

    return route_info
